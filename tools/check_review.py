"""Check a published review package using an isolated local server and data folder."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGMwS+wEAAHxASHduAJkAAAAAElFTkSuQmCC')


def request(url, fields=None, images=(), review_header=True):
    if fields is None:
        req = Request(url)
    else:
        boundary = uuid4().hex
        parts = []
        for field, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
        for filename, content_type, data in images:
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="images"; filename="{filename}"\r\n'
                          f'Content-Type: {content_type}\r\n\r\n').encode() + data + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
        if review_header:
            headers['X-Handbook-Review'] = '1'
        req = Request(url, data=b''.join(parts), headers=headers)
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, response.headers.get_content_type(), response.read()
    except HTTPError as error:
        with error:
            return error.code, error.headers.get_content_type(), error.read()


@contextmanager
def serve(bundle, scratch):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}/'
    env = dict(os.environ, Review__DataDirectory=str(scratch / 'data'))
    log_path = scratch / 'server.log'
    with log_path.open('wb') as log:
        launcher = [str(bundle / 'ReviewServer.exe')] if os.name == 'nt' and (bundle / 'hostfxr.dll').exists() else ['dotnet', 'ReviewServer.dll']
        server = subprocess.Popen([*launcher, '--urls', base],
                                  cwd=bundle, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(50):
                if server.poll() is not None:
                    break
                try:
                    if request(base)[0] == 200:
                        break
                except (URLError, TimeoutError, OSError):
                    time.sleep(0.1)
            else:
                raise RuntimeError('Review server did not become ready.')
            if server.poll() is not None:
                raise RuntimeError('Review server exited before becoming ready.')
            yield base
        except Exception:
            log.flush()
            print(log_path.read_text(encoding='utf-8', errors='replace')[-4000:])
            raise
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


def expect(result, expected):
    status, content_type, body = result
    assert status == expected, (status, expected, body[:500])
    return json.loads(body) if content_type == 'application/json' else body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not (bundle / 'ReviewServer.dll').is_file():
        parser.error('Point to the published folder printed by tools/build_review.py.')
    first = dict(page='index', section='check-out-and-return', author='Reviewer One', text='Test screenshot')
    list_url = 'api/comments?page=index'
    with tempfile.TemporaryDirectory(prefix='handbook-review-check-') as scratch_name:
        scratch = Path(scratch_name)
        with serve(bundle, scratch) as base:
            chapters = ('index', 'sailing-skills', 'equipment-reference')
            for page in chapters:
                html = expect(request(base + page + '.html'), 200)
                assert f'name="handbook-review-page" content="{page}"'.encode() in html
                assert b'assets/review.js' in html and b'assets/review.css' in html
                plain_html = (Path(__file__).resolve().parents[1] / 'dist' / (page + '.html')).read_bytes()
                assert b'handbook-review-page' not in plain_html and b'assets/review.js' not in plain_html
            expect(request(base + 'assets/review.js'), 200)
            expect(request(base + 'assets/review.css'), 200)
            expect(request(base + 'chapters.json'), 404)
            assert expect(request(base + list_url), 200) == []
            no_header = request(base + 'api/comments', first, review_header=False)
            assert no_header[0] in (400, 403), no_header[0]
            wrong_chapter = request(base + 'api/comments', dict(first, page='equipment-reference'))
            expect(wrong_chapter, 400)
            rejected = request(base + 'api/comments', first, [('fake.png', 'image/png', b'<svg/>')])
            assert rejected[0] in (400, 415), rejected[0]
            assert expect(request(base + list_url), 200) == []
            root = expect(request(base + 'api/comments', first, [('screen.png', 'image/png', PNG)]), 201)
            assert root['author'] == first['author'] and root['section'] == first['section']
            assert root['parentId'] is None and len(root['images']) == 1
            image_url = 'api/images/' + root['images'][0]['id']
            assert request(base + image_url) == (200, 'image/png', PNG)
            reply = expect(request(base + 'api/comments', dict(first, parentId=root['id'], author='Reviewer Two', text='Reply')), 201)
            assert reply['parentId'] == root['id'] and reply['author'] != root['author']
            other = expect(request(base + 'api/comments', dict(first, page='sailing-skills', section='page', text=''),
                                   [('screen.png', 'image/png', PNG)]), 201)
            assert other['section'] == 'page' and other['images']
            with ThreadPoolExecutor(max_workers=4) as executor:
                extra = list(executor.map(lambda i: expect(request(base + 'api/comments', dict(first, text=f'Parallel {i}')), 201), range(4)))
            expected_ids = {root['id'], reply['id'], *(post['id'] for post in extra)}
            assert len(expected_ids) == 6
            assert {post['id'] for post in expect(request(base + list_url), 200)} == expected_ids
            assert [post['id'] for post in expect(request(base + 'api/comments?page=sailing-skills'), 200)] == [other['id']]
        with serve(bundle, scratch) as base:
            assert {post['id'] for post in expect(request(base + list_url), 200)} == expected_ids
            assert request(base + image_url) == (200, 'image/png', PNG)
    print('Review package passed: isolated files, posting, reply, image-only post, image validation, concurrent IDs and restart persistence.')


if __name__ == '__main__':
    main()
