#!/usr/bin/env python3
"""
Scraper del Autodefinido diario de El País.
Extrae la cuadrícula y las pistas del HTML y las guarda como JSON.
"""

import json
import re
import sys
import os
from datetime import date, datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Instala dependencias: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

URL = "https://elpais.com/juegos/autodefinido/diario/dia/"

# Cabeceras que imitan un navegador real
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def fetch_html(url: str) -> str:
    """Descarga el HTML de la página simulando un navegador real."""
    session = requests.Session()

    # Primero visitamos la portada de juegos para obtener cookies
    try:
        session.get(
            "https://elpais.com/juegos/",
            headers=HEADERS,
            timeout=20
        )
    except Exception:
        pass  # Si falla la portada, seguimos igualmente

    # Ahora pedimos la página del autodefinido con Referer real
    headers_with_referer = {**HEADERS, "Referer": "https://elpais.com/juegos/"}
    resp = session.get(url, headers=headers_with_referer, timeout=30)
    resp.raise_for_status()

    html = resp.text
    print(f"  HTTP {resp.status_code}, {len(html):,} bytes, encoding: {resp.encoding}")

    # Diagnóstico: si el HTML es muy pequeño, probablemente hay un muro
    if len(html) < 50_000:
        print("  AVISO: HTML muy pequeño, puede ser una página de bloqueo o suscripción")
        # Guardar muestra para depuración
        with open("/tmp/debug_elpais.html", "w", encoding="utf-8") as f:
            f.write(html[:5000])
        print("  Muestra guardada en /tmp/debug_elpais.html")

    return html


def parse_tspan_text(g_element) -> str:
    """Extrae el texto de todos los tspan dentro de un grupo."""
    tspans = g_element.find_all("tspan")
    parts = [t.get_text(strip=True) for t in tspans if t.get_text(strip=True)]
    return " ".join(parts)


