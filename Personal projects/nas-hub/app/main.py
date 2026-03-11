import json
import os
import urllib.parse
from datetime import datetime, timedelta, date
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
SCHEDULING_PROFILE_FILE = os.getenv("SCHEDULING_PROFILE_FILE", "/app/data/scheduling_profile.json")

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


def load_scheduling_profile() -> dict:
    profile = {
        "defaultCalendar": "eric.hm.berg@gmail.com",
        "routingRules": [],
        "avoidWriteCalendars": [],
        "timePreferences": {
            "earliestStart": "09:00",
            "latestEnd": "22:00",
            "latestEndUniversity": "18:00",
            "weekendAllowed": True,
            "avoidUniversityOnWeekends": True,
        },
        "defaultDurationsMin": {"general": 60, "university": 120},
        "conflictPolicy": {"mode": "suggest_then_ask", "autoMove": False},
        "privacyRouting": {"fallback": "eric.hm.berg@gmail.com"},
    }
    try:
        if os.path.exists(SCHEDULING_PROFILE_FILE):
            with open(SCHEDULING_PROFILE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                profile.update({k: v for k, v in loaded.items() if v is not None})
                if isinstance(loaded.get("timePreferences"), dict):
                    profile["timePreferences"].update(loaded["timePreferences"])
                if isinstance(loaded.get("defaultDurationsMin"), dict):
                    profile["defaultDurationsMin"].update(loaded["defaultDurationsMin"])
                if isinstance(loaded.get("conflictPolicy"), dict):
                    profile["conflictPolicy"].update(loaded["conflictPolicy"])
                if isinstance(loaded.get("privacyRouting"), dict):
                    profile["privacyRouting"].update(loaded["privacyRouting"])
    except Exception:
        pass
    return profile


def _is_university_related(body: dict) -> bool:
    if body.get("universityRelated") is True:
        return True
    txt = f"{body.get('summary', '')} {body.get('description', '')} {body.get('context', '')}".lower()
    markers = ["uni", "university", "chalmers", "lecture", "thesis", "kandidatarbete", "cobot"]
    return any(m in txt for m in markers)


def _choose_target_calendar(body: dict, profile: dict) -> str:
    provided = body.get("calendarId")
    if provided:
        return provided

    if _is_university_related(body):
        for rule in profile.get("routingRules", []):
            if rule.get("when") == "university_related" and rule.get("calendarId"):
                return rule["calendarId"]

    return profile.get("defaultCalendar", "eric.hm.berg@gmail.com")


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
def calendars(include_holidays: bool = False):
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    data = svc.calendarList().list(maxResults=100).execute()
    items = []
    for c in data.get("items", []):
        cid = c["id"]
        if not include_holidays and cid == "sv.swedish#holiday@group.v.calendar.google.com":
            continue
        items.append({"id": cid, "summary": c.get("summary", cid)})
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
                "description": e.get("description", ""),
                "start": e.get("start", {}),
                "end": e.get("end", {}),
                "recurrence": e.get("recurrence", []),
                "recurringEventId": e.get("recurringEventId"),
            })
    return {"items": out}


def _create_event(calendar_id: str, summary: str, description: str, start_dt: str, end_dt: str, tz: str = "Europe/Stockholm", recurrence_rule: str | None = None):
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    body = {
        "summary": summary,
        "description": description or "",
        "start": {"dateTime": start_dt, "timeZone": tz},
        "end": {"dateTime": end_dt, "timeZone": tz},
    }
    if recurrence_rule:
        body["recurrence"] = [recurrence_rule]
    created = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return created


