from http.server import HTTPServer


class Server():
    def __init__(self, port: int, handler) -> None: # Not sure the type for handler
            self.handler = handler
            self.port = port

    def run(self) -> None:
        server_address = ('', self.port)
        httpd = HTTPServer(server_address, self.handler)
        print("Serving at port", self.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        print("Closing ...")
        httpd.server_close()