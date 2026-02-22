import socket
import json
import time
from flask import Flask, render_template, Response, stream_with_context

# template_folder="." tells Flask to look in the same folder as app.py
app = Flask(__name__, template_folder=".")

TARGET_IP = "127.0.0.1"

def generate_scan_results():
    """Scans ports 1-1024 and streams findings live."""
    for port in range(1, 1025):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.05)
                result = s.connect_ex((TARGET_IP, port))
                
                # Only send data if the port is OPEN (result == 0)
                if result == 0:
                    data = json.dumps({"port": port, "status": "Open"})
                    yield f"data: {data}\n\n"
            
            # Tiny sleep to prevent CPU spikes
            time.sleep(0.01)
        except Exception:
            continue

@app.route('/')
def index():
    # Now it looks for index.html in the same folder
    return render_template('index.html')

@app.route('/stream')
def stream():
    return Response(stream_with_context(generate_scan_results()), 
                    mimetype='text/event-stream')

if __name__ == '__main__':
    # threaded=True is required for SSE live updates
    app.run(debug=True, port=5000, threaded=True)