@app.post("/api/events")
async def create_event(request: Request):
    body = await request.json()
    try:
        created = _create_event(
            body["calendarId"],
            body["summary"],
            body.get("description", ""),
            body["start"],
            body["end"],
            body.get("timeZone", "Europe/Stockholm"),
            body.get("recurrenceRule"),
        )
        return {"id": created.get("id"), "htmlLink": created.get("htmlLink")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Create event failed: {e}")


@app.post("/events/create")
def create_event_form(
    calendarId: str = Form(...),
    summary: str = Form(...),
    description: str = Form(""),
    start_local: str = Form(...),
    end_local: str = Form(...),
    recurrence_rule: str = Form(""),
):
    try:
        created = _create_event(
            calendarId,
            summary,
            description,
            f"{start_local}:00",
            f"{end_local}:00",
            "Europe/Stockholm",
            recurrence_rule or None,
        )
        return RedirectResponse(url=f"/?created={created.get('id')}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?error={urllib.parse.quote(str(e))}", status_code=303)


@app.put("/api/events/{calendar_id}/{event_id}")
async def update_event(calendar_id: str, event_id: str, request: Request):
    body = await request.json()
    apply_series = bool(body.get("applySeries"))
    target_event_id = body.get("seriesEventId") if apply_series and body.get("seriesEventId") else event_id

    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    try:
        patch_body = {
            "summary": body.get("summary", ""),
            "description": body.get("description", ""),
            "start": {"dateTime": body.get("start"), "timeZone": body.get("timeZone", "Europe/Stockholm")},
            "end": {"dateTime": body.get("end"), "timeZone": body.get("timeZone", "Europe/Stockholm")},
        }
        recurrence_rule = body.get("recurrenceRule")
        if recurrence_rule is not None:
            patch_body["recurrence"] = [recurrence_rule] if recurrence_rule else []

        updated = svc.events().patch(
            calendarId=calendar_id,
            eventId=target_event_id,
            body=patch_body,
        ).execute()
        return {"ok": True, "id": updated.get("id")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {e}")


@app.delete("/api/events/{calendar_id}/{event_id}")
def delete_event(calendar_id: str, event_id: str, applySeries: bool = False, seriesEventId: str | None = None):
    target_event_id = seriesEventId if applySeries and seriesEventId else event_id
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    svc.events().delete(calendarId=calendar_id, eventId=target_event_id).execute()
    return JSONResponse({"ok": True})


@app.post("/api/thesis-log")
def add_thesis_log(
    started_at: str = Form(...),
    hours: float = Form(...),
    summary: str = Form(...),
    details: str = Form(""),
    course: str = Form(""),
    task_type: str = Form(""),
    category_tags: str = Form(""),
    outcome: str = Form(""),
    blocker: str = Form(""),
    next_action: str = Form(""),
):
    dt = datetime.fromisoformat(started_at)

    meta_lines = []
    if course.strip():
        meta_lines.append(f"course={course.strip()}")
    if task_type.strip():
        meta_lines.append(f"task_type={task_type.strip()}")
    if category_tags.strip():
        tags = [t.strip() for t in category_tags.split(",") if t.strip()]
        if tags:
            meta_lines.append(f"category_tags={','.join(tags)}")
    if outcome.strip():
        meta_lines.append(f"outcome={outcome.strip()}")
    if blocker.strip():
        meta_lines.append(f"blocker={blocker.strip()}")
    if next_action.strip():
        meta_lines.append(f"next_action={next_action.strip()}")

    combined_details = (details or "").strip()
    if meta_lines:
        meta_blob = "\n".join(["[meta]"] + meta_lines)
        combined_details = f"{combined_details}\n\n{meta_blob}".strip()

    with Session(engine) as db:
        db.add(ThesisLog(started_at=dt, hours=hours, summary=summary, details=combined_details))
        db.commit()
    return RedirectResponse(url="/", status_code=303)


def _extract_meta(details: str) -> dict:
    meta = {}
    txt = details or ""
    if "[meta]" in txt:
        try:
            section = txt.split("[meta]", 1)[1]
            for line in section.splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                meta[k.strip()] = v.strip()
        except Exception:
            pass
    return meta


def _base_details(details: str) -> str:
    txt = details or ""
    if "[meta]" in txt:
        return txt.split("[meta]", 1)[0].strip()
    return txt.strip()


def _compose_details(base: str, meta: dict) -> str:
    lines = [f"{k}={v}" for k, v in meta.items() if str(v).strip()]
    if not lines:
        return (base or "").strip()
    return ((base or "").strip() + "\n\n[meta]\n" + "\n".join(lines)).strip()


@app.get("/api/thesis-logs")
def thesis_logs(days: int = 7):
    cutoff = datetime.now() - timedelta(days=days)
    with Session(engine) as db:
        logs = db.scalars(select(ThesisLog).where(ThesisLog.started_at >= cutoff).order_by(ThesisLog.started_at.asc())).all()

    items = []
    for l in logs:
        meta = _extract_meta(l.details or "")
        tags = [t.strip() for t in (meta.get("category_tags", "") or "").split(",") if t.strip()]
        items.append({
            "id": l.id,
            "startedAt": l.started_at.isoformat(),
            "hours": float(l.hours),
            "summary": l.summary,
            "taskType": meta.get("task_type", tags[0] if tags else "uncategorized"),
            "categoryTags": tags,
            "details": _base_details(l.details or ""),
            "outcome": meta.get("outcome", ""),
            "blocker": meta.get("blocker", ""),
            "nextAction": meta.get("next_action", ""),
        })
    return {"days": days, "items": items}


@app.delete("/api/thesis-logs/{log_id}")
def delete_thesis_log(log_id: int):
    with Session(engine) as db:
        row = db.get(ThesisLog, log_id)
        if not row:
            raise HTTPException(status_code=404, detail="Thesis log not found")
        db.delete(row)
        db.commit()
    return {"ok": True, "id": log_id}


@app.delete("/api/thesis-logs")
def delete_thesis_logs_by_summary(summary: str):
    summary_norm = (summary or "").strip().lower()
    if not summary_norm:
        raise HTTPException(status_code=400, detail="summary is required")

    deleted = 0
    with Session(engine) as db:
        rows = db.scalars(select(ThesisLog).where(ThesisLog.summary.is_not(None))).all()
        for r in rows:
            if (r.summary or "").strip().lower() == summary_norm:
                db.delete(r)
                deleted += 1
        db.commit()
    return {"ok": True, "deleted": deleted, "summary": summary}


@app.put("/api/thesis-logs/{log_id}")
async def update_thesis_log(log_id: int, request: Request):
    body = await request.json()
    with Session(engine) as db:
        row = db.get(ThesisLog, log_id)
        if not row:
            raise HTTPException(status_code=404, detail="Thesis log not found")

        row.started_at = datetime.fromisoformat(body.get("startedAt", row.started_at.isoformat()))
        row.hours = float(body.get("hours", row.hours))
        row.summary = body.get("summary", row.summary)

        meta = _extract_meta(row.details or "")
        tags = [t.strip() for t in (body.get("categoryTags", []) or []) if str(t).strip()]
        if body.get("taskType") is not None:
            meta["task_type"] = body.get("taskType", "")
        meta["category_tags"] = ",".join(tags)
        meta["outcome"] = body.get("outcome", "")
        meta["blocker"] = body.get("blocker", "")
        meta["next_action"] = body.get("nextAction", "")

        row.details = _compose_details(body.get("details", _base_details(row.details or "")), meta)
        db.commit()

    return {"ok": True, "id": log_id}


@app.put("/api/thesis-logs/{log_id}/categories")
async def update_thesis_log_categories(log_id: int, request: Request):
    body = await request.json()
    tags = [t.strip() for t in (body.get("categoryTags", []) or []) if str(t).strip()]

    with Session(engine) as db:
        row = db.get(ThesisLog, log_id)
        if not row:
            raise HTTPException(status_code=404, detail="Thesis log not found")

        details = row.details or ""
        meta = _extract_meta(details)
        meta["category_tags"] = ",".join(tags)

        row.details = _compose_details(_base_details(details), meta)
        db.commit()

    return {"ok": True, "id": log_id, "categoryTags": tags}


@app.get("/api/thesis-summary")
def thesis_summary(days: int = 7):
    cutoff = datetime.now() - timedelta(days=days)
    with Session(engine) as db:
        logs = db.scalars(select(ThesisLog).where(ThesisLog.started_at >= cutoff)).all()
        all_logs = db.scalars(select(ThesisLog)).all()

    total = round(sum(l.hours for l in logs), 2)
    total_project_hours = round(sum(l.hours for l in all_logs), 2)

    by_task_type = {}
    outcomes = []
    blockers = []
    next_actions = []

    for l in logs:
        meta = _extract_meta(l.details or "")

        tags = [t.strip() for t in (meta.get("category_tags", "") or "").split(",") if t.strip()]
        if tags:
            share = float(l.hours) / len(tags)
            for t in tags:
                by_task_type[t] = round(by_task_type.get(t, 0.0) + share, 2)
        else:
            tt = meta.get("task_type", "uncategorized")
            by_task_type[tt] = round(by_task_type.get(tt, 0.0) + float(l.hours), 2)

        if meta.get("outcome"):
            outcomes.append(meta["outcome"])
        if meta.get("blocker"):
            blockers.append(meta["blocker"])
        if meta.get("next_action"):
            next_actions.append(meta["next_action"])

    return {
        "days": days,
        "entries": len(logs),
        "hours": total,
        "totalProjectHours": total_project_hours,
        "hoursByTaskType": by_task_type,
        "weeklyHighlights": {
            "outcomes": outcomes[-5:],
            "blockers": blockers[-5:],
            "nextActions": next_actions[-5:],
        },
    }


# -------------------------
# Agent/background scheduling helpers
# -------------------------

def _list_calendars_raw():
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    return svc.calendarList().list(maxResults=100).execute().get("items", [])


def _collect_busy_ranges(start_iso: str, end_iso: str, calendar_ids: list[str] | None = None):
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)

    all_cals = _list_calendars_raw()
    selected = []
    for c in all_cals:
        cid = c.get("id")
        if cid == "sv.swedish#holiday@group.v.calendar.google.com":
            continue
        if calendar_ids and cid not in calendar_ids:
            continue
        selected.append(cid)

    busy = []
    for cid in selected:
        evs = svc.events().list(
            calendarId=cid,
            singleEvents=True,
            orderBy="startTime",
            timeMin=start_iso,
            timeMax=end_iso,
            maxResults=250,
        ).execute().get("items", [])

        for e in evs:
            s = e.get("start", {})
            en = e.get("end", {})
            if "dateTime" not in s or "dateTime" not in en:
                continue
            try:
                sdt = datetime.fromisoformat(s["dateTime"].replace("Z", "+00:00"))
                edt = datetime.fromisoformat(en["dateTime"].replace("Z", "+00:00"))
                busy.append((sdt, edt))
            except Exception:
                continue

    busy.sort(key=lambda x: x[0])
    merged = []
    for sdt, edt in busy:
        if not merged or sdt > merged[-1][1]:
            merged.append([sdt, edt])
        else:
            merged[-1][1] = max(merged[-1][1], edt)
    return [(x[0], x[1]) for x in merged]


def _slot_overlaps(slot_start: datetime, slot_end: datetime, busy_ranges: list[tuple[datetime, datetime]]):
    for bs, be in busy_ranges:
        if slot_start < be and slot_end > bs:
            return True
    return False


def _find_overlaps(start_iso: str, end_iso: str, calendar_ids: list[str] | None = None):
    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)

    all_cals = _list_calendars_raw()
    selected = []
    for c in all_cals:
        cid = c.get("id")
        if cid == "sv.swedish#holiday@group.v.calendar.google.com":
            continue
        if calendar_ids and cid not in calendar_ids:
            continue
        selected.append((cid, c.get("summary", cid)))

    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))

    overlaps = []
    for cid, cname in selected:
        evs = svc.events().list(
            calendarId=cid,
            singleEvents=True,
            orderBy="startTime",
            timeMin=start_iso,
            timeMax=end_iso,
            maxResults=50,
        ).execute().get("items", [])

        for e in evs:
            s = e.get("start", {})
            en = e.get("end", {})
            if "dateTime" not in s or "dateTime" not in en:
                continue
            try:
                es = datetime.fromisoformat(s["dateTime"].replace("Z", "+00:00"))
                ee = datetime.fromisoformat(en["dateTime"].replace("Z", "+00:00"))
                if start_dt < ee and end_dt > es:
                    overlaps.append({
                        "calendarId": cid,
                        "calendar": cname,
                        "id": e.get("id"),
                        "summary": e.get("summary", "(no title)"),
                        "start": s,
                        "end": en,
                    })
            except Exception:
                continue

    return overlaps