def parse_transform(transform_str: str):
    """Extrae (x, y) de translate(x, y)."""
    m = re.search(r"translate\((\d+),\s*(\d+)\)", transform_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def has_arrow_down(g_element) -> bool:
    """Detecta si la celda tiene flecha hacia abajo (pista vertical)."""
    images = g_element.find_all("image")
    for img in images:
        transform = img.get("transform", "")
        # Flecha abajo: transform con translate(35, 80) o similar — en la parte inferior
        if "35, 80" in transform or "35,80" in transform:
            return True
    return False


def has_arrow_right(g_element) -> bool:
    """Detecta si la celda tiene flecha hacia la derecha (pista horizontal)."""
    images = g_element.find_all("image")
    for img in images:
        transform = img.get("transform", "")
        # Flecha derecha: transform con translate(80, 35) — en el lado derecho
        if "80, 35" in transform or "80,35" in transform:
            return True
    return False


def extract_date_from_html(soup) -> str:
    """Extrae la fecha del autodefinido desde el footer."""
    footer = soup.find("footer")
    if footer:
        text = footer.get_text()
        # Busca patrón: "Autodefinido 17 abril, 2026"
        m = re.search(r"Autodefinido\s+(\d+)\s+(\w+),?\s+(\d{4})", text, re.IGNORECASE)
        if m:
            day = int(m.group(1))
            month_es = m.group(2).lower()
            year = int(m.group(3))
            months = {
                "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
            }
            month = months.get(month_es, 0)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"
    return date.today().isoformat()


def parse_autodefinido(html: str) -> dict:
    """Parsea el HTML y extrae toda la información del autodefinido."""
    soup = BeautifulSoup(html, "lxml")

    # Encontrar el SVG del juego — intentamos varias estrategias
    svg = None

    # 1. Buscar por viewBox exacto conocido
    svg = soup.find("svg", attrs={"viewBox": "0 0 802 962"})

    # 2. Buscar dentro del div del juego
    if not svg:
        game_div = soup.find("div", id="self-defined-game")
        if game_div:
            svg = game_div.find("svg")

    # 3. Buscar cualquier SVG grande con celdas (tiene muchos <g transform>)
    if not svg:
        for candidate in soup.find_all("svg"):
            groups = candidate.find_all("g", attrs={"transform": True})
            if len(groups) > 20:
                svg = candidate
                break

    # 4. Si sigue sin encontrarse, dar diagnóstico útil
    if not svg:
        all_svgs = soup.find_all("svg")
        game_divs = soup.find_all("div", id=lambda x: x and "game" in x.lower())
        title = soup.find("title")
        print(f"  Diagnóstico: {len(all_svgs)} SVGs en página, "
              f"{len(game_divs)} divs de juego, "
              f"título: {title.text if title else 'sin título'}")
        # ¿Hay muro de suscripción?
        if soup.find(class_=lambda c: c and "paywall" in str(c).lower()):
            raise ValueError("El País está mostrando un muro de suscripción. "
                             "Prueba a ejecutar el scraper más tarde.")
        raise ValueError(
            f"No se encontró el SVG del autodefinido. "
            f"SVGs en página: {len(all_svgs)}. "
            f"Puede que El País haya cambiado el HTML o esté bloqueando el acceso."
        )

    # Extraer fecha
    puzzle_date = extract_date_from_html(soup)

    # El SVG tiene celdas de 80x80 píxeles, comenzando en translate(x, y)
    # Columnas: 0, 80, 160, 240, 320, 400, 480, 560, 640, 720 → índices 0-9
    # Filas:    0, 80, 160, ..., 880 → índices 0-10

    CELL_SIZE = 80

    # Estructuras de salida
    clues = []      # lista de pistas
    grid = {}       # diccionario {(col, row): tipo_celda}

    # Parsear todos los grupos <g> con transform
    all_groups = svg.find_all("g", attrs={"transform": True})

    for g in all_groups:
        transform = g.get("transform", "")
        px, py = parse_transform(transform)
        if px is None:
            continue

        col = px // CELL_SIZE
        row = py // CELL_SIZE

        # Encontrar el rect principal de la celda
        rect = g.find("rect", recursive=False)
        if not rect:
            # A veces el rect está un nivel más adentro
            rect = g.find("rect")

        if not rect:
            continue

        fill = rect.get("fill", "")

        # Clasificar la celda
        if fill == "#F5F5F5":
            # Celda gris = celda de pista (contiene texto)
            text = parse_tspan_text(g)
            if text:
                arrow_down = has_arrow_down(g)
                arrow_right = has_arrow_right(g)

                # Una celda puede tener pista vertical Y horizontal
                # Si hay línea horizontal divisoria, tiene dos pistas
                divider = g.find("rect", attrs={"height": "1"})
                
                if divider:
                    # Celda con dos pistas (separadas por línea)
                    tspans = g.find_all("tspan")
                    texts_above = []
                    texts_below = []
                    div_y = float(divider.get("y", 40))
                    
                    for ts in tspans:
                        ts_y_str = ts.get("y", "0")
                        try:
                            ts_y = float(ts_y_str)
                        except ValueError:
                            ts_y = 40
                        if ts_y < div_y:
                            texts_above.append(ts.get_text(strip=True))
                        else:
                            texts_below.append(ts.get_text(strip=True))
                    
                    text_above = " ".join(t for t in texts_above if t)
                    text_below = " ".join(t for t in texts_below if t)
                    
                    if text_above:
                        clues.append({
                            "text": text_above,
                            "col": col,
                            "row": row,
                            "direction": "down" if arrow_down else "right",
                            "part": "top"
                        })
                    if text_below:
                        clues.append({
                            "text": text_below,
                            "col": col,
                            "row": row,
                            "direction": "down" if arrow_right else "right",
                            "part": "bottom"
                        })
                else:
                    # Celda con una sola pista
                    direction = "unknown"
                    if arrow_down and arrow_right:
                        direction = "both"
                    elif arrow_down:
                        direction = "down"
                    elif arrow_right:
                        direction = "right"
                    
                    clues.append({
                        "text": text,
                        "col": col,
                        "row": row,
                        "direction": direction,
                    })

                grid[(col, row)] = "clue"
            else:
                grid[(col, row)] = "black"

        elif fill in ("white", "#ffffff", "#FFFFFF"):
            # Celda blanca = celda jugable (el usuario escribe aquí)
            grid[(col, row)] = "playable"

        elif fill in ("#D2F5FD", "#55CBE3"):
            # Celda azul = celda seleccionada (también jugable)
            grid[(col, row)] = "playable"

    # Calcular dimensiones de la cuadrícula
    if grid:
        all_cols = [c for c, r in grid.keys()]
        all_rows = [r for c, r in grid.keys()]
        max_col = max(all_cols)
        max_row = max(all_rows)
    else:
        max_col = 9
        max_row = 11

    # Construir la cuadrícula como lista de listas
    num_cols = max_col + 1
    num_rows = max_row + 1
    grid_matrix = []
    for row in range(num_rows):
        grid_row = []
        for col in range(num_cols):
            cell_type = grid.get((col, row), "black")
            grid_row.append(cell_type)
        grid_matrix.append(grid_row)

    # Serializar grid como lista de listas (0=negro, 1=jugable, 2=pista)
    grid_simple = []
    for row in range(num_rows):
        grid_row = []
        for col in range(num_cols):
            cell_type = grid.get((col, row), "black")
            if cell_type == "playable":
                grid_row.append(1)
            elif cell_type == "clue":
                grid_row.append(2)
            else:
                grid_row.append(0)
        grid_simple.append(grid_row)

    # Ordenar pistas por posición
    clues_sorted = sorted(clues, key=lambda c: (c["row"], c["col"]))

    return {
        "date": puzzle_date,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "source": URL,
        "grid_cols": num_cols,
        "grid_rows": num_rows,
        "grid": grid_simple,
        "clues": clues_sorted,
        "total_clues": len(clues_sorted),
    }


def save_puzzle(data: dict, output_dir: str = "data") -> str:
    """Guarda el puzzle como JSON en la carpeta de datos."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"{output_dir}/{data['date']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def update_index(output_dir: str = "data"):
    """Actualiza el índice de fechas disponibles."""
    data_path = Path(output_dir)
    dates = sorted([
        f.stem for f in data_path.glob("*.json")
        if f.stem != "index" and re.match(r"\d{4}-\d{2}-\d{2}", f.stem)
    ], reverse=True)
    
    index = {
        "total": len(dates),
        "dates": dates,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    with open(data_path / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    return index


def main():
    print(f"[{datetime.now().isoformat()}] Descargando autodefinido de El País...")
    
    try:
        html = fetch_html(URL)
        print(f"  HTML descargado: {len(html):,} bytes")
    except Exception as e:
        print(f"  ERROR descargando HTML: {e}")
        sys.exit(1)

    try:
        data = parse_autodefinido(html)
        print(f"  Fecha: {data['date']}")
        print(f"  Cuadrícula: {data['grid_cols']}x{data['grid_rows']}")
        print(f"  Pistas encontradas: {data['total_clues']}")
    except Exception as e:
        print(f"  ERROR parseando HTML: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Guardar JSON
    output_dir = os.environ.get("DATA_DIR", "data")
    filename = save_puzzle(data, output_dir)
    print(f"  Guardado en: {filename}")

    # Actualizar índice
    index = update_index(output_dir)
    print(f"  Índice actualizado: {index['total']} autodefinidos")

    print("  ¡Listo!")


if __name__ == "__main__":
    main()
