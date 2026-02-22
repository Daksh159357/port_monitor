from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
import socket

app = FastAPI()

# Embed the HTML page inside the Python script
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Full Port Scanner</title>
    <style>
        body{font-family:Arial;}
        #log{padding:10px; border:1px solid #ccc; height:400px; overflow:auto;}
        .open{color:green;}
        .closed{color:red;}
    </style>
</head>
<body>
<h2>Live Full Port Scanner</h2>

<input id="target" placeholder="Enter IP/Domain">
<button onclick="startScan()">Start Scan</button>
<button onclick="stopScan()">Stop</button>

<div id="log"></div>

<script>
let ws;

function startScan(){
    document.getElementById("log").innerHTML = "";
    ws = new WebSocket("ws://" + location.host + "/scan");
    ws.onopen = () => {
        ws.send(JSON.stringify({ target: target.value }));
    };
    ws.onmessage = (evt) => {
        let data = JSON.parse(evt.data);
        let log = document.getElementById("log");

        if(data.done){
            log.innerHTML += "<div><b>Scan complete.</b></div>";
            return;
        }

        let line = document.createElement("div");
        if(data.status === "open"){
            line.innerHTML = `<span class="open">${data.port} OPEN</span>`;
        } else {
            line.innerHTML = `<span class="closed">${data.port} closed</span>`;
        }
        log.appendChild(line);
        log.scrollTop = log.scrollHeight;
    };
}

function stopScan(){
    if(ws) ws.close();
}
</script>

</body>
</html>
"""

@app.get("/")
async def index():
    return HTMLResponse(HTML)

@app.websocket("/scan")
async def scan_ports(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()
    target = data.get("target")

    # Resolve address
    try:
        ip = socket.gethostbyname(target)
    except:
        await ws.send_json({"done": True})
        return

    async def scan(p):
        try:
            conn = asyncio.open_connection(ip, p)
            reader, writer = await asyncio.wait_for(conn, timeout=0.5)
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False

    # Scan all 65,535 ports live
    for port in range(1, 65536):
        is_open = await scan(port)
        await ws.send_json({"port": port, "status": "open" if is_open else "closed"})

    # Signal done
    await ws.send_json({"done": True})