@app.post("/api/agent/suggest-slots")
async def suggest_slots(request: Request):
    """
    Background-friendly slot suggestion endpoint.
    Body example:
    {
      "durationMin": 120,
      "startDate": "2026-03-11",
      "endDate": "2026-03-18",
      "dayStartHour": 8,
      "dayEndHour": 22,
      "calendarIds": ["eric.hm.berg@gmail.com"],
      "avoidWeekends": false,
      "maxResults": 5,
      "timeZone": "Europe/Stockholm"
    }
    """
    body = await request.json()
    profile = load_scheduling_profile()
    uni_related = _is_university_related(body)

    default_duration = profile.get("defaultDurationsMin", {}).get("university" if uni_related else "general", 60)
    duration_min = int(body.get("durationMin", default_duration))
    start_date = date.fromisoformat(body.get("startDate"))
    end_date = date.fromisoformat(body.get("endDate"))

    pref = profile.get("timePreferences", {})
    default_day_start = int(str(pref.get("earliestStart", "09:00")).split(":")[0])
    default_day_end = int(str(pref.get("latestEndUniversity" if uni_related else "latestEnd", "22:00")).split(":")[0])

    day_start = int(body.get("dayStartHour", default_day_start))
    day_end = int(body.get("dayEndHour", default_day_end))

    default_avoid_weekends = (not bool(pref.get("weekendAllowed", True))) or (uni_related and bool(pref.get("avoidUniversityOnWeekends", True)))
    avoid_weekends = bool(body.get("avoidWeekends", default_avoid_weekends))

    max_results = int(body.get("maxResults", 5))
    tz_name = body.get("timeZone", "Europe/Stockholm")
    tz = ZoneInfo(tz_name)

    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tz)
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=tz)

    busy = _collect_busy_ranges(start_dt.isoformat(), end_dt.isoformat(), body.get("calendarIds"))

    step = 15
    out = []
    cur_day = start_date
    while cur_day <= end_date and len(out) < max_results:
        wd = datetime.combine(cur_day, datetime.min.time(), tzinfo=tz).weekday()  # 0 Monday
        if avoid_weekends and wd >= 5:
            cur_day += timedelta(days=1)
            continue

        slot_start = datetime(cur_day.year, cur_day.month, cur_day.day, day_start, 0, tzinfo=tz)
        day_limit = datetime(cur_day.year, cur_day.month, cur_day.day, day_end, 0, tzinfo=tz)

        while slot_start + timedelta(minutes=duration_min) <= day_limit and len(out) < max_results:
            slot_end = slot_start + timedelta(minutes=duration_min)
            if not _slot_overlaps(slot_start, slot_end, busy):
                out.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                    "score": 1.0,
                    "reason": "Earliest free slot",
                })
            slot_start += timedelta(minutes=step)

        cur_day += timedelta(days=1)

    return {"items": out, "count": len(out)}


