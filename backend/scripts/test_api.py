# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient
import api.routes as r

client = TestClient(r.app)
root_resp = client.get('/')
# root serves HTML; don't assume JSON
print('GET / ->', root_resp.status_code, 'content_type=', root_resp.headers.get('content-type'))
resp = client.post('/dream', json={'dream':'I lost someone in a jungle and felt scared'})
print('POST /dream ->', resp.status_code, resp.json())
