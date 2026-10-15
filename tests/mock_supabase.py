"""Tiny in-memory stand-in for the Supabase endpoints the game uses. Test-only."""
import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANON_KEY = "test-anon-key"
tokens = {}  # access token -> user id
refresh = {}  # refresh token -> user id
saves = {}  # user id -> (data, version, lifetime, updated_at)


def issue(user_id):
    access, ref = uuid.uuid4().hex, uuid.uuid4().hex
    tokens[access] = user_id
    refresh[ref] = user_id
    return {"access_token": access, "refresh_token": ref, "expires_in": 3600,
            "user": {"id": user_id, "is_anonymous": True}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def user(self):
        token = self.headers.get("Authorization", "").removeprefix("Bearer ")
        return tokens.get(token)

    def do_POST(self):
        if self.headers.get("apikey") != ANON_KEY:
            return self.reply(401, {"message": "Invalid API key"})
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/auth/v1/signup":
            return self.reply(200, issue(str(uuid.uuid4())))
        if self.path == "/auth/v1/token?grant_type=refresh_token":
            uid = refresh.pop(body.get("refresh_token"), None)
            if uid is None:
                return self.reply(400, {"error_description": "Invalid Refresh Token"})
            return self.reply(200, issue(uid))
        if self.path == "/auth/v1/token?grant_type=password":
            return self.reply(400, {"error_description": "Invalid login credentials"})
        uid = self.user()
        if uid is None:
            return self.reply(401, {"message": "JWT expired"})
        if self.path == "/rest/v1/rpc/save_game":
            saves[uid] = (body["p_data"], body["p_save_version"], body["p_lifetime_coins"], time.time())
            return self.reply(200, "ok")
        if self.path == "/rest/v1/rpc/load_game":
            if uid not in saves:
                return self.reply(200, [])
            data, version, lifetime, at = saves[uid]
            return self.reply(200, [{"data": data, "save_version": version, "lifetime_coins": lifetime,
                                     "elapsed_seconds": time.time() - at}])
        self.reply(404, {"message": "not found"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