@app.post("/api/agent/book-slot")
async def agent_book_slot(request: Request):
    body = await request.json()
    profile = load_scheduling_profile()

    target_calendar = _choose_target_calendar(body, profile)
    avoid_set = {x.get("calendarId") for x in profile.get("avoidWriteCalendars", []) if x.get("calendarId")}
    if target_calendar in avoid_set:
        source = (body.get("sourceCalendarId") or "").lower()
        privacy = profile.get("privacyRouting", {})
        if source and "cobot" in source and privacy.get("cobotSharedSource"):
            target_calendar = privacy["cobotSharedSource"]
        elif source and ("cdk" in source or "chalmersdykarklubb" in source) and privacy.get("cdkSharedSource"):
            target_calendar = privacy["cdkSharedSource"]
        else:
            target_calendar = privacy.get("fallback", profile.get("defaultCalendar", "eric.hm.berg@gmail.com"))

    if body.get("start") and not body.get("end"):
        uni_related = _is_university_related(body)
        duration_min = int(body.get("durationMin", profile.get("defaultDurationsMin", {}).get("university" if uni_related else "general", 60)))
        start_dt = datetime.fromisoformat(body["start"].replace("Z", "+00:00"))
        body["end"] = (start_dt + timedelta(minutes=duration_min)).isoformat()

    check_conflicts = bool(body.get("checkConflicts", True))
    conflict_scope = body.get("conflictScope", "all")  # "all" | "targetCalendar"
    scope_calendar_ids = None
    if conflict_scope == "targetCalendar":
        scope_calendar_ids = [target_calendar]

    if check_conflicts:
        overlaps = _find_overlaps(body["start"], body["end"], scope_calendar_ids)
        if overlaps:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SLOT_CONFLICT",
                    "message": "New event overlaps existing event(s). Ask user what should move.",
                    "overlaps": overlaps,
                    "proposedCalendarId": target_calendar,
                },
            )

    created = _create_event(
        target_calendar,
        body["summary"],
        body.get("description", ""),
        body["start"],
        body["end"],
        body.get("timeZone", "Europe/Stockholm"),
        body.get("recurrenceRule"),
    )
    return {"ok": True, "id": created.get("id"), "htmlLink": created.get("htmlLink"), "calendarId": target_calendar}


