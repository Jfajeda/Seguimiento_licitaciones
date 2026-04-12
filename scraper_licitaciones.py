#!/usr/bin/env python3
"""
Scraper de Licitaciones Públicas de Cataluña
=============================================
Fuentes:
  1. API abierta Gencat PSCP (analisi.transparenciacatalunya.cat) - Fuente principal
  2. Scraping HTML directo de portales específicos
  3. DIBA open data API

Ejecutar: python3 scraper_licitaciones.py
Servidor: python3 scraper_licitaciones.py --server
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import time
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote
import argparse

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ─── Configuración ───────────────────────────────────────────────────────────
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,ca;q=0.8',
}

REQUEST_TIMEOUT = 20
RATE_LIMIT_SECONDS = 1.5  # pausa entre peticiones

# ─── Catálogo de Fuentes ────────────────────────────────────────────────────
# Todas las URLs proporcionadas, organizadas por categoría
FUENTES = {
    "Generalitat": [
        {"nombre": "Generalitat de Catalunya", "url": "https://contractacio.gencat.cat", "provincia": "Barcelona", "tipo": "Generalitat"},
        {"nombre": "Servei Català de la Salut", "url": "https://catsalut.gencat.cat", "provincia": "Barcelona", "tipo": "Generalitat"},
        {"nombre": "Institut Català de la Salut", "url": "https://ics.gencat.cat", "provincia": "Barcelona", "tipo": "Generalitat"},
        {"nombre": "Agència Catalana de l'Aigua", "url": "https://aca.gencat.cat", "provincia": "Barcelona", "tipo": "Generalitat"},
        {"nombre": "Ferrocarrils de la Generalitat de Catalunya", "url": "https://transparencia.fgc.cat", "provincia": "Barcelona", "tipo": "Empresa pública"},
        {"nombre": "Institut Català d'Arqueologia Clàssica", "url": "https://icac.cat/es/quienes-somos/perfil-del-contratante/", "provincia": "Tarragona", "tipo": "Generalitat"},
        {"nombre": "Consorci per a la Formació Contínua de Catalunya", "url": "https://conforcat.gencat.cat/es/consorci/perfil-del-contractant/", "provincia": "Barcelona", "tipo": "Consorci"},
    ],
    "Diputacions": [
        {"nombre": "Diputació de Barcelona", "url": "https://www.diba.cat/perfil-contractant", "provincia": "Barcelona", "tipo": "Diputació"},
        {"nombre": "Diputació de Girona", "url": "https://www.ddgi.cat", "provincia": "Girona", "tipo": "Diputació"},
        {"nombre": "Diputació de Tarragona", "url": "https://www.dipta.cat", "provincia": "Tarragona", "tipo": "Diputació"},
        {"nombre": "Diputació de Lleida", "url": "https://www.diputaciolleida.cat", "provincia": "Lleida", "tipo": "Diputació"},
    ],
    "Ajuntaments": [
        {"nombre": "Ajuntament de Barcelona", "url": "https://seuelectronica.ajuntament.barcelona.cat", "provincia": "Barcelona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de L'Hospitalet de Llobregat", "url": "https://seuelectronica.l-h.cat", "provincia": "Barcelona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Badalona", "url": "https://seu.badalona.cat", "provincia": "Barcelona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Terrassa", "url": "https://seuelectronica.terrassa.cat", "provincia": "Barcelona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Sabadell", "url": "https://seu.sabadell.cat", "provincia": "Barcelona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Girona", "url": "https://web.girona.cat/perfildelcontractant", "provincia": "Girona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Tarragona", "url": "https://seu.tarragona.cat", "provincia": "Tarragona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Lleida", "url": "https://seu.paeria.cat", "provincia": "Lleida", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Mataró", "url": "https://seu.mataro.cat", "provincia": "Barcelona", "tipo": "Ajuntament"},
        {"nombre": "Ajuntament de Reus", "url": "https://seu.reus.cat", "provincia": "Tarragona", "tipo": "Ajuntament"},
    ],
    "Consorcis": [
        {"nombre": "Àrea Metropolitana de Barcelona", "url": "https://www.amb.cat/es/web/amb/seu-electronica/perfil-de-contractant", "provincia": "Barcelona", "tipo": "Consorci"},
        {"nombre": "Consorci d'Educació de Barcelona", "url": "https://www.edubcn.cat/es/el_consorcio/gestion_economica/perfil_del_contratante", "provincia": "Barcelona", "tipo": "Consorci"},
        {"nombre": "Consorci Sanitari de Barcelona", "url": "https://www.csbcn.cat", "provincia": "Barcelona", "tipo": "Consorci"},
        {"nombre": "Consorci de la Zona Franca de Barcelona", "url": "https://www.zfbarcelona.es", "provincia": "Barcelona", "tipo": "Consorci"},
    ],
    "Universitats": [
        {"nombre": "Universitat de Barcelona", "url": "https://www.ub.edu", "provincia": "Barcelona", "tipo": "Universidad"},
        {"nombre": "Universitat Autònoma de Barcelona", "url": "https://seuelectronica.uab.cat", "provincia": "Barcelona", "tipo": "Universidad"},
        {"nombre": "Universitat Politècnica de Catalunya", "url": "https://seuelectronica.upc.edu", "provincia": "Barcelona", "tipo": "Universidad"},
        {"nombre": "Universitat Pompeu Fabra", "url": "https://seuelectronica.upf.edu", "provincia": "Barcelona", "tipo": "Universidad"},
        {"nombre": "Universitat Oberta de Catalunya", "url": "https://seu-electronica.uoc.edu/es/perfil-contratante", "provincia": "Barcelona", "tipo": "Universidad"},
    ],
}

# ─── Mapeos de nombres de órganos para la API Gencat ────────────────────────
# Estos son los nombres que aparecen en la API de datos abiertos de la Gencat
ORGANOS_GENCAT = [
    # Generalitat
    "Generalitat de Catalunya",
    "Servei Català de la Salut",
    "Institut Català de la Salut",
    "Agència Catalana de l'Aigua",
    "Ferrocarrils de la Generalitat de Catalunya",
    "Institut Català d'Arqueologia Clàssica",
    # Diputaciones
    "Diputació de Barcelona",
    "Diputació de Girona",
    "Diputació de Tarragona",
    "Diputació de Lleida",
    # Ajuntaments
    "Ajuntament de Barcelona",
    "Ajuntament de l'Hospitalet de Llobregat",
    "Ajuntament de Badalona",
    "Ajuntament de Terrassa",
    "Ajuntament de Sabadell",
    "Ajuntament de Girona",
    "Ajuntament de Tarragona",
    "Ajuntament de Lleida",
    "Ajuntament de Mataró",
    "Ajuntament de Reus",
    # Consorcis / Àrea Metropolitana
    "Àrea Metropolitana de Barcelona",
    "Consorci d'Educació de Barcelona",
    "Consorci Sanitari de Barcelona",
    "Consorci de la Zona Franca de Barcelona",
    "Consorci per a la Formació Contínua de Catalunya",
    # Universitats
    "Universitat de Barcelona",
    "Universitat Autònoma de Barcelona",
    "Universitat Politècnica de Catalunya",
    "Universitat Pompeu Fabra",
    "Universitat Oberta de Catalunya",
]

# Mapeo NOM_ORGAN -> Tipo y Provincia
ORGAN_META = {}
for cat, fuentes_list in FUENTES.items():
    for f in fuentes_list:
        ORGAN_META[f["nombre"].lower()] = {
            "tipo": f["tipo"],
            "provincia": f["provincia"],
            "url_portal": f["url"],
        }


# ─── Funciones auxiliares ────────────────────────────────────────────────────

def detectar_norma(texto):
    """Detecta normas de certificación en el texto."""
    if not texto:
        return ""
    normas = []
    t = texto.upper()
    if "ISO 27001" in t or "ISO27001" in t or "SEGURETAT DE LA INFORMACIÓ" in t:
        normas.append("ISO27001")
    if re.search(r'\bENS\b', t) or "ESQUEMA NACIONAL DE SEGURETAT" in t or "ESQUEMA NACIONAL DE SEGURIDAD" in t:
        normas.append("ENS")
    if "NIS2" in t or "NIS 2" in t:
        normas.append("NIS2")
    if "ISO 22301" in t or "ISO22301" in t or "CONTINUÏTAT" in t:
        normas.append("ISO22301")
    if "ISO 9001" in t or "ISO9001" in t or "QUALITAT" in t or "CALIDAD" in t:
        normas.append("ISO9001")
    if "ISO 14001" in t or "ISO14001" in t or "MEDIAMBIENT" in t or "MEDIOAMBIENTAL" in t:
        normas.append("ISO14001")
    if "ISO 45001" in t or "ISO45001" in t or "SEGURETAT LABORAL" in t:
        normas.append("ISO45001")
    if "ISO 50001" in t or "ISO50001" in t or "ENERGÈTIC" in t:
        normas.append("ISO50001")
    if "ISO 13485" in t or "ISO13485" in t:
        normas.append("ISO13485")
    return "/".join(normas) if normas else ""


def detectar_area(texto):
    """Detecta el área/sector de la licitación.

    NOTA: El orden de evaluación importa. Las categorías más específicas
    (Informática, Obras) se evalúan antes que las genéricas (Servicios, Otros)
    para evitar falsos positivos. Por ejemplo, 'servei informàtic' devuelve
    'Informática', no 'Servicios'.
    """
    if not texto:
        return "Otros"
    t = texto.upper()
    if any(w in t for w in ["INFORMÀTIC", "INFORMATIC", "SOFTWARE", "SISTEMA D'INFORMACIÓ", "CPD",
                             "DIGITALITZ", "CIBERSEGURE", "CLOUD", "DADES", "WEB", "APP"]):
        return "Informática"
    if any(w in t for w in ["OBRA", "REFORMA", "CONSTRUCCIÓ", "EDIFICI", "PAVIMENT"]):
        return "Obras"
    if any(w in t for w in ["MANTENIM", "CONSERVACI"]):
        return "Mantenimiento"
    if any(w in t for w in ["FORMACI", "DOCENT", "CAPACITACI", "CURS"]):
        return "Formación"
    if any(w in t for w in ["SANIT", "HOSPITAL", "MÈDIC", "FARMAC", "SALUT", "CLÍNIC"]):
        return "Sanidad"
    if any(w in t for w in ["EDUCAT", "ESCOL", "UNIVERSIT"]):
        return "Educación"
    if any(w in t for w in ["CULTUR", "BIBLIOTE", "MUSE"]):
        return "Cultural"
    if any(w in t for w in ["NETEJA", "LIMPI"]):
        return "Servicios"
    if any(w in t for w in ["SUBMINISTRAMENT", "SUMINISTR", "EQUIP", "MATERIAL", "MOBILIARI"]):
        return "Suministros"
    if any(w in t for w in ["SERVEI", "SERVICIO", "ASSISTÈNCI", "CONSULTORI"]):
        return "Servicios"
    return "Otros"


def fecha_iso_a_ddmmyyyy(fecha_iso):
    """Convierte '2026-02-11T14:02:00.000' a '11/02/2026'."""
    if not fecha_iso:
        return ""
    try:
        dt = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00").split(".")[0])
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""


def detectar_tipo_desde_nombre(nombre_organ):
    """Infiere el tipo de organismo desde su nombre."""
    n = nombre_organ.lower()
    for nombre_conocido, meta in ORGAN_META.items():
        if nombre_conocido in n or n in nombre_conocido:
            return meta["tipo"], meta["provincia"]
    # Heurísticas generales
    if "ajuntament" in n:
        return "Ajuntament", detectar_provincia_desde_nombre(n)
    if "generalitat" in n or "gencat" in n:
        return "Generalitat", "Barcelona"
    if "diputació" in n or "diputaci" in n:
        return detectar_diputacio(n)
    if "universit" in n:
        return "Universidad", "Barcelona"
    if "hospital" in n or "sanitari" in n or "salut" in n:
        return "Hospital", "Barcelona"
    if "consorci" in n or "àrea metropolitana" in n:
        return "Consorci", "Barcelona"
    if "empresa" in n or "sau" in n or "spm" in n:
        return "Empresa pública", "Barcelona"
    return "Otros", "Barcelona"


def detectar_diputacio(nombre):
    if "girona" in nombre:
        return "Diputació", "Girona"
    if "tarragona" in nombre:
        return "Diputació", "Tarragona"
    if "lleida" in nombre:
        return "Diputació", "Lleida"
    return "Diputació", "Barcelona"


def detectar_provincia_desde_nombre(nombre):
    n = nombre.lower()
    if any(c in n for c in ["girona", "figueres", "blanes", "lloret", "olot", "salt"]):
        return "Girona"
    if any(c in n for c in ["tarragona", "reus", "tortosa", "valls", "cambrils"]):
        return "Tarragona"
    if any(c in n for c in ["lleida", "balaguer", "tàrrega", "mollerussa"]):
        return "Lleida"
    return "Barcelona"


def detectar_provincia_nuts(codi_nuts):
    """Detecta provincia desde código NUTS."""
    if not codi_nuts:
        return "Barcelona"
    mapa = {
        "ES511": "Barcelona",
        "ES512": "Girona",
        "ES513": "Lleida",
        "ES514": "Tarragona",
    }
    return mapa.get(codi_nuts, "Barcelona")


def calcular_score(importe, norma, dias_restantes, tipo, provincia):
    """Calcula score automático según la rúbrica CODANOR."""
    score = 0

    # Importe (30%)
    try:
        imp = float(importe) if importe else 0
    except (ValueError, TypeError):
        imp = 0
    if imp > 1000000:
        score += 3.0
    elif imp > 500000:
        score += 2.4
    elif imp > 100000:
        score += 1.8
    elif imp > 50000:
        score += 1.2
    elif imp > 0:
        score += 0.6

    # Norma (25%)
    if norma:
        n = norma.upper()
        if any(x in n for x in ["ISO27001", "ENS", "NIS2"]):
            score += 2.5
        elif "ISO22301" in n:
            score += 2.0
        elif "ISO9001" in n:
            score += 1.75
        elif "ISO14001" in n:
            score += 1.25
        else:
            score += 0.75

    # Urgencia (20%)
    if dias_restantes is not None:
        if dias_restantes < 0:
            score += 0
        elif dias_restantes <= 3:
            score += 2.0
        elif dias_restantes <= 7:
            score += 1.5
        elif dias_restantes <= 14:
            score += 1.0
        else:
            score += 0.5

    # Tipo organismo (15%)
    if tipo:
        t = tipo.lower()
        if "generalitat" in t:
            score += 1.5
        elif "hospital" in t:
            score += 1.35
        elif "universit" in t or "universidad" in t:
            score += 1.05
        elif "ajuntament" in t:
            score += 0.9
        elif any(x in t for x in ["empresa", "consorci", "diputaci"]):
            score += 0.75

    # Provincia (10%)
    if provincia:
        if "barcelona" in provincia.lower():
            score += 1.0
        else:
            score += 0.8

    return min(10, round(score, 1))


def dias_restantes(fecha_limite_str):
    """Calcula días restantes desde hoy a la fecha límite (dd/mm/yyyy)."""
    if not fecha_limite_str:
        return None
    try:
        parts = fecha_limite_str.split("/")
        if len(parts) == 3:
            fecha = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            return (fecha - datetime.now()).days
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# FUENTE 1: API Abierta Gencat PSCP (PRINCIPAL)
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_gencat_api(organos_filtro=None, dias_atras=90, max_resultados=1000):
    """
    Consulta la API abierta de datos de contractación pública de Catalunya.
    Dataset: ybgg-dgi6 en analisi.transparenciacatalunya.cat
    
    Filtra por:
    - fase_publicacio = 'Anunci de licitació' (licitaciones abiertas)
    - data_publicacio_anunci en los últimos N días
    
    Devuelve lista de diccionarios normalizados.
    """
    licitaciones = []
    base_url = "https://analisi.transparenciacatalunya.cat/resource/ybgg-dgi6.json"

    # Calcular fecha de corte
    fecha_corte = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%dT00:00:00.000")

    # Construir filtro SoQL
    # Fases que nos interesan: licitaciones abiertas o en evaluación
    fases = [
        "Anunci de licitació",
        "Anunci previ",
        "Avaluació",
    ]
    fases_filter = " OR ".join([f"fase_publicacio='{f}'" for f in fases])

    # Filtro temporal: solo licitaciones recientes
    where_clauses = [
        f"({fases_filter})",
        f"data_publicacio_anunci > '{fecha_corte}'",
    ]

    # Consulta paginada
    offset = 0
    limit = 500
    total_fetched = 0

    log.info("=" * 60)
    log.info("FUENTE 1: API Gencat PSCP (Datos Abiertos Catalunya)")
    log.info("=" * 60)

    while total_fetched < max_resultados:
        where = " AND ".join(where_clauses)
        params = {
            "$where": where,
            "$order": "data_publicacio_anunci DESC",
            "$limit": limit,
            "$offset": offset,
        }

        try:
            log.info(f"  Consultando API (offset={offset})...")
            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            if resp.status_code != 200:
                log.warning(f"  API devolvió status {resp.status_code}")
                break

            datos = resp.json()
            if not datos:
                log.info("  No más resultados.")
                break

            for d in datos:
                nom_organ = d.get("nom_organ", "")

                # Si hay filtro de órganos, solo incluir los que coinciden
                if organos_filtro:
                    match = False
                    for organo in organos_filtro:
                        if organo.lower() in nom_organ.lower() or nom_organ.lower() in organo.lower():
                            match = True
                            break
                    if not match:
                        continue

                # Extraer datos
                denominacion = d.get("denominacio", "")
                objeto = d.get("objecte_contracte", denominacion)
                tipo_contrato = d.get("tipus_contracte", "")

                # Importes
                importe_str = d.get("valor_estimat_contracte", "0")
                try:
                    importe = float(importe_str) if importe_str else 0
                except (ValueError, TypeError):
                    importe = 0

                # Fechas
                fecha_pub_raw = d.get("data_publicacio_anunci", d.get("data_publicacio_previ", ""))
                fecha_pub = fecha_iso_a_ddmmyyyy(fecha_pub_raw)

                # Fecha límite de presentación
                fecha_lim_raw = d.get("data_limit_presentacio", "")
                fecha_lim = fecha_iso_a_ddmmyyyy(fecha_lim_raw)

                # Provincia desde código NUTS
                provincia = detectar_provincia_nuts(d.get("codi_nuts", ""))

                # Tipo de organismo
                tipo, prov_detect = detectar_tipo_desde_nombre(nom_organ)
                if not provincia or provincia == "Barcelona":
                    provincia = prov_detect

                # Norma y área
                texto_completo = f"{denominacion} {objeto} {tipo_contrato}"
                norma = detectar_norma(texto_completo)
                area = detectar_area(texto_completo)

                # URL
                enlace = d.get("enllac_publicacio", {})
                url_licit = enlace.get("url", "") if isinstance(enlace, dict) else str(enlace)
                if not url_licit:
                    url_licit = f"https://contractaciopublica.cat/ca/detall-publicacio/{d.get('codi_expedient', '')}"

                # Score
                dias = dias_restantes(fecha_lim)
                score = calcular_score(importe, norma, dias, tipo, provincia)

                licitaciones.append({
                    "Fecha publicacion": fecha_pub,
                    "Fecha limite": fecha_lim,
                    "Organismo": nom_organ,
                    "Tipo": tipo,
                    "Provincia": provincia,
                    "Objeto": objeto[:300] if objeto else denominacion[:300],
                    "Area": area,
                    "Importe": importe,
                    "Valoracion": score,
                    "Norma afectada": norma,
                    "URL": url_licit,
                    "Fuente": "Gencat PSCP",
                })

            total_fetched += len(datos)
            offset += limit
            log.info(f"  Obtenidos {len(datos)} registros (total: {total_fetched})")

            time.sleep(RATE_LIMIT_SECONDS)

        except requests.exceptions.Timeout:
            log.warning("  Timeout en API Gencat")
            break
        except Exception as e:
            log.error(f"  Error consultando API Gencat: {e}")
            break

    log.info(f"  TOTAL desde Gencat API: {len(licitaciones)} licitaciones")
    return licitaciones


# ═══════════════════════════════════════════════════════════════════════════════
# FUENTE 2: Scraping HTML directo de portales específicos
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_icac():
    """Scraping del perfil del contratante del ICAC."""
    licitaciones = []
    url = "https://icac.cat/es/quienes-somos/perfil-del-contratante/"
    log.info(f"  Scraping: ICAC ({url})")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Buscar tablas o listados de licitaciones
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        texto = cols[0].get_text(strip=True)
                        link = cols[0].find('a')
                        url_lic = link['href'] if link and link.get('href') else url
                        if not url_lic.startswith('http'):
                            url_lic = urljoin(url, url_lic)
                        norma = detectar_norma(texto)
                        area = detectar_area(texto)
                        licitaciones.append({
                            "Fecha publicacion": datetime.now().strftime("%d/%m/%Y"),
                            "Fecha limite": "",
                            "Organismo": "Institut Català d'Arqueologia Clàssica",
                            "Tipo": "Generalitat",
                            "Provincia": "Tarragona",
                            "Objeto": texto[:300],
                            "Area": area,
                            "Importe": 0,
                            "Valoracion": 0,
                            "Norma afectada": norma,
                            "URL": url_lic,
                            "Fuente": "ICAC Web",
                        })
            log.info(f"    -> {len(licitaciones)} encontradas")
    except Exception as e:
        log.warning(f"    Error: {e}")
    return licitaciones


def scrape_conforcat():
    """Scraping del perfil del contratante del Conforcat."""
    licitaciones = []
    url = "https://conforcat.gencat.cat/es/consorci/perfil-del-contractant/"
    log.info(f"  Scraping: Conforcat ({url})")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Buscar enlaces a licitaciones
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                if any(kw in text.lower() for kw in ['licitaci', 'contracte', 'servei', 'subministr', 'obra']):
                    href = link['href']
                    if not href.startswith('http'):
                        href = urljoin(url, href)
                    norma = detectar_norma(text)
                    area = detectar_area(text)
                    licitaciones.append({
                        "Fecha publicacion": datetime.now().strftime("%d/%m/%Y"),
                        "Fecha limite": "",
                        "Organismo": "Consorci per a la Formació Contínua de Catalunya",
                        "Tipo": "Consorci",
                        "Provincia": "Barcelona",
                        "Objeto": text[:300],
                        "Area": area,
                        "Importe": 0,
                        "Valoracion": 0,
                        "Norma afectada": norma,
                        "URL": href,
                        "Fuente": "Conforcat Web",
                    })
            log.info(f"    -> {len(licitaciones)} encontradas")
    except Exception as e:
        log.warning(f"    Error: {e}")
    return licitaciones


def scrape_generico(nombre, url_base, tipo, provincia):
    """
    Scraping genérico: intenta encontrar licitaciones en la página.
    Busca tablas, listados, o enlaces con palabras clave.
    """
    licitaciones = []
    log.info(f"  Scraping genérico: {nombre} ({url_base})")
    try:
        resp = requests.get(url_base, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            log.warning(f"    Status {resp.status_code}")
            return licitaciones

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Estrategia 1: Buscar tablas con datos de licitaciones
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows[1:]:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    texto = " ".join(c.get_text(strip=True) for c in cols)
                    if any(kw in texto.lower() for kw in ['licitaci', 'contracte', 'expedient', 'adjudica']):
                        link = row.find('a', href=True)
                        url_lic = link['href'] if link else url_base
                        if not url_lic.startswith('http'):
                            url_lic = urljoin(url_base, url_lic)
                        norma = detectar_norma(texto)
                        area = detectar_area(texto)
                        licitaciones.append({
                            "Fecha publicacion": datetime.now().strftime("%d/%m/%Y"),
                            "Fecha limite": "",
                            "Organismo": nombre,
                            "Tipo": tipo,
                            "Provincia": provincia,
                            "Objeto": texto[:300],
                            "Area": area,
                            "Importe": 0,
                            "Valoracion": 0,
                            "Norma afectada": norma,
                            "URL": url_lic,
                            "Fuente": f"{nombre} Web",
                        })

        # Estrategia 2: Buscar listados (ul/li, div con clase)
        if not licitaciones:
            keywords = ['licitaci', 'contracte', 'contractaci', 'perfil']
            for el in soup.find_all(['li', 'div', 'article']):
                text = el.get_text(strip=True)[:500]
                if len(text) > 30 and any(kw in text.lower() for kw in keywords):
                    link = el.find('a', href=True)
                    url_lic = link['href'] if link else url_base
                    if not url_lic.startswith('http'):
                        url_lic = urljoin(url_base, url_lic)
                    norma = detectar_norma(text)
                    area = detectar_area(text)
                    licitaciones.append({
                        "Fecha publicacion": datetime.now().strftime("%d/%m/%Y"),
                        "Fecha limite": "",
                        "Organismo": nombre,
                        "Tipo": tipo,
                        "Provincia": provincia,
                        "Objeto": text[:300],
                        "Area": area,
                        "Importe": 0,
                        "Valoracion": 0,
                        "Norma afectada": norma,
                        "URL": url_lic,
                        "Fuente": f"{nombre} Web",
                    })

        log.info(f"    -> {len(licitaciones)} encontradas")
    except Exception as e:
        log.warning(f"    Error: {e}")
    return licitaciones


def scrape_portales_html():
    """Ejecuta scraping HTML en todos los portales."""
    licitaciones = []

    log.info("=" * 60)
    log.info("FUENTE 2: Scraping HTML de Portales")
    log.info("=" * 60)

    # Portales con scraper específico
    licitaciones.extend(scrape_icac())
    time.sleep(RATE_LIMIT_SECONDS)
    licitaciones.extend(scrape_conforcat())
    time.sleep(RATE_LIMIT_SECONDS)

    # Scraping genérico de portales accesibles
    portales_genericos = [
        ("Ferrocarrils de la Generalitat", "https://transparencia.fgc.cat", "Empresa pública", "Barcelona"),
        ("Diputació de Girona", "https://www.ddgi.cat", "Diputació", "Girona"),
        ("Diputació de Tarragona", "https://www.dipta.cat", "Diputació", "Tarragona"),
        ("Diputació de Lleida", "https://www.diputaciolleida.cat", "Diputació", "Lleida"),
        ("Ajuntament de Girona", "https://web.girona.cat/perfildelcontractant", "Ajuntament", "Girona"),
        ("Àrea Metropolitana de Barcelona", "https://www.amb.cat/es/web/amb/seu-electronica/perfil-de-contractant", "Consorci", "Barcelona"),
        ("Consorci d'Educació de Barcelona", "https://www.edubcn.cat/es/el_consorcio/gestion_economica/perfil_del_contratante", "Consorci", "Barcelona"),
    ]

    for nombre, url, tipo, prov in portales_genericos:
        licitaciones.extend(scrape_generico(nombre, url, tipo, prov))
        time.sleep(RATE_LIMIT_SECONDS)

    log.info(f"  TOTAL desde portales HTML: {len(licitaciones)} licitaciones")
    return licitaciones


# ═══════════════════════════════════════════════════════════════════════════════
# DEDUPLICACIÓN Y NORMALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def deduplicar(licitaciones):
    """Elimina duplicados basándose en organismo + objeto (primeros 100 chars)."""
    seen = set()
    result = []
    for lic in licitaciones:
        # Clave compuesta: organismo + primeros 100 chars del objeto
        key = (
            lic.get("Organismo", "").lower().strip(),
            lic.get("Objeto", "")[:100].lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            result.append(lic)
    log.info(f"Deduplicación: {len(licitaciones)} -> {len(result)} ({len(licitaciones) - len(result)} duplicados)")
    return result


def normalizar(licitaciones):
    """Normaliza los datos para la salida."""
    for lic in licitaciones:
        # Recalcular score si es 0
        if not lic.get("Valoracion") or lic["Valoracion"] == 0:
            dias = dias_restantes(lic.get("Fecha limite", ""))
            lic["Valoracion"] = calcular_score(
                lic.get("Importe", 0),
                lic.get("Norma afectada", ""),
                dias,
                lic.get("Tipo", ""),
                lic.get("Provincia", ""),
            )
        # Formatear importe
        try:
            lic["Importe"] = round(float(lic.get("Importe", 0)), 2)
        except (ValueError, TypeError):
            lic["Importe"] = 0
    return licitaciones


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL DE SCRAPING
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_todo(dias_atras=90, max_api=1000, solo_api=False):
    """
    Ejecuta el scraping completo de todas las fuentes.
    
    Args:
        dias_atras: Días hacia atrás para buscar en la API
        max_api: Máximo de resultados de la API
        solo_api: Si True, solo usa la API (más rápido)
    
    Returns:
        Lista de diccionarios con las licitaciones.
    """
    inicio = time.time()
    todas = []

    log.info("=" * 60)
    log.info("  SCRAPER DE LICITACIONES - CATALUÑA")
    log.info(f"  Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log.info(f"  Período: últimos {dias_atras} días")
    log.info("=" * 60)

    # 1. API Gencat PSCP (fuente principal, cubre casi todo)
    todas.extend(scrape_gencat_api(
        organos_filtro=ORGANOS_GENCAT,
        dias_atras=dias_atras,
        max_resultados=max_api,
    ))

    # 2. Scraping HTML de portales (complementario)
    if not solo_api:
        todas.extend(scrape_portales_html())

    # 3. Deduplicar y normalizar
    todas = deduplicar(todas)
    todas = normalizar(todas)

    # 4. Ordenar por score descendente
    todas.sort(key=lambda x: x.get("Valoracion", 0), reverse=True)

    elapsed = time.time() - inicio
    log.info("=" * 60)
    log.info(f"  COMPLETADO en {elapsed:.1f} segundos")
    log.info(f"  Total licitaciones: {len(todas)}")
    log.info("=" * 60)

    return todas


def guardar_csv(licitaciones, archivo=None):
    """Guarda las licitaciones en CSV."""
    if archivo is None:
        archivo = f"licitaciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    campos = [
        'Fecha publicacion', 'Fecha limite', 'Organismo', 'Tipo',
        'Provincia', 'Objeto', 'Area', 'Importe', 'Valoracion',
        'Norma afectada', 'URL'
    ]

    with open(archivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=';', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(licitaciones)

    log.info(f"CSV guardado: {archivo} ({len(licitaciones)} registros)")
    return archivo


def guardar_json(licitaciones, archivo="licitaciones.json"):
    """Guarda las licitaciones en JSON."""
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump(licitaciones, f, ensure_ascii=False, indent=2)
    log.info(f"JSON guardado: {archivo} ({len(licitaciones)} registros)")
    return archivo


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN DIRECTA
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de Licitaciones Cataluña")
    parser.add_argument("--server", action="store_true", help="Iniciar servidor Flask")
    parser.add_argument("--dias", type=int, default=90, help="Días hacia atrás (default: 90)")
    parser.add_argument("--max", type=int, default=1000, help="Máximo resultados API (default: 1000)")
    parser.add_argument("--solo-api", action="store_true", help="Solo usar API (más rápido)")
    parser.add_argument("--json", action="store_true", help="Guardar también como JSON")
    args = parser.parse_args()

    if args.server:
        # Importar y ejecutar servidor
        from servidor_licitaciones import app
        app.run(host='0.0.0.0', port=5050, debug=True)
    else:
        licitaciones = scrape_todo(
            dias_atras=args.dias,
            max_api=args.max,
            solo_api=args.solo_api,
        )
        guardar_csv(licitaciones)
        if args.json:
            guardar_json(licitaciones)

        # Resumen
        print(f"\n{'='*50}")
        print(f"RESUMEN:")
        print(f"  Total: {len(licitaciones)} licitaciones")
        tipos = {}
        for l in licitaciones:
            t = l.get('Tipo', 'N/A')
            tipos[t] = tipos.get(t, 0) + 1
        for t, c in sorted(tipos.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}")
        print(f"{'='*50}")
