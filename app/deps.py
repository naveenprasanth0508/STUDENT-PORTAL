import os
from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from fastapi import Cookie, Depends, HTTPException
from .db import get_db
from .models import User

SECRET = os.environ["JWT_SECRET"]

def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def check_pw(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())

def make_token(uid: int) -> str:
    return jwt.encode({"sub": str(uid), "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, "HS256")

def current_user(session: str | None = Cookie(None), db=Depends(get_db)) -> User:
    try:
        uid = int(jwt.decode(session, SECRET, ["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Not authenticated")
    u = db.get(User, uid)
    if not u:
        raise HTTPException(401, "Not authenticated")
    return u

def admin_only(u: User = Depends(current_user)) -> User:
    if u.role != "admin":
        raise HTTPException(403, "Forbidden")
    return u

def student_only(u: User = Depends(current_user)) -> User:
    if u.role != "student":
        raise HTTPException(403, "Forbidden")
    return u