@app.post("/api/agent/move-event")
async def agent_move_event(request: Request):
    body = await request.json()
    apply_series = bool(body.get("applySeries", False))
    target_event_id = body.get("seriesEventId") if apply_series and body.get("seriesEventId") else body["eventId"]

    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)
    updated = svc.events().patch(
        calendarId=body["calendarId"],
        eventId=target_event_id,
        body={
            "start": {"dateTime": body["newStart"], "timeZone": body.get("timeZone", "Europe/Stockholm")},
            "end": {"dateTime": body["newEnd"], "timeZone": body.get("timeZone", "Europe/Stockholm")},
        },
    ).execute()
    return {"ok": True, "id": updated.get("id")}


@app.post("/api/agent/add-buffers")
async def agent_add_buffers(request: Request):
    """
    Add prep/travel buffer events around an existing event.

    Body example:
    {
      "calendarId": "eric.hm.berg@gmail.com",
      "eventId": "abc123",
      "prepMin": 15,
      "travelBeforeMin": 20,
      "travelAfterMin": 0,
      "timeZone": "Europe/Stockholm",
      "createPrep": true,
      "createTravelBefore": true,
      "createTravelAfter": false
    }
    """
    body = await request.json()
    calendar_id = body["calendarId"]
    event_id = body["eventId"]
    tz_name = body.get("timeZone", "Europe/Stockholm")

    prep_min_raw = int(body.get("prepMin", 0))
    travel_before_min_raw = int(body.get("travelBeforeMin", 0))
    travel_after_min_raw = int(body.get("travelAfterMin", 0))

    # Keep planner blocks aligned with 15-minute calendar granularity.
    def _normalize_block_minutes(v: int) -> int:
        if v <= 0:
            return 0
        return max(15, v)

    prep_min = _normalize_block_minutes(prep_min_raw)
    travel_before_min = _normalize_block_minutes(travel_before_min_raw)
    travel_after_min = _normalize_block_minutes(travel_after_min_raw)

    create_prep = bool(body.get("createPrep", prep_min > 0))
    create_travel_before = bool(body.get("createTravelBefore", travel_before_min > 0))
    create_travel_after = bool(body.get("createTravelAfter", travel_after_min > 0))

    creds = get_google_creds()
    svc = build("calendar", "v3", credentials=creds)

    src = svc.events().get(calendarId=calendar_id, eventId=event_id).execute()
    start_raw = src.get("start", {}).get("dateTime")
    end_raw = src.get("end", {}).get("dateTime")
    if not start_raw or not end_raw:
        raise HTTPException(status_code=400, detail="Buffers only supported for timed events (not all-day).")

    src_start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    src_end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))

    title = src.get("summary", "Event")
    created = []

    if create_prep and prep_min > 0:
        s = src_start - timedelta(minutes=prep_min)
        e = src_start
        ev = _create_event(
            calendar_id,
            f"Prep: {title}",
            f"Prep buffer before: {title}",
            s.isoformat(),
            e.isoformat(),
            tz_name,
        )
        created.append({"kind": "prep", "id": ev.get("id"), "htmlLink": ev.get("htmlLink")})

    if create_travel_before and travel_before_min > 0:
        s = src_start - timedelta(minutes=travel_before_min)
        e = src_start
        ev = _create_event(
            calendar_id,
            f"Travel: {title}",
            f"Travel buffer before: {title}",
            s.isoformat(),
            e.isoformat(),
            tz_name,
        )
        created.append({"kind": "travel_before", "id": ev.get("id"), "htmlLink": ev.get("htmlLink")})

    if create_travel_after and travel_after_min > 0:
        s = src_end
        e = src_end + timedelta(minutes=travel_after_min)
        ev = _create_event(
            calendar_id,
            f"Travel after: {title}",
            f"Travel buffer after: {title}",
            s.isoformat(),
            e.isoformat(),
            tz_name,
        )
        created.append({"kind": "travel_after", "id": ev.get("id"), "htmlLink": ev.get("htmlLink")})

    return {"ok": True, "sourceEventId": event_id, "created": created, "count": len(created)}
