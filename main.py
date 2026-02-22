import asyncio
import socket
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import pathlib

app = FastAPI()
html = pathlib.Path("index.html").read_text()

@app.get("/")
async def home():
    return HTMLResponse(html)

async def scan_ports(target):
    sem = asyncio.Semaphore(1000)  # limit concurrency
    try:
        ip = socket.gethostbyname(target)
    except:
        return []

    async def scan(port):
        async with sem:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), timeout=0.5
                )
                writer.close()
                await writer.wait_closed()
                return port
            except:
                return None

    tasks = [scan(p) for p in range(1, 65536)]
    results = await asyncio.gather(*tasks)
    return [p for p in results if p]

@app.websocket("/scan")
async def websocket_scan(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()

    target = data["target"]

    while True:
        open_ports = await scan_ports(target)
        await ws.send_json({"open": sorted(open_ports)})
        await asyncio.sleep(5)
