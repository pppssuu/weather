import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

LAT = 37.4499
LON = 129.1653
TZ = "Asia/Seoul"
URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&hourly=temperature_2m,cloud_cover,shortwave_radiation,direct_normal_irradiance,diffuse_radiation"
    f"&timezone={TZ}&forecast_days=3"
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "solar_samcheok.csv"
JSON_PATH = DATA_DIR / "latest_forecast.json"

FIELDNAMES = [
    "collected_at_kst",
    "time",
    "temperature_2m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    clouds = hourly.get("cloud_cover", [])
    ghi = hourly.get("shortwave_radiation", [])
    dni = hourly.get("direct_normal_irradiance", [])
    dhi = hourly.get("diffuse_radiation", [])

    now_kst = datetime.now(timezone.utc).astimezone(ZoneInfo(TZ)).isoformat(timespec="seconds")

    rows = []
    for i, t in enumerate(times):
        rows.append({
            "collected_at_kst": now_kst,
            "time": t,
            "temperature_2m": temps[i] if i < len(temps) else None,
            "cloud_cover": clouds[i] if i < len(clouds) else None,
            "shortwave_radiation": ghi[i] if i < len(ghi) else None,
            "direct_normal_irradiance": dni[i] if i < len(dni) else None,
            "diffuse_radiation": dhi[i] if i < len(dhi) else None,
        })

    # 최신 예보 스냅샷 저장(대시보드 예보 그래프용)
    JSON_PATH.write_text(
        json.dumps({"updated_at_kst": now_kst, "records": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 누적 CSV 병합(동일 time 기준 최신 수집값으로 갱신 후 시간순 정렬)
    existing = {}
    if CSV_PATH.exists():
        with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("time"):
                    existing[r["time"]] = r

    for r in rows:
        existing[r["time"]] = {k: "" if v is None else v for k, v in r.items()}

    sorted_times = sorted(existing.keys())
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for t in sorted_times:
            writer.writerow(existing[t])

    print(f"Saved {len(rows)} forecast slots; total CSV rows: {len(sorted_times)}")


if __name__ == "__main__":
    main()
