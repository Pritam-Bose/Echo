# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient
import api.routes as r

client = TestClient(r.app)
resp = client.post('/chat', json={'message':'Hello'})
print(resp.status_code)
print(resp.json())
