import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local static file server with CORS headers.")
    parser.add_argument(
        "--root",
        required=True,
        help="Directory to serve, for example DATA_PATH.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument(
        "--allow-origin",
        default="http://127.0.0.1:8080",
        help="CORS allow origin. Use * only for local debugging.",
    )
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    os.chdir(root)

    allow_origin = args.allow_origin

    class CORSRequestHandler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", allow_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.end_headers()

    server = ThreadingHTTPServer((args.host, args.port), CORSRequestHandler)
    print(f"Serving: {root}")
    print(f"URL: http://{args.host}:{args.port}")
    print(f"Allow-Origin: {allow_origin}")
    server.serve_forever()


if __name__ == "__main__":
    main()

