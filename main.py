import socket
import json
import time
from flask import Flask, render_template, Response

app = Flask(__name__)

# The Target (Change this to the IP you are authorized to scan)
TARGET_IP = "127.0.0.1"

def generate_scan_results():
    """
    Scans ports and yields results immediately to the frontend.
    """
    # Scanning a sample range; change to range(1, 65536) for a full scan
    for port in range(1, 1025):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.01) # Very fast timeout for local scanning
            result = s.connect_ex((TARGET_IP, port))
            
            if result == 0:
                # Format required for Server-Sent Events (SSE)
                data = json.dumps({"port": port, "status": "Open"})
                yield f"data: {data}\n\n"
        
        # Artificial tiny sleep so you can actually see the "live" flow
        time.sleep(0.01)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    # This route stays open and 'pipes' the generator to the browser
    return Response(generate_scan_results(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
