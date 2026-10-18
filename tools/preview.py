"""Serve the generated handbook on this computer using only standard Python."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = root / 'dist'
    if not (directory / 'index.html').is_file():
        parser.error('Build the handbook first: python tools/build.py')
    # Some Windows MIME registries call WebP a download rather than an image.
    SimpleHTTPRequestHandler.extensions_map['.webp'] = 'image/webp'
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Handbook preview: http://127.0.0.1:{server.server_port}/', flush=True)
        print('Press Ctrl+C to stop. This serves only on this computer.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
