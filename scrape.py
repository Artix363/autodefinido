#!/usr/bin/env python3
"""
Scraper del Autodefinido de El País.
Usa la API oficial de SmartGames: backend.smartgames.media/api/game/self_defined/last
No necesita Cloudflare bypass, Scrape.do ni scraping de HTML. 100% gratis.
"""

import json, re, sys, os, subprocess
from datetime import date, datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Ejecuta: pip install requests")
    sys.exit(1)

API_URL   = "https://backend.smartgames.media/api/game/self_defined/last"
DATA_DIR  = os.environ.get("DATA_DIR", "data")
AUTO_PUSH = os.environ.get("AUTO_PUSH", "true").lower() == "true"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/vnd.api+json",
    "Origin": "https://elpais.com",
    "Referer": "https://elpais.com/juegos/autodefinido/diario/dia/",
}


def fetch_puzzle():
    print(f"  URL: {API_URL}")
    r = requests.get(API_URL, headers=HEADERS, timeout=20)
    print(f"  Status: {r.status_code}, bytes: {len(r.text):,}")
    if r.status_code != 200:
        raise ValueError(f"Error {r.status_code}: {r.text[:300]}")
    return r.json()


def parse_puzzle(raw):
    attrs  = raw["data"]["attributes"]
    config = attrs["config"]
    board  = config["board"]

    pub_date  = attrs.get("publicationDate") or date.today().isoformat()
    grid_cols = max(c["col"] for c in board) + 1
    grid_rows = max(c["row"] for c in board) + 1

    # Cuadrícula: 0=negro, 1=jugable, 2=pista
    grid = [[0] * grid_cols for _ in range(grid_rows)]
    for cell in board:
        col, row, typ = cell["col"], cell["row"], cell["type"]
        if typ == "cell":
            grid[row][col] = 1
        elif typ in ("clue", "clues"):
            grid[row][col] = 2

    # Extraer pistas
    clues = []
    for cell in board:
        typ = cell["type"]
        col, row = cell["col"], cell["row"]

        if typ == "clue":
            text      = cell.get("value", "").replace("\\n", " ").strip()
            direction = cell.get("orientation", {}).get("to", "right")
            if text:
                clues.append({"text": text, "col": col, "row": row, "direction": direction})

        elif typ == "clues":
            values       = cell.get("values", [])
            orientations = cell.get("orientations", [])
            for i, text in enumerate(values):
                text = text.replace("\\n", " ").strip()
                direction = orientations[i].get("to", "right") if i < len(orientations) else "right"
                if text:
                    clues.append({"text": text, "col": col, "row": row, "direction": direction})

    clues.sort(key=lambda c: (c["row"], c["col"]))

    return {
        "date":        pub_date,
        "scraped_at":  datetime.utcnow().isoformat() + "Z",
        "source":      API_URL,
        "grid_cols":   grid_cols,
        "grid_rows":   grid_rows,
        "grid":        grid,
        "clues":       clues,
        "total_clues": len(clues),
    }


def save_puzzle(data, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fn = f"{output_dir}/{data['date']}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fn


def update_index(output_dir):
    dates = sorted(
        [f.stem for f in Path(output_dir).glob("*.json")
         if f.stem != "index" and re.match(r"\d{4}-\d{2}-\d{2}", f.stem)],
        reverse=True
    )
    idx = {"total": len(dates), "dates": dates,
           "updated_at": datetime.utcnow().isoformat() + "Z"}
    with open(f"{output_dir}/index.json", "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    return idx


def git_push(data_dir):
    try:
        changed = subprocess.run(
            ["git", "status", "--porcelain", data_dir],
            capture_output=True, text=True
        ).stdout.strip()
        if not changed:
            print("  Git: sin cambios")
            return
        subprocess.run(["git", "add", data_dir], check=True)
        subprocess.run(["git", "commit", "-m",
                        f"Autodefinido {date.today().isoformat()}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("  Git: subido correctamente")
    except Exception as e:
        print(f"  Git error: {e}")


def main():
    today = date.today().isoformat()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Descargando autodefinido de {today}...")

    if Path(f"{DATA_DIR}/{today}.json").exists():
        print(f"  Ya existe {today}.json — nada que hacer.")
        return

    try:
        raw = fetch_puzzle()
    except Exception as e:
        print(f"  ERROR descargando: {e}")
        sys.exit(1)

    try:
        data = parse_puzzle(raw)
    except Exception as e:
        print(f"  ERROR parseando: {e}")
        Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
        with open(f"{DATA_DIR}/debug_raw.json", "w") as f:
            json.dump(raw, f, indent=2)
        sys.exit(1)

    if data["date"] != today:
        print(f"  AVISO: el puzzle es de {data['date']}, no de {today}.")
        print(f"  El País aún no publicó el de hoy. Reintenta más tarde.")
        sys.exit(1)

    fn = save_puzzle(data, DATA_DIR)
    print(f"  Guardado: {fn}")
    print(f"  Cuadrícula: {data['grid_cols']}x{data['grid_rows']} | Pistas: {data['total_clues']}")

    idx = update_index(DATA_DIR)
    print(f"  Total en archivo: {idx['total']} puzzles")

    if AUTO_PUSH:
        git_push(DATA_DIR)

    print("  Listo!")


if __name__ == "__main__":
    main()
