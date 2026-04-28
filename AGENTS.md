# AGENTS.md — Seguimiento Licitaciones (Radar de Licitaciones)

## Quick start

```bash
pip install requests beautifulsoup4 flask flask-cors
python servidor_licitaciones.py          # Flask on :5050, auto-scrapes if cache empty
open http://localhost:5050               # serves Index02.html as dashboard
```

Verify:
```bash
python scraper_licitaciones.py --solo-api --max 10 --json   # quick scrape test
curl http://localhost:5050/api/estado                        # server health check
```

No automated tests exist. Verify by running the server and checking the browser.

## Architecture

Three files, no build step:

| File | Role | Lines |
|------|------|-------|
| `scraper_licitaciones.py` | CLI scraper: Gencat API (primary) + HTML scraping (secondary) | ~870 |
| `servidor_licitaciones.py` | Flask server on :5050, imports scraper, background threads, disk cache | ~310 |
| `Index02.html` | SPA dashboard with Google Charts, PapaParse, embedded CSV fallback | ~890 |

**Data flow**: `scraper_licitaciones.scrape_todo()` → server stores in `cache` dict → `/api/licitaciones` JSON → dashboard renders.

**Primary data source**: Gencat PSCP open data API at `analisi.transparenciacatalunya.cat/resource/ybgg-dgi6.json` (SoQL queries). Covers all Catalan public entities in structured JSON. HTML scraping (ICAC, Conforcat, 7 generic portals) is secondary and yields far fewer results.

## Critical gotchas

- **Scoring logic is duplicated** in Python (`calcular_score` at scraper:274) and JavaScript (`calcularScore` at Index02.html:551). Any change to the rubric MUST be applied to both. The rubric: importe 30%, norma 25%, urgencia 20%, tipo organismo 15%, provincia 10%.
- **`cache_lock`** (threading.Lock) must protect ALL reads/writes of the `cache` dict, including the `scraping_en_curso` flag. Race condition was already fixed once — do not regress.
- **ENS detection** uses `re.search(r'\bENS\b', t)` — word boundary is required to avoid false positives with ENSAYO, ENSENANZA, etc.
- **CSV delimiter is semicolon** (`;`) because tender descriptions contain commas. Both `guardar_csv` and PapaParse in the HTML use `;`.
- **Dict keys have NO accent marks**: `"Fecha publicacion"`, `"Area"`, `"Norma afectada"`. Not `"Área"`, not `"Fecha publicación"`.
- **Deduplication key** is `(organismo.lower(), objeto[:100].lower())` — same logic in Python (`deduplicar`) and JS (`deduplicate`). Keep in sync.
- **`FUENTES` dict** is a catalog for display/metadata only. Actual scrape targets are hardcoded in `scrape_portales_html()` and `ORGANOS_GENCAT` list.
- **Server catch-all route** (`/<path:filename>`) serves any file in WORK_DIR — acceptable for localhost only, never expose to the internet.

## Code conventions

- All code, comments, variable names, and UI strings in **Spanish**. Data may be in Catalan.
- Python: no type hints, no classes, f-strings, `encoding='utf-8'`, `snake_case` in Spanish, shebang `#!/usr/bin/env python3`, `log = logging.getLogger(__name__)`.
- No build tools, no linters, no formatters, no CI.
- CODANOR branding: primary `#1a4d7c` (dashboard), `#178DC2` (corporate). Font: Montserrat (web).

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/licitaciones` | All tenders (supports query filters: area, tipo, provincia, norma, min_score) |
| POST | `/api/actualizar` | Launch background scraping (body: `{dias, max, solo_api}`) |
| GET | `/api/estado` | System status, total count, scraping flag |
| GET | `/api/fuentes` | Configured source catalog |
| GET | `/api/estadisticas` | Summary stats by tipo/area/provincia/norma |

## File layout

```
├── scraper_licitaciones.py       # Scraper (CLI + library)
├── servidor_licitaciones.py      # Flask server
├── Index02.html                  # Dashboard SPA
├── datos.csv                     # Fallback CSV (embedded copy also in HTML)
├── cache_licitaciones.json       # Auto-generated disk cache (gitignored: no)
├── datos_actualizados.csv        # Auto-generated CSV from scraping
├── Manuales/                     # User manual (v1 + v2 + v3 .docx)
├── Prompt/                       # Prompt engineering documentation
├── Documentacion/                # Pipeline docs, directives
├── Plantillas/                   # Excel templates
└── Datos_historicos/             # Old JSON/CSV exports
```

## Province detection

NUTS codes from the API: ES511=Barcelona, ES512=Girona, ES513=Lleida, ES514=Tarragona. Fallback heuristic uses city names in organism name.

## Norms detected

ISO27001, ENS, NIS2, ISO22301, ISO9001, ISO14001, ISO45001, ISO50001, ISO13485 — detected via keyword matching in `detectar_norma()`. The JS norma filter `<select>` must list all of these.
