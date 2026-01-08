# -*- coding: utf-8 -*-
import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:8000/chat',
    data=json.dumps({'message':'Hello'}).encode('utf-8'),
    headers={'Content-Type':'application/json'}
)
print(json.load(urllib.request.urlopen(req)))
