import http.server
import socketserver
import webbrowser
import threading
import os
import time

PORT = 8000
DIRECTORY = "/Users/will/Documents/MoodleExport/python_sql_workflow"

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
        
    # Silence standard logging to keep the terminal clean
    def log_message(self, format, *args):
        pass

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
        print(f"Dashboard server started at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()

if __name__ == "__main__":
    # Start server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait a tiny bit for the server to bind
    time.sleep(0.5)
    
    # Open the user's default browser to the dashboard index
    dashboard_url = f"http://localhost:{PORT}/dashboard/index.html"
    print(f"Opening browser to {dashboard_url} ...")
    webbrowser.open(dashboard_url)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
