import os, pathlib, uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import String, case, cast, func, or_, select
from starlette.exceptions import HTTPException as StarletteHTTPException
from .db import Base, engine, get_db
from .deps import admin_only, check_pw, current_user, make_token, student_only
from .models import Note, Reply, Request, Timeline, User, now

Status = Literal["Pending", "In Progress", "Resolved", "Rejected"]
Category = Literal["Academic", "Fee", "Certificate", "Hostel", "Other"]
Priority = Literal["Low", "Medium", "High"]
MAX_FILE = 2 * 1024 * 1024
MAGIC = {"application/pdf": (b"%PDF", ".pdf"), "image/png": (b"\x89PNG", ".png"), "image/jpeg": (b"\xff\xd8\xff", ".jpg")}
UPLOADS = pathlib.Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(title="Student Portal API")
Base.metadata.create_all(engine)  # dev convenience; use Alembic migrations in production

# Demo data for a serverless deployment that starts with an empty SQLite database.
from .db import SessionLocal
from .deps import hash_pw
with SessionLocal() as _seed_db:
    if not _seed_db.scalar(select(User).limit(1)):
        _seed_db.add_all([
            User(name="Admin Alice", email="admin@example.com", role="admin",
                 password_hash=hash_pw(os.getenv("SEED_ADMIN_PASSWORD", "Admin@12345"))),
            User(name="Sam Student", email="student@example.com", role="student",
                 password_hash=hash_pw(os.getenv("SEED_STUDENT_PASSWORD", "Student@12345"))),
        ])
        _seed_db.commit()

# The frontend expects {"message": "..."} for every error.
@app.exception_handler(StarletteHTTPException)
async def http_err(_, e):
    return JSONResponse({"message": e.detail}, e.status_code)

@app.exception_handler(RequestValidationError)
async def val_err(_, e):
    x = e.errors()[0]
    return JSONResponse({"message": f"{'.'.join(str(p) for p in x['loc'][1:])}: {x['msg']}"}, 422)

def user_out(u): return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}

def ser(r: Request, admin: bool, full: bool = True) -> dict:
    d = {"id": r.id, "subject": r.subject, "category": r.category, "priority": r.priority, "status": r.status,
         "description": r.description, "studentId": r.student_id, "studentName": r.student.name,
         "createdAt": r.created_at, "updatedAt": r.updated_at, "assignedTo": r.assigned_to, "archived": r.archived,
         "attachment": {"name": r.attachment_name, "size": r.attachment_size, "type": r.attachment_type} if r.attachment_name else None}
    if full:
        d["replies"] = [{"id": p.id, "author": p.author, "role": "admin", "message": p.message, "createdAt": p.created_at} for p in r.replies]
        d["timeline"] = [{"status": t.status, "at": t.at, "by": t.by} for t in r.timeline]
        if admin:  # internal notes are NEVER sent to students
            d["notes"] = [{"id": n.id, "author": n.author, "text": n.text, "createdAt": n.created_at} for n in r.notes]
    return d

def get_req(db, u, id: int) -> Request:
    r = db.get(Request, id)
    if not r or (u.role == "student" and r.student_id != u.id):  # ownership check
        raise HTTPException(404, "Request not found")
    return r

# ---------- auth ----------
class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=1, max_length=64)
    role: Literal["student", "admin"]

