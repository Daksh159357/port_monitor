import asyncio
import socket
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import pathlib

app = FastAPI()

HTML = pathlib.Path("index.html").read_text()


@app.get("/")
async def home():
    return HTMLResponse(HTML)


async def scan_ports(target, start, end, speed):
    sem = asyncio.Semaphore(speed)
    ip = socket.gethostbyname(target)

    async def scan(p):
        async with sem:
            try:
                r, w = await asyncio.wait_for(
                    asyncio.open_connection(ip, p), timeout=1
                )
                w.close()
                await w.wait_closed()
                return p
            except:
                return None

    tasks = [scan(p) for p in range(start, end + 1)]
    res = await asyncio.gather(*tasks)
    return [p for p in res if p]


@app.websocket("/scan")
async def websocket_scan(ws: WebSocket):
    await ws.accept()

    data = await ws.receive_json()
    target = data["target"]
    start = int(data["start"])
    end = int(data["end"])
    speed = int(data["speed"])
    delay = float(data["delay"])

    last = set()

    while True:
        found = set(await scan_ports(target, start, end, speed))

        await ws.send_json({
            "open": sorted(found),
            "new": sorted(found - last),
            "closed": sorted(last - found)
        })

        last = found
        await asyncio.sleep(delay)
