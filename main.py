from flask import Flask, render_template_string, request, jsonify
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Global storage for scan data
scan_data = {
    "target": "",
    "open_ports": [],
    "closed_count": 0,
    "last_closed": [], # Keeps UI light by only storing recent closed
    "current_port": 0,
    "is_scanning": False,
    "progress": 0
}

def scan_single_port(ip, port):
    global scan_data
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            result = s.connect_ex((ip, port))
            if result == 0:
                if port not in scan_data["open_ports"]:
                    scan_data["open_ports"].append(port)
                    scan_data["open_ports"].sort()
            else:
                scan_data["closed_count"] += 1
                # Only keep last 10 closed ports to prevent browser lag
                scan_data["last_closed"] = ([port] + scan_data["last_closed"])[:10]
    except:
        pass
    scan_data["current_port"] = port

def run_scanner(ip):
    global scan_data
    scan_data.update({"is_scanning": True, "open_ports": [], "closed_count": 0, "last_closed": [], "progress": 0})
    
    total_ports = 65535
    with ThreadPoolExecutor(max_workers=200) as executor:
        for port in range(1, total_ports + 1):
            executor.submit(scan_single_port, ip, port)
            if port % 500 == 0:
                scan_data["progress"] = round((port / total_ports) * 100, 1)
    
    scan_data["progress"] = 100
    scan_data["is_scanning"] = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CyberScan Pro</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        :root { --bg: #0b0e14; --card: #161b22; --accent: #00d2ff; --open: #00ff88; --closed: #ff4b2b; }
        body { background: var(--bg); color: #c9d1d9; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 40px; }
        .dashboard { max-width: 1100px; margin: auto; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .header-card { grid-column: 1 / span 2; background: var(--card); padding: 30px; border-radius: 15px; border-top: 4px solid var(--accent); text-align: center; margin-bottom: 10px; }
        .input-box { display: flex; gap: 10px; justify-content: center; margin: 20px 0; }
        input { background: #0d1117; border: 1px solid #30363d; color: white; padding: 12px; border-radius: 8px; width: 300px; font-size: 16px; outline: none; }
        input:focus { border-color: var(--accent); box-shadow: 0 0 10px rgba(0, 210, 255, 0.3); }
        button { background: linear-gradient(45deg, #00d2ff, #3a7bd5); border: none; padding: 12px 30px; border-radius: 8px; color: white; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { transform: scale(1.05); }
        
        .stat-card { background: var(--card); border-radius: 12px; padding: 20px; height: 450px; display: flex; flex-direction: column; border: 1px solid #30363d; }
        .stat-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 15px; margin-bottom: 15px; }
        .scroll-area { flex: 1; overflow-y: auto; padding-right: 5px; }
        
        .port-tag { display: flex; justify-content: space-between; padding: 8px 12px; margin: 5px 0; border-radius: 6px; background: #0d1117; font-family: monospace; }
        .open-tag { border-left: 4px solid var(--open); color: var(--open); }
        .closed-tag { border-left: 4px solid var(--closed); color: var(--closed); opacity: 0.7; }
        
        .progress-container { width: 100%; background: #30363d; height: 8px; border-radius: 4px; margin-top: 15px; overflow: hidden; }
        .progress-bar { height: 100%; background: var(--accent); width: 0%; transition: width 0.4s; box-shadow: 0 0 15px var(--accent); }
        .pulse { animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>

<div class="dashboard">
    <div class="header-card">
        <h1 style="margin:0; color:var(--accent);">🛰️ CYBER-SCAN PORT ANALYZER</h1>
        <div class="input-box">
            <input type="text" id="target_ip" placeholder="Target IP (e.g. 127.0.0.1)">
            <button id="scan_btn">INITIALIZE SCAN</button>
        </div>
        <div id="status_text" class="pulse">Ready to Breach...</div>
        <div class="progress-container"><div id="progress-fill" class="progress-bar"></div></div>
    </div>

    <div class="stat-card">
        <div class="stat-header">
            <h2 style="color:var(--open); margin:0;">ACTIVE PORTS</h2>
            <span id="open_count" style="background:var(--open); color:black; padding:2px 10px; border-radius:15px; font-weight:bold;">0</span>
        </div>
        <div id="open_list" class="scroll-area"></div>
    </div>

    <div class="stat-card">
        <div class="stat-header">
            <h2 style="color:var(--closed); margin:0;">CLOSED PORTS</h2>
            <span id="closed_total" style="background:var(--closed); color:white; padding:2px 10px; border-radius:15px; font-weight:bold;">0</span>
        </div>
        <div id="closed_list" class="scroll-area"></div>
    </div>
</div>

<script>
    $('#scan_btn').click(function() {
        let ip = $('#target_ip').val();
        if(!ip) return alert("Please input target IP!");
        $.post('/start', {ip: ip});
    });

    function update() {
        $.get('/data', function(d) {
            $('#progress-fill').css('width', d.progress + '%');
            $('#open_count').text(d.open_ports.length);
            $('#closed_total').text(d.closed_count);
            
            if(d.is_scanning) {
                $('#status_text').text("ANALYZING PORT: " + d.current_port + " [" + d.progress + "%]");
            } else if(d.progress == 100) {
                $('#status_text').text("SCAN COMPLETE").removeClass('pulse');
            }

            // Update Open Ports
            let openHtml = "";
            d.open_ports.forEach(p => {
                openHtml += `<div class="port-tag open-tag"><span>PORT ${p}</span><span>OPEN</span></div>`;
            });
            $('#open_list').html(openHtml);

            // Update Closed Ports (Show recent activity)
            let closedHtml = "";
            d.last_closed.forEach(p => {
                closedHtml += `<div class="port-tag closed-tag"><span>PORT ${p}</span><span>CLOSED</span></div>`;
            });
            $('#closed_list').html(closedHtml);
        });
    }
    setInterval(update, 800);
</script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
def start():
    ip = request.form.get('ip')
    threading.Thread(target=run_scanner, args=(ip,), daemon=True).start()
    return "OK"

@app.route('/data')
def get_data(): return jsonify(scan_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
