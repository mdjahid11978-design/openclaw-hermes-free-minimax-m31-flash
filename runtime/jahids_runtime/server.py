"""Standard-library HTTP API; write and mission-read endpoints require bearer auth."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .service import MissionService

class Handler(BaseHTTPRequestHandler):
    service = MissionService()
    def send_json(self,status,payload):
        data=json.dumps(payload,default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data)))
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        self.wfile.write(data)
    def authorized(self):
        token=os.getenv("JAHIDS_API_TOKEN","")
        return bool(token) and hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+token)
    def body(self):
        length=int(self.headers.get("Content-Length","0"))
        if length<0 or length>16000: raise ValueError("body must be at most 16000 bytes")
        if length == 0: return {}
        payload=json.loads(self.rfile.read(length))
        if not isinstance(payload,dict): raise ValueError("JSON body must be an object")
        return payload
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/healthz": return self.send_json(200,{"status":"ok","service":"jahids-agent-runtime","version":"0.1.0"})
        if not self.authorized(): return self.send_json(401,{"error":"unauthorized"})
        if path=="/v1/missions": return self.send_json(200,{"missions":self.service.store.list()})
        if path.startswith("/v1/missions/"):
            mission=self.service.store.get(path.rsplit("/",1)[-1])
            return self.send_json(200 if mission else 404,mission or {"error":"not_found"})
        return self.send_json(404,{"error":"not_found"})
    def do_POST(self):
        if not self.authorized(): return self.send_json(401,{"error":"unauthorized"})
        path=urlparse(self.path).path
        try:
            body=self.body()
            if path=="/v1/missions":
                mission=self.service.create(body.get("provider","nvidia-nim"),body.get("prompt",""),body.get("category","model"))
                return self.send_json(201,{"mission":mission,"next":"POST /v1/missions/{id}/approve then /execute"})
            parts=path.strip("/").split("/")
            if len(parts)==4 and parts[:2]==["v1","missions"]:
                if parts[3]=="approve": result=self.service.approve(parts[2])
                elif parts[3]=="execute": result=self.service.execute(parts[2],body.get("approval_id",""))
                else: result=False
                return self.send_json(404 if result is None or result is False else 200,result or {"error":"not_found"})
            return self.send_json(404,{"error":"not_found"})
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            return self.send_json(400,{"error":str(exc)})
    def log_message(self,fmt,*args):
        print("jahids-runtime",self.address_string(),fmt%args)

def main():
    host=os.getenv("JAHIDS_HOST","127.0.0.1")
    port=int(os.getenv("JAHIDS_PORT","8787"))
    if host not in {"127.0.0.1","localhost"} and os.getenv("JAHIDS_ALLOW_REMOTE_BIND")!="true":
        raise SystemExit("remote bind blocked; enable only behind TLS/reverse proxy")
    server=ThreadingHTTPServer((host,port),Handler)
    print("JAHIDS.AI Agent Runtime listening on http://"+host+":"+str(port))
    server.serve_forever()

if __name__=="__main__": main()
