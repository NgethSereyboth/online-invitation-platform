"""Credential-free development backend for Sovan Invite Studio."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote
from pathlib import Path
import base64, hashlib, hmac, json, re, secrets, sqlite3, time, uuid

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
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, salt TEXT NOT NULL, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, draft_json TEXT NOT NULL, updated_at INTEGER NOT NULL, owner_id TEXT);
    CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, version INTEGER NOT NULL, document_json TEXT NOT NULL, published_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS rsvps(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL, guest_count INTEGER NOT NULL, note TEXT, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL);
    """)
    columns={row["name"] for row in db.execute("PRAGMA table_info(invitations)")}
    if "owner_id" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN owner_id TEXT")
    return db

def clean_slug(value):
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return value[:60] or "our-invitation"

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),210_000).hex()

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
    def user(self):
        header=self.headers.get("Authorization","")
        if not header.startswith("Bearer "): return None
        token_hash=hashlib.sha256(header[7:].encode()).hexdigest(); now=int(time.time()*1000)
        with connect() as db:
            return db.execute("SELECT u.id,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?",(token_hash,now)).fetchone()
    def require_user(self):
        user=self.user()
        if not user:self.json(401,{"error":"Authentication required"})
        return user
    def owns(self, db, invite_id, user_id):
        return db.execute("SELECT 1 FROM invitations WHERE id=? AND owner_id=?",(invite_id,user_id)).fetchone() is not None
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health": return self.json(200, {"ok": True, "storage": "sqlite"})
        if path == "/api/auth/me":
            user=self.user(); return self.json(200,{"user":dict(user) if user else None})
        if path == "/api/invitations": return self.list_invitations()
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
            if path == "/api/auth/register": return self.register()
            if path == "/api/auth/login": return self.login()
            if path == "/api/auth/logout": return self.logout()
            if path == "/api/invitations": return self.create_invitation()
            if path.startswith("/api/invitations/") and path.endswith("/publish"): return self.publish(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets"): return self.upload(path.split("/")[3])
            if path.startswith("/api/public/") and path.endswith("/rsvps"): return self.rsvp(unquote(path.split("/")[3]))
            self.json(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc: self.json(400, {"error": str(exc)})
    def register(self):
        data=self.body(100_000); email=str(data.get("email","")).strip().lower()[:254]; password=str(data.get("password",""))
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):raise ValueError("Valid email required")
        if len(password)<8:raise ValueError("Password must be at least 8 characters")
        user_id=str(uuid.uuid4()); salt=secrets.token_hex(16); now=int(time.time()*1000)
        try:
            with connect() as db: db.execute("INSERT INTO users VALUES(?,?,?,?,?)",(user_id,email,password_hash(password,salt),salt,now))
        except sqlite3.IntegrityError:return self.json(409,{"error":"An account with this email already exists"})
        self.create_session(user_id,email)
    def login(self):
        data=self.body(100_000); email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
        with connect() as db: row=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if not row or not hmac.compare_digest(row["password_hash"],password_hash(password,row["salt"])):return self.json(401,{"error":"Incorrect email or password"})
        self.create_session(row["id"],row["email"])
    def create_session(self,user_id,email):
        token=secrets.token_urlsafe(32); now=int(time.time()*1000); expires=now+30*24*60*60*1000
        with connect() as db: db.execute("INSERT INTO sessions VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),user_id,expires,now))
        self.json(201,{"token":token,"user":{"id":user_id,"email":email},"expiresAt":expires})
    def logout(self):
        header=self.headers.get("Authorization","")
        if header.startswith("Bearer "):
            with connect() as db: db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(header[7:].encode()).hexdigest(),))
        self.json(200,{"signedOut":True})
    def list_invitations(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT i.id,i.slug,i.updated_at,CASE WHEN EXISTS(SELECT 1 FROM publications p WHERE p.invitation_id=i.id) THEN 'Published' ELSE 'Draft' END status,(SELECT COUNT(*) FROM rsvps r WHERE r.invitation_id=i.id) rsvps,i.draft_json FROM invitations i WHERE i.owner_id=? ORDER BY i.updated_at DESC",(user["id"],)).fetchall()
        result=[]
        for row in rows:
            draft=json.loads(row["draft_json"]); result.append({"id":row["id"],"slug":row["slug"],"title":draft.get("fields",{}).get("names","Untitled invitation"),"status":row["status"],"rsvps":row["rsvps"],"updatedAt":row["updated_at"]})
        self.json(200,result)
    def create_invitation(self):
        user=self.require_user()
        if not user:return
        data = self.body(); invite_id = str(uuid.uuid4()); slug = clean_slug(data.get("slug", "our-invitation")); now = int(time.time()*1000)
        with connect() as db:
            base=slug; n=2
            while db.execute("SELECT 1 FROM invitations WHERE slug=?",(slug,)).fetchone(): slug=f"{base}-{n}"; n+=1
            db.execute("INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id) VALUES(?,?,?,?,?)",(invite_id,slug,json.dumps(data.get("document",{})),now,user["id"]))
        self.json(201,{"id":invite_id,"slug":slug})
    def save_draft(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(); now=int(time.time()*1000)
        with connect() as db:
            changed=db.execute("UPDATE invitations SET draft_json=?,updated_at=? WHERE id=? AND owner_id=?",(json.dumps(data.get("document",{})),now,invite_id,user["id"])).rowcount
        self.json(200 if changed else 404,{"saved":bool(changed),"updatedAt":now})
    def publish(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(); now=int(time.time()*1000); pub_id=str(uuid.uuid4())
        with connect() as db:
            row=db.execute("SELECT slug,draft_json FROM invitations WHERE id=? AND owner_id=?",(invite_id,user["id"])).fetchone()
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
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT * FROM rsvps WHERE invitation_id=? ORDER BY created_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(r) for r in rows])
    def get_versions(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,version,published_at FROM publications WHERE invitation_id=? ORDER BY published_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(r) for r in rows])
    def upload(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
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
