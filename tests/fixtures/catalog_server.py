"""Process fixture for the external JSON-RPC boundary; no Codex state touched."""
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    if 'id' not in request:
        continue
    method = request['method']
    if method == 'initialize':
        assert request['params']['capabilities']['experimentalApi'] is True
        result = {}
    elif method == 'project/list':
        pages = json.loads(open(sys.argv[1]).read())
        cursor = int(request['params'].get('cursor') or 0)
        result = {'data': pages[cursor], 'nextCursor': str(cursor+1) if cursor+1 < len(pages) else None}
    else:
        raise ValueError(method)
    print(json.dumps({'id': request['id'], 'result': result}), flush=True)
