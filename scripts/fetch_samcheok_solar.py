import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

CITIES = [
    # 기존 기준 도시
    {"id": "samcheok", "group": "한국", "name": "삼척", "lat": 37.4499, "lon": 129.1653, "tz": "Asia/Seoul"},
    # 한국 주요 10개 도시
    {"id": "seoul", "group": "한국", "name": "서울", "lat": 37.5665, "lon": 126.9780, "tz": "Asia/Seoul"},
    {"id": "busan", "group": "한국", "name": "부산", "lat": 35.1796, "lon": 129.0756, "tz": "Asia/Seoul"},
    {"id": "incheon", "group": "한국", "name": "인천", "lat": 37.4563, "lon": 126.7052, "tz": "Asia/Seoul"},
    {"id": "daegu", "group": "한국", "name": "대구", "lat": 35.8714, "lon": 128.6014, "tz": "Asia/Seoul"},
    {"id": "daejeon", "group": "한국", "name": "대전", "lat": 36.3504, "lon": 127.3845, "tz": "Asia/Seoul"},
    {"id": "gwangju", "group": "한국", "name": "광주", "lat": 35.1595, "lon": 126.8526, "tz": "Asia/Seoul"},
    {"id": "ulsan", "group": "한국", "name": "울산", "lat": 35.5384, "lon": 129.3114, "tz": "Asia/Seoul"},
    {"id": "suwon", "group": "한국", "name": "수원", "lat": 37.2636, "lon": 127.0286, "tz": "Asia/Seoul"},
    {"id": "gangneung", "group": "한국", "name": "강릉", "lat": 37.7519, "lon": 128.8761, "tz": "Asia/Seoul"},
    {"id": "jeju", "group": "한국", "name": "제주", "lat": 33.4996, "lon": 126.5312, "tz": "Asia/Seoul"},
    # 세계 주요 10개 수도
    {"id": "tokyo", "group": "세계 수도", "name": "도쿄 (일본)", "lat": 35.6762, "lon": 139.6503, "tz": "Asia/Tokyo"},
    {"id": "beijing", "group": "세계 수도", "name": "베이징 (중국)", "lat": 39.9042, "lon": 116.4074, "tz": "Asia/Shanghai"},
    {"id": "washington", "group": "세계 수도", "name": "워싱턴 D.C. (미국)", "lat": 38.9072, "lon": -77.0369, "tz": "America/New_York"},
    {"id": "london", "group": "세계 수도", "name": "런던 (영국)", "lat": 51.5072, "lon": -0.1276, "tz": "Europe/London"},
    {"id": "paris", "group": "세계 수도", "name": "파리 (프랑스)", "lat": 48.8566, "lon": 2.3522, "tz": "Europe/Paris"},
    {"id": "berlin", "group": "세계 수도", "name": "베를린 (독일)", "lat": 52.5200, "lon": 13.4050, "tz": "Europe/Berlin"},
    {"id": "ottawa", "group": "세계 수도", "name": "오타와 (캐나다)", "lat": 45.4215, "lon": -75.6972, "tz": "America/Toronto"},
    {"id": "canberra", "group": "세계 수도", "name": "캔버라 (호주)", "lat": -35.2809, "lon": 149.1300, "tz": "Australia/Sydney"},
    {"id": "new_delhi", "group": "세계 수도", "name": "뉴델리 (인도)", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    {"id": "singapore", "group": "세계 수도", "name": "싱가포르 (싱가포르)", "lat": 1.3521, "lon": 103.8198, "tz": "Asia/Singapore"},
]

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_DIR = DATA_DIR / "csv"
JSON_PATH = DATA_DIR / "latest_forecast.json"

FIELDNAMES = [
    "collected_at_kst",
    "city_id",
    "city_name",
    "time_local",
    "temperature_2m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
]


def main():
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    lats = ",".join(str(c["lat"]) for c in CITIES)
    lons = ",".join(str(c["lon"]) for c in CITIES)
    tzs = ",".join(c["tz"] for c in CITIES)

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lats}&longitude={lons}"
        "&hourly=temperature_2m,cloud_cover,shortwave_radiation,direct_normal_irradiance,diffuse_radiation"
        f"&timezone={tzs}&forecast_days=3"
    )

    resp = requests.get(url, timeout=45)
    resp.raise_for_status()
    payload = resp.json()

    if isinstance(payload, dict):
        payload = [payload]

    now_kst = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    dashboard_cities = {}

    for city, item in zip(CITIES, payload):
        hourly = item.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        clouds = hourly.get("cloud_cover", [])
        ghi = hourly.get("shortwave_radiation", [])
        dni = hourly.get("direct_normal_irradiance", [])
        dhi = hourly.get("diffuse_radiation", [])

        rows = []
        for i, t in enumerate(times):
            rows.append({
                "collected_at_kst": now_kst,
                "city_id": city["id"],
                "city_name": city["name"],
                "time_local": t,
                "temperature_2m": temps[i] if i < len(temps) else None,
                "cloud_cover": clouds[i] if i < len(clouds) else None,
                "shortwave_radiation": ghi[i] if i < len(ghi) else None,
                "direct_normal_irradiance": dni[i] if i < len(dni) else None,
                "diffuse_radiation": dhi[i] if i < len(dhi) else None,
            })

        dashboard_cities[city["id"]] = {
            "id": city["id"],
            "group": city["group"],
            "name": city["name"],
            "lat": city["lat"],
            "lon": city["lon"],
            "timezone": city["tz"],
            "records": rows,
        }

        csv_path = CSV_DIR / f"{city['id']}.csv"
        existing = {}
        if csv_path.exists():
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("time_local"):
                        existing[r["time_local"]] = r

        for r in rows:
            existing[r["time_local"]] = {k: "" if v is None else v for k, v in r.items()}

        sorted_times = sorted(existing.keys())
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for t in sorted_times:
                writer.writerow(existing[t])

    JSON_PATH.write_text(
        json.dumps(
            {
                "updated_at_kst": now_kst,
                "city_order": [c["id"] for c in CITIES],
                "cities": dashboard_cities,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Updated {len(CITIES)} cities at {now_kst}")


if __name__ == "__main__":
    main()
