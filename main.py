import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALQURAN_BASE = "https://api.alquran.cloud/v1"
HADITH_BASE = "https://api.hadith.gading.dev"
ALADHAN_BASE = "https://api.aladhan.com/v1"

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

# Quran proxy endpoints
@app.get("/api/quran/surahs")
def quran_surahs():
    try:
        r = requests.get(f"{ALQURAN_BASE}/surah", timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            raise HTTPException(status_code=502, detail="Upstream error")
        return data["data"]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/quran/surah/{sid}")
def quran_surah(sid: int):
    try:
        r = requests.get(f"{ALQURAN_BASE}/surah/{sid}", timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            raise HTTPException(status_code=502, detail="Upstream error")
        return data["data"]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/quran/surah/{sid}/audio")
def quran_surah_audio(sid: int):
    try:
        r = requests.get(f"{ALQURAN_BASE}/surah/{sid}/ar.alafasy", timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            raise HTTPException(status_code=502, detail="Upstream error")
        return data["data"]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/quran/surah/{sid}/translation/{edition}")
def quran_surah_translation(sid: int, edition: str):
    try:
        r = requests.get(f"{ALQURAN_BASE}/surah/{sid}/{edition}", timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            raise HTTPException(status_code=502, detail="Upstream error")
        return data["data"]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

# Hadith proxy endpoints (using public gading.dev API)
@app.get("/api/hadith/collections")
def hadith_collections():
    try:
        r = requests.get(f"{HADITH_BASE}/books", timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/hadith/{collection}")
def hadith_by_collection(collection: str, start: int = Query(1, ge=1), end: int = Query(150, ge=1, le=500)):
    try:
        r = requests.get(f"{HADITH_BASE}/books/{collection}?range={start}-{end}", timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("data", {})
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

# Prayer times and Hijri APIs (Aladhan)
@app.get("/api/prayer/timingsByCity")
def timings_by_city(city: str, country: str, method: int = 2):
    try:
        r = requests.get(f"{ALADHAN_BASE}/timingsByCity", params={"city": city, "country": country, "method": method}, timeout=20)
        r.raise_for_status()
        return r.json().get("data", {})
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/hijri/convert")
def gregorian_to_hijri(date: str):
    try:
        # date format DD-MM-YYYY
        r = requests.get(f"{ALADHAN_BASE}/gToH", params={"date": date}, timeout=20)
        r.raise_for_status()
        return r.json().get("data", {})
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/hijri/calendar")
def hijri_calendar(month: int, year: int, method: int = 2):
    try:
        r = requests.get(f"{ALADHAN_BASE}/hijriCalendar/{year}/{month}", params={"method": method}, timeout=20)
        r.raise_for_status()
        return r.json().get("data", [])
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

# Contact form sink
@app.post("/api/contact")
async def contact(request: Request):
    body = await request.json()
    # Here we might send an email or push to webhook; for now, just echo
    name = body.get("name")
    email = body.get("email")
    message = body.get("message")
    if not name or not email or not message:
        raise HTTPException(status_code=400, detail="Missing fields")
    return {"status": "ok", "received": {"name": name, "email": email}}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
