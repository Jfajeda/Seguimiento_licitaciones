#!/usr/bin/env python3
"""
Servidor Flask para el Radar de Licitaciones
=============================================
Proporciona una API REST para que Index02.html pueda:
  - Obtener licitaciones en tiempo real
  - Actualizar datos bajo demanda

Ejecutar: python3 servidor_licitaciones.py
Acceder:  http://localhost:5050
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
import time
import logging
from datetime import datetime
from threading import Thread, Lock

# Importar el scraper
from scraper_licitaciones import scrape_todo, guardar_csv, guardar_json

# ─── Configuración ───────────────────────────────────────────────────────────
app = Flask(__name__, static_folder='.')
CORS(app, origins=['http://localhost:5050', 'http://127.0.0.1:5050'])  # Restringir a localhost

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ─── Cache en memoria ───────────────────────────────────────────────────────
cache = {
    "licitaciones": [],
    "ultima_actualizacion": None,
    "scraping_en_curso": False,
    "error": None,
}
cache_lock = Lock()

CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache_licitaciones.json")
WORK_DIR = os.path.dirname(os.path.abspath(__file__))


def cargar_cache():
    """Carga datos del archivo de caché si existe."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with cache_lock:
                cache["licitaciones"] = data.get("licitaciones", [])
                cache["ultima_actualizacion"] = data.get("ultima_actualizacion")
            log.info(f"Cache cargada: {len(cache['licitaciones'])} licitaciones")
        except Exception as e:
            log.warning(f"Error cargando cache: {e}")


def guardar_cache():
    """Guarda datos en archivo de caché."""
    try:
        with cache_lock:
            datos = {
                "licitaciones": cache["licitaciones"][:],
                "ultima_actualizacion": cache["ultima_actualizacion"],
            }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        log.info("Cache guardada en disco")
    except Exception as e:
        log.warning(f"Error guardando cache: {e}")


def ejecutar_scraping(dias=90, max_api=1000, solo_api=False):
    """Ejecuta el scraping en background."""
    with cache_lock:
        if cache["scraping_en_curso"]:
            return
        cache["scraping_en_curso"] = True
        cache["error"] = None

    try:
        licitaciones = scrape_todo(
            dias_atras=dias,
            max_api=max_api,
            solo_api=solo_api,
        )

        with cache_lock:
            cache["licitaciones"] = licitaciones
            cache["ultima_actualizacion"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            cache["scraping_en_curso"] = False

        # Guardar en disco
        guardar_cache()

        # También guardar CSV para uso offline
        csv_path = os.path.join(WORK_DIR, "datos_actualizados.csv")
        guardar_csv(licitaciones, csv_path)

    except Exception as e:
        log.error(f"Error en scraping: {e}")
        with cache_lock:
            cache["scraping_en_curso"] = False
            cache["error"] = str(e)


# ─── Rutas API ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Sirve el archivo Index02.html."""
    return send_from_directory(WORK_DIR, 'Index02.html')


@app.route('/api/licitaciones')
def api_licitaciones():
    """
    GET /api/licitaciones
    Devuelve todas las licitaciones en formato JSON.
    
    Query params opcionales:
      - area: Filtrar por área
      - tipo: Filtrar por tipo de organismo
      - provincia: Filtrar por provincia
      - norma: Filtrar por norma afectada
      - vigencia: 'activas', 'urgentes', 'caducadas'
      - min_score: Score mínimo
    """
    with cache_lock:
        data = cache["licitaciones"][:]
        ultima = cache["ultima_actualizacion"]

    # Aplicar filtros opcionales
    area = request.args.get('area')
    tipo = request.args.get('tipo')
    provincia = request.args.get('provincia')
    norma = request.args.get('norma')
    min_score = request.args.get('min_score', type=float)

    if area and area != 'all':
        data = [d for d in data if area.lower() in (d.get('Area', '') or '').lower()]
    if tipo and tipo != 'all':
        data = [d for d in data if tipo.lower() in (d.get('Tipo', '') or '').lower()]
    if provincia and provincia != 'all':
        data = [d for d in data if provincia.lower() in (d.get('Provincia', '') or '').lower()]
    if norma and norma != 'all':
        data = [d for d in data if norma.lower() in (d.get('Norma afectada', '') or '').lower()]
    if min_score is not None:
        data = [d for d in data if (d.get('Valoracion', 0) or 0) >= min_score]

    return jsonify({
        "total": len(data),
        "ultima_actualizacion": ultima,
        "scraping_en_curso": cache["scraping_en_curso"],
        "licitaciones": data,
    })


@app.route('/api/actualizar', methods=['POST'])
def api_actualizar():
    """
    POST /api/actualizar
    Lanza el scraping en segundo plano.
    
    Body JSON opcional:
      - dias: Días hacia atrás (default: 90)
      - max: Máximo resultados API (default: 1000)
      - solo_api: Solo usar API Gencat (default: false)
    """
    with cache_lock:
        en_curso = cache["scraping_en_curso"]
    if en_curso:
        return jsonify({
            "status": "en_curso",
            "mensaje": "Ya hay un scraping en curso. Por favor espere.",
        }), 409

    body = request.get_json(silent=True) or {}
    dias = body.get("dias", 90)
    max_api = body.get("max", 1000)
    solo_api = body.get("solo_api", False)

    # Ejecutar en background
    thread = Thread(
        target=ejecutar_scraping,
        args=(dias, max_api, solo_api),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "status": "iniciado",
        "mensaje": f"Scraping iniciado (últimos {dias} días, max {max_api} resultados)",
    })


