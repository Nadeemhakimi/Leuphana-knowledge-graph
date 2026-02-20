#!/usr/bin/env python3
"""
Simple HTTP server with SPARQL proxy for GraphDB.
Solves CORS issues when accessing GraphDB from the browser.

Usage:
    python server.py
    
Then open: http://localhost:8000
The SPARQL endpoint is proxied at: http://localhost:8000/sparql
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error
import json

# Add visualization directory to path so we can import nlq_chain
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GRAPHDB_ENDPOINT = "http://localhost:7200/repositories/leuphana-kg"

class CORSProxyHandler(SimpleHTTPRequestHandler):
    
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Proxy POST requests to GraphDB or handle NLQ"""
        if self.path == '/sparql':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            req = urllib.request.Request(
                GRAPHDB_ENDPOINT,
                data=post_data,
                headers={
                    'Content-Type': self.headers.get('Content-Type', 'application/x-www-form-urlencoded'),
                    'Accept': self.headers.get('Accept', 'application/sparql-results+json')
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = response.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/sparql-results+json')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(result)
                    print(f"  SPARQL query executed successfully")
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8', errors='ignore')
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': f'GraphDB error: {e.reason}',
                    'details': error_body
                }).encode())
                print(f"  GraphDB error: {e.code} {e.reason}")
            except urllib.error.URLError as e:
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Cannot connect to GraphDB',
                    'details': str(e.reason)
                }).encode())
                print(f"  Connection error: {e.reason}")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Server error',
                    'details': str(e)
                }).encode())
                print(f"  Error: {e}")

        elif self.path == '/ask':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                body = json.loads(post_data.decode('utf-8'))
                question = body.get('question', '').strip()

                if not question:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'error': 'No question provided',
                        'success': False
                    }).encode())
                    return

                print(f"  NLQ: \"{question}\"")

                from nlq_chain import ask_question
                result = ask_question(question)

                if result['success']:
                    self.send_response(200)
                    bindings = result.get('results', {}).get('results', {}).get('bindings', [])
                    print(f"  NLQ result: {len(bindings)} rows")
                else:
                    self.send_response(500)
                    print(f"  NLQ error: {result.get('error', 'Unknown')}")

                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Invalid JSON body',
                    'success': False
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': f'Server error: {str(e)}',
                    'success': False
                }).encode())
                print(f"  NLQ error: {e}")

        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        """Serve static files with CORS headers"""
        # Add CORS headers to all responses
        super().do_GET()
    
    def end_headers(self):
        # Add CORS headers to all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        if '/sparql' in str(args) or '/ask' in str(args):
            return  # Already logged above
        print(f"  {args[0]}")


def main():
    port = 8000
    server = HTTPServer(('', port), CORSProxyHandler)
    
    print("=" * 60)
    print("  Leuphana KG Visualization Server")
    print("=" * 60)
    print(f"  Static files:  http://localhost:{port}")
    print(f"  SPARQL proxy:  http://localhost:{port}/sparql")
    print(f"  NLQ endpoint:  http://localhost:{port}/ask")
    print(f"  GraphDB:       {GRAPHDB_ENDPOINT}")
    print("=" * 60)
    print("  Open http://localhost:8000 in your browser")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        server.shutdown()


if __name__ == '__main__':
    main()
