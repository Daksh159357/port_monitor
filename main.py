import socket
import threading
from flask import Flask, render_template_string, request, jsonify
import os

app = Flask(__name__)

# Global storage for scan data
scan_data = {
    "target": "",
    "open_ports": [],
    "closed_count": 0,
    "last_closed": [],
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
                # UI Performance: only keep last 10 closed ports in memory
                scan_data["last_closed"] = ([port] + scan_data["last_closed"])[:10]
    except:
        pass
    scan_data["current_port"] = port

def run_scanner(ip):
    global scan_data
    # Reset data for new scan
    scan_data.update({
        "target": ip,
        "is_scanning": True, 
        "open_ports": [], 
        "closed_count": 0, 
        "last_closed": [], 
        "progress": 0
    })
    
    total_ports = 65535
    # Using a ThreadPool to prevent crashing the server while scanning
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=100) as executor:
        for port in range(1, total_ports + 1):
            executor.submit(scan_single_port, ip, port)
            if port % 500 == 0:
                scan_data["progress"] = round((port / total_ports) * 100, 1)
    
    scan_data["progress"] = 100
    scan_data["is_scanning"] = False

# --- UI DESIGN (Glassmorphism Cyber Theme) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CyberScan Port Monitor</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        :root { --bg: #0d1117; --card: #161b22; --accent: #58a6ff; --open: #3fb950; --closed: #f85149; }
        body { background: var(--bg); color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; }
        .header { background: var(--card); padding: 25px; border-radius: 12px; border: 1px solid #30363d; text-align: center; margin-bottom: 20px; }
        .input-area { margin: 20px 0; display: flex; gap: 10px; justify-content: center; }
        input { background: #010409; border: 1px solid #30363d; color: white; padding: 12px; border-radius: 6px; width: 280px; }
        button { background: #238636; border: none; color: white; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        button:disabled { background: #216e39; opacity: 0.6; }
        
        .progress-box { width: 100%; background: #30363d; height: 10px; border-radius: 5px; margin: 15px 0; overflow: hidden; }
        .progress-bar { height: 100%; background: var(--accent); width: 0%; transition: width 0.3s; }
        
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .panel { background: var(--card); border: 1px solid #30363d; border-radius: 12px; height: 500px; display: flex; flex-direction: column; }
        .panel-header { padding: 15px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
        .list-content { flex: 1; overflow-y: auto; padding: 15px; font-family: monospace; }
        
        .item { padding: 8px; margin-bottom: 5px; border-radius: 4px; display: flex; justify-content: space-between; background: #0d1117; }
        .item.open { border-left: 4px solid var(--open); color: var(--open); }
        .item.closed { border-left: 4px solid var(--closed); color: var(--closed); opacity: 0.7; }
        .badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; background: #30363d; color: white; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1 style="margin:0; color: var(--accent);">Port Monitor Pro</h1>
        <div class="input-area">
            <input type="text" id="target_ip" placeholder="Target IP (e.g., 8.8.8.8)">
            <button id="scan_btn">START FULL SCAN</button>
        </div>
        <div id="status">System Idle</div>
        <div class="progress-box"><div id="progress-bar" class="progress-bar"></div></div>
    </div>

    <div class="main-grid">
        <div class="panel">
            <div class="panel-header">
                <h3 style="color:var(--open); margin:0;">Open Ports</h3>
                <span id="open_count" class="badge">0</span>
            </div>
            <div id="open_list" class="list-content"></div>
        </div>
        <div class="panel">
            <div class="panel-header">
                <h3 style="color:var(--closed); margin:0;">Closed Ports (Recent)</h3>
                <span id="closed_total" class="badge">0</span>
            </div>
            <div id="closed_list" class="list-content"></div>
        </div>
    </div>
</div>

<script>
    $('#scan_btn').click(function() {
        let ip = $('#target_ip').val();
        if(!ip) return alert("Enter an IP Address");
        $(this).prop('disabled', true).text('Scanning...');
        $.post('/start', {ip: ip});
    });

    function poll() {
        $.get('/data', function(data) {
            $('#progress-bar').css('width', data.progress + '%');
            $('#open_count').text(data.open_ports.length);
            $('#closed_total').text(data.closed_count);
            
            if(data.is_scanning) {
                $('#status').text("Current Port: " + data.current_port + " (" + data.progress + "%)");
            } else if(data.progress == 100) {
                $('#status').text("Scan Complete!");
                $('#scan_btn').prop('disabled', false).text('START FULL SCAN');
            }

            let openHtml = "";
            data.open_ports.forEach(p => {
                openHtml += `<div class="item open"><span>Port ${p}</span><span>OPEN</span></div>`;
            });
            $('#open_list').html(openHtml);

            let closedHtml = "";
            data.last_closed.forEach(p => {
                closedHtml += `<div class="item closed"><span>Port ${p}</span><span>CLOSED</span></div>`;
            });
            $('#closed_list').html(closedHtml);
        });
    }
    setInterval(poll, 1000);
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
    # For local testing
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