@app.route('/api/estado')
def api_estado():
    """GET /api/estado - Estado actual del sistema."""
    from scraper_licitaciones import FUENTES
    with cache_lock:
        return jsonify({
            "total_licitaciones": len(cache["licitaciones"]),
            "ultima_actualizacion": cache["ultima_actualizacion"],
            "scraping_en_curso": cache["scraping_en_curso"],
            "error": cache["error"],
            "fuentes_configuradas": sum(len(v) for v in FUENTES.values()),
        })


@app.route('/api/fuentes')
def api_fuentes():
    """GET /api/fuentes - Lista de fuentes configuradas."""
    from scraper_licitaciones import FUENTES
    return jsonify(FUENTES)


@app.route('/api/estadisticas')
def api_estadisticas():
    """GET /api/estadisticas - Estadísticas resumen."""
    with cache_lock:
        data = cache["licitaciones"][:]

    if not data:
        return jsonify({"error": "No hay datos. Ejecute /api/actualizar primero."})

    # Contar por tipo
    por_tipo = {}
    por_area = {}
    por_provincia = {}
    por_norma = {}
    importes = []

    for d in data:
        t = d.get('Tipo', 'N/A')
        por_tipo[t] = por_tipo.get(t, 0) + 1

        a = d.get('Area', 'N/A')
        por_area[a] = por_area.get(a, 0) + 1

        p = d.get('Provincia', 'N/A')
        por_provincia[p] = por_provincia.get(p, 0) + 1

        n = d.get('Norma afectada', '')
        if n:
            por_norma[n] = por_norma.get(n, 0) + 1

        imp = d.get('Importe', 0) or 0
        try:
            importes.append(float(imp))
        except (ValueError, TypeError):
            pass

    return jsonify({
        "total": len(data),
        "por_tipo": por_tipo,
        "por_area": por_area,
        "por_provincia": por_provincia,
        "por_norma": por_norma,
        "importe_total": sum(importes),
        "importe_medio": sum(importes) / len(importes) if importes else 0,
    })


# ─── Servir archivos estáticos ──────────────────────────────────────────────

# Whitelist explícita — impide path traversal (OWASP A5)
_STATIC_WHITELIST = {
    'datos.csv',
    'datos_actualizados.csv',
    'cache_licitaciones.json',
    'favicon.ico',
}


@app.route('/<path:filename>')
def static_files(filename):
    """Sirve archivos estáticos del directorio de trabajo (solo whitelist)."""
    if filename not in _STATIC_WHITELIST:
        abort(404)
    return send_from_directory(WORK_DIR, filename)


# ─── Inicio ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  SERVIDOR RADAR DE LICITACIONES - CODANOR")
    print("=" * 60)
    print()
    print("  Abrir en navegador: http://localhost:5050")
    print()
    print("  API endpoints:")
    print("    GET  /api/licitaciones  - Obtener licitaciones")
    print("    POST /api/actualizar    - Lanzar scraping")
    print("    GET  /api/estado        - Estado del sistema")
    print("    GET  /api/fuentes       - Fuentes configuradas")
    print("    GET  /api/estadisticas  - Estadísticas resumen")
    print()
    print("=" * 60)
    print()

    # Cargar caché existente
    cargar_cache()

    # Si no hay datos en cache, lanzar scraping automático (solo API, rápido)
    if not cache["licitaciones"]:
        log.info("No hay datos en cache. Lanzando scraping inicial (solo API)...")
        thread = Thread(
            target=ejecutar_scraping,
            args=(90, 500, True),
            daemon=True,
        )
        thread.start()

    app.run(host='127.0.0.1', port=5050, debug=False)
