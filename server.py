"""Credential-free development backend for Sovan Invite Studio."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote
from pathlib import Path
import base64, json, mimetypes, re, sqlite3, time, uuid

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UPLOADS = DATA / "uploads"
DB = DATA / "invites.db"
DATA.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, draft_json TEXT NOT NULL, updated_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, version INTEGER NOT NULL, document_json TEXT NOT NULL, published_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS rsvps(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL, guest_count INTEGER NOT NULL, note TEXT, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL);
    """)
    return db

def clean_slug(value):
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return value[:60] or "our-invitation"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()
    def json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self, limit=20_000_000):
        size = int(self.headers.get("Content-Length", "0"))
        if size > limit: raise ValueError("Request too large")
        return json.loads(self.rfile.read(size) or b"{}")
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health": return self.json(200, {"ok": True, "storage": "sqlite"})
        if path.startswith("/i/"): return self.serve_public(path.split("/", 2)[2])
        if path.startswith("/api/public/"): return self.get_public(unquote(path.split("/", 3)[3]))
        if path.startswith("/api/invitations/") and path.endswith("/rsvps"): return self.get_rsvps(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/versions"): return self.get_versions(path.split("/")[3])
        if path.startswith("/uploads/"):
            self.path = "/data" + path
        return super().do_GET()
    def do_PUT(self):
        path = urlparse(self.path).path
        if path.startswith("/api/invitations/"): return self.save_draft(path.split("/")[3])
        self.json(404, {"error": "Not found"})
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/invitations": return self.create_invitation()
            if path.startswith("/api/invitations/") and path.endswith("/publish"): return self.publish(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets"): return self.upload(path.split("/")[3])
            if path.startswith("/api/public/") and path.endswith("/rsvps"): return self.rsvp(unquote(path.split("/")[3]))
            self.json(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc: self.json(400, {"error": str(exc)})
    def create_invitation(self):
        data = self.body(); invite_id = str(uuid.uuid4()); slug = clean_slug(data.get("slug", "our-invitation")); now = int(time.time()*1000)
        with connect() as db:
            base=slug; n=2
            while db.execute("SELECT 1 FROM invitations WHERE slug=?",(slug,)).fetchone(): slug=f"{base}-{n}"; n+=1
            db.execute("INSERT INTO invitations VALUES(?,?,?,?)",(invite_id,slug,json.dumps(data.get("document",{})),now))
        self.json(201,{"id":invite_id,"slug":slug})
    def save_draft(self, invite_id):
        data=self.body(); now=int(time.time()*1000)
        with connect() as db:
            changed=db.execute("UPDATE invitations SET draft_json=?,updated_at=? WHERE id=?",(json.dumps(data.get("document",{})),now,invite_id)).rowcount
        self.json(200 if changed else 404,{"saved":bool(changed),"updatedAt":now})
    def publish(self, invite_id):
        data=self.body(); now=int(time.time()*1000); pub_id=str(uuid.uuid4())
        with connect() as db:
            row=db.execute("SELECT slug,draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            document=data.get("document") or json.loads(row["draft_json"]); db.execute("INSERT INTO publications VALUES(?,?,?,?,?)",(pub_id,invite_id,now,json.dumps(document),now))
        self.json(201,{"publicationId":pub_id,"version":now,"slug":row["slug"],"url":f"/i/{row['slug']}"})
    def get_public(self, slug):
        with connect() as db:
            row=db.execute("SELECT i.id,p.id publication_id,p.version,p.document_json FROM invitations i JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? ORDER BY p.published_at DESC LIMIT 1",(slug,)).fetchone()
        if not row:return self.json(404,{"error":"Published invitation not found"})
        self.json(200,{"invitationId":row["id"],"publicationId":row["publication_id"],"version":row["version"],"document":json.loads(row["document_json"])})
    def rsvp(self, slug):
        data=self.body(100_000); name=str(data.get("name","")).strip()[:120]
        if not name:raise ValueError("Name is required")
        count=max(1,min(10,int(data.get("count",1))))
        with connect() as db:
            pub=db.execute("SELECT i.id invitation_id,p.id publication_id FROM invitations i JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? ORDER BY p.published_at DESC LIMIT 1",(slug,)).fetchone()
            if not pub:return self.json(404,{"error":"Invitation not found"})
            rid=str(uuid.uuid4()); db.execute("INSERT INTO rsvps VALUES(?,?,?,?,?,?,?,?)",(rid,pub["invitation_id"],pub["publication_id"],name,str(data.get("status","Maybe"))[:40],count,str(data.get("note",""))[:1000],int(time.time()*1000)))
        self.json(201,{"id":rid,"saved":True})
    def get_rsvps(self, invite_id):
        with connect() as db: rows=db.execute("SELECT * FROM rsvps WHERE invitation_id=? ORDER BY created_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(r) for r in rows])
    def get_versions(self, invite_id):
        with connect() as db: rows=db.execute("SELECT id,version,published_at FROM publications WHERE invitation_id=? ORDER BY published_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(r) for r in rows])
    def upload(self, invite_id):
        data=self.body(); raw=base64.b64decode(data["base64"],validate=True); mime=str(data.get("mime","application/octet-stream")); allowed={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif","audio/mpeg":".mp3","audio/mp4":".m4a"}
        if mime not in allowed:raise ValueError("Unsupported material type")
        if len(raw)>15_000_000:raise ValueError("Material exceeds 15 MB")
        aid=str(uuid.uuid4()); filename=aid+allowed[mime]; (UPLOADS/filename).write_bytes(raw)
        with connect() as db: db.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?)",(aid,invite_id,str(data.get("name","upload"))[:180],mime,filename,len(raw),int(time.time()*1000)))
        self.json(201,{"id":aid,"url":f"/uploads/{filename}","size":len(raw)})
    def serve_public(self, slug):
        page=(ROOT/"public.html").read_text(encoding="utf-8").replace("__INVITATION_SLUG__",slug)
        body=page.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

if __name__ == "__main__":
    print("Sovan Invite Studio: http://127.0.0.1:4175")
    ThreadingHTTPServer(("127.0.0.1",4175),Handler).serve_forever()
