#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os, subprocess

class StatusHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        cpu = subprocess.check_output("cat /proc/loadavg", shell=True).decode().split()[0]
        mem = subprocess.check_output("free -m | awk 'NR==2{print int(\$3*100/\$2)}'", shell=True).decode().strip()
        backup = subprocess.check_output("ls -lh /backup/database/*.gz 2>/dev/null | tail -1 || echo 'No backup'", shell=True).decode()
        monit = subprocess.check_output("sudo monit summary", shell=True).decode()
        
        html = f"""
        <html><body>
        <h1>🏥 Healthcare Lab Dashboard</h1>
        <h2>System</h2><p>CPU: {cpu} | RAM: {mem}%</p>
        <h2>Backup</h2><pre>{backup}</pre>
        <h2>Monit</h2><pre>{monit}</pre>
        <iframe src="http://localhost:19999" width="100%" height="400"></iframe>
        </body></html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

if __name__ == '__main__':
    print("Dashboard at http://192.168.52.5:5000")
    HTTPServer(('0.0.0.0', 5000), StatusHandler).serve_forever()