@app.post("/api/auth/login")
def login(b: LoginIn, res: Response, db=Depends(get_db)):
    u = db.scalar(select(User).where(User.email == b.email.strip().lower()))
    if not u or u.role != b.role or not check_pw(b.password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")
    res.set_cookie("session", make_token(u.id), httponly=True, samesite="lax", max_age=8 * 3600,
                   secure=os.getenv("COOKIE_SECURE", "false") == "true")
    return {"user": user_out(u)}

@app.post("/api/auth/logout", status_code=204)
def logout():
    res = Response(status_code=204)
    res.delete_cookie("session")
    return res

@app.get("/api/auth/me")
def me(u: User = Depends(current_user)):
    return {"user": user_out(u)}

# ---------- requests ----------
@app.get("/api/requests")
def list_requests(u: User = Depends(current_user), db=Depends(get_db), search: str = "", status: str = "",
                  category: str = "", priority: str = "", from_: date | None = Query(None, alias="from"),
                  to: date | None = None, sort: str = "createdAt", order: Literal["asc", "desc"] = "desc",
                  page: int = Query(1, ge=1), pageSize: int = Query(5, ge=1, le=100), archived: bool = False):
    conds = []
    if u.role == "student": conds.append(Request.student_id == u.id)
    if not archived: conds.append(Request.archived.is_(False))
    if search:
        s = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conds.append(or_(Request.subject.ilike(f"%{s}%", escape="\\"), User.name.ilike(f"%{s}%", escape="\\"),
                         cast(Request.id, String).ilike(f"%{s}%", escape="\\")))
    for col, val in ((Request.status, status), (Request.category, category), (Request.priority, priority)):
        if val: conds.append(col == val)
    if from_: conds.append(Request.created_at >= datetime.combine(from_, time.min, timezone.utc))
    if to: conds.append(Request.created_at < datetime.combine(to + timedelta(days=1), time.min, timezone.utc))
    cols = {"subject": Request.subject, "studentName": User.name, "category": Request.category, "status": Request.status,
            "priority": case({"Low": 1, "Medium": 2, "High": 3}, value=Request.priority), "createdAt": Request.created_at}
    col = cols.get(sort, Request.created_at)
    join = (Request.student_id == User.id)
    total = db.scalar(select(func.count()).select_from(Request).join(User, join).where(*conds))
    rows = db.scalars(select(Request).join(User, join).where(*conds)
                      .order_by(col.asc() if order == "asc" else col.desc(), Request.id.desc())
                      .offset((page - 1) * pageSize).limit(pageSize)).unique().all()
    return {"items": [ser(r, False, False) for r in rows], "total": total, "page": page, "pageSize": pageSize}

@app.get("/api/requests/{id}")
def get_request(id: int, u: User = Depends(current_user), db=Depends(get_db)):
    return ser(get_req(db, u, id), u.role == "admin")

async def save_upload(f: UploadFile | None) -> dict:
    if not f or not f.filename: return {}
    spec = MAGIC.get(f.content_type)
    data = await f.read(MAX_FILE + 1)
    if len(data) > MAX_FILE: raise HTTPException(413, "File must be 2 MB or smaller.")
    if not spec or not data.startswith(spec[0]): raise HTTPException(400, "Only PDF, PNG or JPG files are allowed.")
    name = f"{uuid.uuid4().hex}{spec[1]}"  # never use the client's filename on disk
    (UPLOADS / name).write_bytes(data)
    return {"attachment_name": pathlib.Path(f.filename).name[:200], "attachment_type": f.content_type,
            "attachment_size": len(data), "attachment_path": name}

@app.post("/api/requests", status_code=201)
async def create_request(subject: str = Form(..., min_length=5, max_length=100), category: Category = Form(...),
                         priority: Priority = Form(...), description: str = Form(..., min_length=20, max_length=5000),
                         attachment: UploadFile | None = File(None), u: User = Depends(student_only), db=Depends(get_db)):
    r = Request(subject=subject.strip(), category=category, priority=priority, description=description.strip(),
                status="Pending", student_id=u.id, archived=False, **await save_upload(attachment))
    r.timeline.append(Timeline(status="Pending", by=u.name))
    db.add(r); db.commit()
    return ser(r, False)

class PatchIn(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    assignedTo: str | None = Field(None, max_length=100)
    archived: bool | None = None

@app.patch("/api/requests/{id}")
def patch_request(id: int, b: PatchIn, u: User = Depends(admin_only), db=Depends(get_db)):
    r, d = get_req(db, u, id), b.model_dump(exclude_unset=True)
    if d.get("status") and d["status"] != r.status:
        r.timeline.append(Timeline(status=d["status"], by=u.name))
    for k, attr in (("status", "status"), ("priority", "priority"), ("archived", "archived")):
        if d.get(k) is not None: setattr(r, attr, d[k])
    if "assignedTo" in d: r.assigned_to = d["assignedTo"]  # null = unassign
    r.updated_at = now()
    db.commit()
    return ser(r, True)

class ReplyIn(BaseModel):
    message: str = Field(min_length=2, max_length=5000)

class NoteIn(BaseModel):
    text: str = Field(min_length=2, max_length=5000)

@app.post("/api/requests/{id}/replies", status_code=201)
def add_reply(id: int, b: ReplyIn, u: User = Depends(admin_only), db=Depends(get_db)):
    r = get_req(db, u, id)
    r.replies.append(Reply(author=u.name, message=b.message.strip())); r.updated_at = now()
    db.commit()
    return ser(r, True)

@app.post("/api/requests/{id}/notes", status_code=201)
def add_note(id: int, b: NoteIn, u: User = Depends(admin_only), db=Depends(get_db)):
    r = get_req(db, u, id)
    r.notes.append(Note(author=u.name, text=b.text.strip())); r.updated_at = now()
    db.commit()
    return ser(r, True)

@app.delete("/api/requests/{id}", status_code=204)
def delete_request(id: int, u: User = Depends(admin_only), db=Depends(get_db)):
    r = get_req(db, u, id)
    path = r.attachment_path
    db.delete(r); db.commit()
    if path: (UPLOADS / path).unlink(missing_ok=True)
    return Response(status_code=204)

@app.get("/api/requests/{id}/attachment")
def download(id: int, u: User = Depends(current_user), db=Depends(get_db)):
    r = get_req(db, u, id)
    if not r.attachment_path: raise HTTPException(404, "No attachment")
    return FileResponse(UPLOADS / r.attachment_path, media_type=r.attachment_type, filename=r.attachment_name,
                        content_disposition_type="attachment")

# ---------- misc ----------
@app.get("/api/admins")
def admins(u: User = Depends(admin_only), db=Depends(get_db)):
    return [{"id": a.id, "name": a.name} for a in db.scalars(select(User).where(User.role == "admin").order_by(User.name))]

@app.get("/api/stats")
def stats(u: User = Depends(current_user), db=Depends(get_db)):
    conds = [Request.archived.is_(False)] + ([Request.student_id == u.id] if u.role == "student" else [])
    counts = dict(db.execute(select(Request.status, func.count()).where(*conds).group_by(Request.status)).all())
    recent = db.scalars(select(Request).where(*conds).order_by(Request.updated_at.desc()).limit(5)).unique().all()
    return {"total": sum(counts.values()), "counts": counts, "recent": [ser(r, False, False) for r in recent]}
