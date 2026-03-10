import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import create_engine, String, Float, Text, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_URL = os.getenv("BASE_URL", "http://192.168.50.165:3180")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "/app/secrets/client.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "/app/secrets/token.json")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/app.db")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


class Base(DeclarativeBase):
    pass


class AppSetting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class ThesisLog(Base):
    __tablename__ = "thesis_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    hours: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(String(255))
    details: Mapped[str] = mapped_column(Text, default="")


engine = create_engine(DATABASE_URL, future=True)
Base.metadata.create_all(engine)

app = FastAPI(title="NAS Calendar + Thesis Hub")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
templates = Jinja2Templates(directory="/app/templates")


def get_setting(key: str):
    with Session(engine) as db:
        row = db.get(AppSetting, key)
        return row.value if row else None


def set_setting(key: str, value: str):
    with Session(engine) as db:
        row = db.get(AppSetting, key)
        if row:
            row.value = value
        else:
            db.add(AppSetting(key=key, value=value))
        db.commit()


def get_google_creds() -> Credentials:
    if not os.path.exists(TOKEN_FILE):
        raise HTTPException(status_code=401, detail=f"Google token file missing: {TOKEN_FILE}")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request as GRequest

        creds.refresh(GRequest())
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    connected = os.path.exists(TOKEN_FILE)
    with Session(engine) as db:
        logs = db.scalars(select(ThesisLog).order_by(ThesisLog.started_at.desc()).limit(20)).all()
    return templates.TemplateResponse("index.html", {"request": request, "connected": connected, "logs": logs, "base_url": BASE_URL, "token_file": TOKEN_FILE})


@app.get("/api/calendars")
def calendars():
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    data = svc.calendarList().list(maxResults=100).execute()
    items = [{"id": c["id"], "summary": c.get("summary", c["id"])} for c in data.get("items", [])]
    return {"items": items}


@app.get("/api/events")
def events(start: str, end: str):
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    cal_list = svc.calendarList().list(maxResults=100).execute().get("items", [])
    out = []
    for c in cal_list:
        cal_id = c["id"]
        cal_name = c.get("summary", cal_id)
        ev = svc.events().list(
            calendarId=cal_id,
            singleEvents=True,
            orderBy="startTime",
            timeMin=start,
            timeMax=end,
            maxResults=50,
        ).execute().get("items", [])
        for e in ev:
            out.append({
                "calendarId": cal_id,
                "calendar": cal_name,
                "id": e.get("id"),
                "summary": e.get("summary", "(no title)"),
                "start": e.get("start", {}),
                "end": e.get("end", {}),
            })
    return {"items": out}


@app.post("/api/events")
async def create_event(request: Request):
    body = await request.json()
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    created = svc.events().insert(calendarId=body["calendarId"], body={
        "summary": body["summary"],
        "description": body.get("description", ""),
        "start": {"dateTime": body["start"], "timeZone": body.get("timeZone", "Europe/Stockholm")},
        "end": {"dateTime": body["end"], "timeZone": body.get("timeZone", "Europe/Stockholm")},
    }).execute()
    return {"id": created.get("id"), "htmlLink": created.get("htmlLink")}


@app.delete("/api/events/{calendar_id}/{event_id}")
def delete_event(calendar_id: str, event_id: str):
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return JSONResponse({"ok": True})


@app.post("/api/thesis-log")
def add_thesis_log(started_at: str = Form(...), hours: float = Form(...), summary: str = Form(...), details: str = Form("")):
    dt = datetime.fromisoformat(started_at)
    with Session(engine) as db:
        db.add(ThesisLog(started_at=dt, hours=hours, summary=summary, details=details))
        db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/thesis-summary")
def thesis_summary(days: int = 7):
    cutoff = datetime.now() - timedelta(days=days)
    with Session(engine) as db:
        logs = db.scalars(select(ThesisLog).where(ThesisLog.started_at >= cutoff)).all()
    total = round(sum(l.hours for l in logs), 2)
    return {"days": days, "entries": len(logs), "hours": total}
