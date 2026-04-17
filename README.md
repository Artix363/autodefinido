# 📰 Archivo Autodefinido — El País

Archivo histórico automático del autodefinido diario de El País.
**Gratuito · Sin servidor · Automatizado** via GitHub Actions + GitHub Pages.

---

## ¿Cómo funciona?

```
Cada noche a las 23:45
    ↓
GitHub Actions ejecuta scrape.py
    ↓
Descarga el HTML de elpais.com/juegos/autodefinido/diario/dia/
    ↓
Extrae cuadrícula y pistas → guarda data/YYYY-MM-DD.json
    ↓
GitHub Pages sirve la web con el archivo histórico
```

---

## Configuración (10-15 minutos)

### 1. Crear el repositorio en GitHub

1. Ve a [github.com/new](https://github.com/new)
2. Nombre: `autodefinido` (o el que quieras)
3. Visibilidad: **Público** (necesario para GitHub Pages gratis)
4. Clic en **"Create repository"**

### 2. Subir los archivos

En tu ordenador, abre una terminal:

```bash
# Clona el repositorio vacío
git clone https://github.com/TU_USUARIO/autodefinido.git
cd autodefinido

# Copia estos archivos al repositorio:
# - scrape.py          → raíz
# - .github/           → raíz (con toda su estructura)
# - web/index.html     → raíz (renómbralo a index.html)
# - data/              → créala vacía

# Primer commit
git add .
git commit -m "Configuración inicial"
git push
```

### 3. Activar GitHub Pages

1. Ve a tu repositorio → **Settings** → **Pages**
2. En "Source" selecciona: **Deploy from a branch**
3. Branch: `main` / Folder: `/ (root)`
4. Clic **Save**

En 2-3 minutos tu web estará en:
`https://TU_USUARIO.github.io/autodefinido/`

### 4. Ejecutar el primer scraping manualmente

1. Ve a tu repositorio → pestaña **Actions**
2. Clic en "Scrape Autodefinido Diario"
3. Clic en **"Run workflow"** → **"Run workflow"**

Espera ~30 segundos. Verás aparecer el primer JSON en la carpeta `data/`.

### 5. Listo 🎉

A partir de ahora, cada noche a las 23:45 UTC (madrugada en España) el sistema:
- Descargará el autodefinido del día
- Lo guardará como JSON
- Actualizará la web automáticamente

---

## Estructura de archivos

```
autodefinido/
├── .github/
│   └── workflows/
│       └── scrape.yml      ← Automatización diaria
├── data/
│   ├── index.json          ← Índice de todas las fechas
│   ├── 2026-04-17.json     ← Un archivo por día
│   └── 2026-04-18.json
├── index.html              ← La web pública
└── scrape.py               ← El script de scraping
```

---

## Formato del JSON

```json
{
  "date": "2026-04-17",
  "scraped_at": "2026-04-17T23:46:12Z",
  "source": "https://elpais.com/juegos/autodefinido/diario/dia/",
  "grid_cols": 10,
  "grid_rows": 12,
  "grid": [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ...
  ],
  "clues": [
    {
      "text": "COLECTIVO EN ACCIÓN",
      "col": 0,
      "row": 0,
      "direction": "down"
    },
    ...
  ],
  "total_clues": 34
}
```

**Valores de `grid`:**
- `0` = celda negra (bloqueada)
- `1` = celda jugable (el usuario escribe)
- `2` = celda de pista (contiene texto)

**Valores de `direction`:**
- `"right"` = pista horizontal
- `"down"` = pista vertical
- `"both"` = pista en ambas direcciones
- `"unknown"` = no se pudo determinar la dirección

---

## Ejecutar localmente

```bash
pip install requests beautifulsoup4 lxml
python scrape.py
```

---

## Nota legal

Este proyecto es de uso personal. Los datos pertenecen a El País / Grupo Prisa.
No redistribuyas los datos con fines comerciales.
