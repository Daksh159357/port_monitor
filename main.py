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

@app.websocket("/scan")
async def websocket_scan(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()

    target = data["target"]
    start = int(data["start"])
    end = int(data["end"])
    speed = int(data["speed"])
    delay = float(data["delay"])

    try:
        ip = socket.gethostbyname(target)
    except:
        await ws.send_json({"error": "Cannot resolve host"})
        return

    sem = asyncio.Semaphore(speed)

    async def scan_port(port):
        async with sem:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), timeout=0.6
                )
                writer.close()
                await writer.wait_closed()
                await ws.send_json({"port": port, "status": "open"})
            except:
                await ws.send_json({"port": port, "status": "closed"})

    for p in range(start, end+1):
        await scan_port(p)

    await ws.send_json({"done": True})
