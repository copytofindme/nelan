import os
import re
import sys
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler

class RangeRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler supporting Byte Range requests (HTTP 206), required by iOS Safari."""
    
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        
        fs = os.fstat(f.fileno())
        total_length = fs.st_size
        range_header = self.headers.get('Range')
        
        if range_header:
            match = re.match(r'^bytes=(\d*)-(\d*)$', range_header.strip())
            if match:
                first, last = match.groups()
                first = int(first) if first else 0
                last = int(last) if last else total_length - 1
                if last >= total_length:
                    last = total_length - 1
                if first > last or first >= total_length:
                    self.send_error(HTTPStatus.RANGE_NOT_SATISFIABLE)
                    f.close()
                    return None
                
                length = last - first + 1
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Content-Range', f'bytes {first}-{last}/{total_length}')
                self.send_header('Content-Length', str(length))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                f.seek(first)
                return RangeFileWrapper(f, length)
        
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Length', str(total_length))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        return f

class RangeFileWrapper:
    def __init__(self, file, length):
        self.file = file
        self.length = length
        self.bytes_read = 0

    def read(self, size=-1):
        if self.bytes_read >= self.length:
            return b""
        if size < 0 or size > (self.length - self.bytes_read):
            size = self.length - self.bytes_read
        data = self.file.read(size)
        self.bytes_read += len(data)
        return data

    def close(self):
        self.file.close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = '0.0.0.0'
    server_address = (host, port)
    
    # Switch working directory if specified
    if len(sys.argv) > 2:
        os.chdir(sys.argv[2])
        
    httpd = HTTPServer(server_address, RangeRequestHandler)
    print(f"Serving HTTP on {host}:{port} with Range support (iOS Safari compatible)...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
