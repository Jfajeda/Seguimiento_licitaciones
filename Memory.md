# Memory.md — Seguimiento_licitaciones
> Ultima actualizacion: 2026-04-28

## Estado actual

- **Fase**: Revisado, correcciones criticas aplicadas, documentacion v3 completada
- **Ultimo cambio significativo**: Filtrado de licitaciones caducadas en scraper (2026-04-28)
- **Tamano**: ~530 KB codigo fuente (3 ficheros), ~21 ficheros totales en 6 directorios
- **Lineas de codigo**: scraper 867 + servidor 311 + dashboard 887 = 2065 lineas

## Arquitectura

| Fichero | Rol | Lineas |
|---------|-----|--------|
| `scraper_licitaciones.py` | Scraper CLI: API Gencat (primaria) + HTML scraping (secundaria) | 867 |
| `servidor_licitaciones.py` | Servidor Flask en :5050, importa scraper, hilos background, cache disco | 311 |
| `Index02.html` | Dashboard SPA con Google Charts, PapaParse, CSV embebido de respaldo | 887 |

**Flujo de datos**: `scrape_todo()` → cache dict en servidor → `/api/licitaciones` JSON → dashboard renderiza.

**Fuente principal**: API abierta Gencat PSCP en `analisi.transparenciacatalunya.cat/resource/ybgg-dgi6.json` (consultas SoQL). Cubre todos los organismos publicos catalanes en JSON estructurado.

## Infraestructura

| Elemento | Estado | Detalle |
|----------|--------|---------|
| Git | Si | 1 commit (c4b2f16, 2026-04-12). Branch: main |
| GitHub | **No** | Pendiente de crear repo y subir |
| SonarCloud | **No** | Pendiente de conectar |
| .gitignore | Si | Creado 2026-04-26 (10 reglas) |
| AGENTS.md | Si | 83 lineas, instrucciones tecnicas compactas |
| Memory.md | Si | Este archivo |
| opencode.json | Si | Apunta a AGENTS.md |

## Estructura de ficheros

```
Seguimiento_licitaciones/
├── scraper_licitaciones.py          # Scraper (867 lineas)
├── servidor_licitaciones.py         # Servidor Flask (311 lineas)
├── Index02.html                     # Dashboard SPA (887 lineas)
├── datos.csv                        # CSV de respaldo para modo offline
├── cache_licitaciones.json          # Cache disco (auto-generado)
├── datos_actualizados.csv           # CSV del ultimo scraping (auto-generado)
├── AGENTS.md                        # Instrucciones para agentes IA
├── Memory.md                        # Este fichero
├── opencode.json                    # Config OpenCode
├── .gitignore                       # Exclusiones de git
├── Manuales/
│   ├── Manual.docx                  # Manual v1 (basico, marzo 2026)
│   ├── Manual_..._v2.docx           # Manual v2 (12 secciones, abril 2026)
│   └── Manual_..._v3.docx           # Manual v3 (16 secciones, abril 2026)
├── Documentacion/
│   ├── PIPELINE_LICITACIONES.md     # Flujo de datos del sistema
│   └── Directiva.docx               # Directiva de referencia
├── Prompt/
│   └── PROMPT_Desarrollo_...v1.docx # Doc ingenieria de prompts
├── Plantillas/
│   ├── plantilla_seguimiento_licitaciones.xlsx
│   └── seguimiento_licitaciones_ejemplo.xlsx
├── Datos_historicos/
│   ├── licitaciones.json
│   └── licitaciones_20260313_120256.csv
└── Biblioteca/
    └── Captura de pantalla ...png   # Screenshot de referencia
```

## Historial de decisiones

| Fecha | Decision | Razon |
|-------|----------|-------|
| 2026-03-13 | Proyecto creado con scraper + dashboard | Necesidad de monitorizar licitaciones catalanas |
| 2026-04-12 | Primer commit Git | Versionado local |
| 2026-04-26 | Proyecto movido de ~/Desktop/ a ~/Proyectos/ | iCloud sincroniza ~/Desktop/ causando conflictos |
| 2026-04-26 | Git inicializado con .gitignore | Centralizacion y versionado de todos los proyectos |
| 2026-04-27 | Revision de seguridad y calidad | Detectados 12 hallazgos de seguridad + 15 de calidad |
| 2026-04-28 | Manual v3 creado | Incorporar bugfixes, notas tecnicas, historial, seccion Git |

## Revisiones de calidad/seguridad

| Fecha | Tipo | Resultado |
|-------|------|-----------|
| 2026-04-27 | Revision manual (OpenCode) | 3 criticos + 4 altos + 5 medios (seguridad), 4 altos + 6 medios + 5 bajos (calidad) |

### Correcciones aplicadas (2026-04-27)
1. servidor_licitaciones.py: host cambiado de 0.0.0.0 a 127.0.0.1 (CRITICO)
2. scraper_licitaciones.py: host cambiado de 0.0.0.0 a 127.0.0.1 + debug=True a False (CRITICO+MEDIO)

### Correcciones aplicadas anteriormente (sesiones previas)
3. Race condition en cache_lock (ALTA) — todas las lecturas/escrituras del dict cache protegidas
4. fecha_corte con timedelta en vez de resta manual (ALTA)
5. Deteccion ENS con regex \bENS\b para evitar falsos positivos (ALTA)
6. Endpoint /api/estadisticas protegido por cache_lock (MEDIA)
7. normalizar() recalcula score cuando Valoracion es 0/vacio (MEDIA)
8. try/catch en polling de estado del dashboard (MEDIA)
9. /api/fuentes devuelve fuentes dinamicamente desde modulo scraper (MEDIA)
10. Docstring mejorada del modulo scraper (BAJA)
11. Comentarios de seccion en servidor (BAJA)
12. Formato de logging unificado (BAJA)
13. Manejo de importes con formato europeo (BAJA)
14. Validacion de respuesta HTTP antes de procesar JSON de API (BAJA)

### Correcciones aplicadas (2026-04-28)
15. Filtrado de licitaciones caducadas: filtro SoQL en API Gencat (data_limit_presentacio >= hoy) + filtro post-procesado en scrape_todo() que descarta licitaciones con fecha limite pasada (ALTA)

### Hallazgos pendientes de corregir
- **CRITICO**: Path traversal en ruta catch-all `/<path:filename>` (sirve cualquier archivo del directorio)
- **ALTO**: CORS abierto sin restricciones, XSS en innerHTML de Index02.html, SSRF en scraper, sin validacion de parametros POST
- **CALIDAD**: Logica de scoring duplicada Python/JS (actualmente sincronizadas, pero manual)

## Documentacion generada

| Documento | Version | Fecha | Secciones |
|-----------|---------|-------|-----------|
| Manual.docx | v1 | Mar 2026 | Basico |
| Manual_Usuario_Radar_Licitaciones_v2.docx | v2 | Abr 2026 | 12 secciones |
| Manual_Usuario_Radar_Licitaciones_v3.docx | v3 | 28 Abr 2026 | 16 secciones (+Novedades v3, Notas tecnicas, Git, Historial) |
| PROMPT_Desarrollo_...v1.docx | v1 | Abr 2026 | 14 secciones (ingenieria de prompts) |
| PIPELINE_LICITACIONES.md | v1 | Abr 2026 | 5 capas + historial decisiones |

## Pendiente

- [x] ~~Revision de calidad y seguridad del codigo~~ (completada 2026-04-27)
- [x] ~~Servidor cambiado a 127.0.0.1~~ (aplicado 2026-04-27)
- [x] ~~debug=True eliminado~~ (aplicado 2026-04-27)
- [x] ~~Manual v3 con cambios incorporados~~ (creado 2026-04-28)
- [ ] Restringir ruta catch-all a whitelist de archivos permitidos
- [ ] Sanitizar innerHTML en Index02.html (crear escapeHtml)
- [ ] Restringir CORS a localhost
- [ ] Validar parametros POST (dias, max)
- [ ] Unificar logica de scoring Python/JS (actualmente sincronizada pero duplicada)
- [ ] Crear repo en GitHub y subir
- [ ] Conectar a SonarCloud
- [ ] Integrar DIBA open data API como fuente adicional
- [ ] Soporte Playwright para portales JavaScript-heavy
- [ ] Scraping programado (cron)
- [ ] Alertas por email para licitaciones de score alto
- [ ] Exportar a Excel
- [ ] Paginacion para resultados grandes

## Notas y descubrimientos

- API Gencat PSCP es la fuente primaria: 82+ licitaciones en ~6 segundos. Cubre todos los organismos catalanes.
- La mayoria de portales individuales son SPAs JavaScript — requests+BS4 no funciona, pero la API Gencat los cubre.
- Deteccion de provincia via codigos NUTS: ES511=BCN, ES512=GI, ES513=LL, ES514=TGN.
- Scoring duplicado Python/JS: calcular_score (scraper:274) y calcularScore (Index02:551). Mantener sincronizados.
- CSV usa punto y coma (;) como delimitador. Claves sin tildes.
- Deduplicacion por (organismo.lower(), objeto[:100].lower()).
- FUENTES dict es catalogo informativo, no se itera para scraping. Objetivos reales: ORGANOS_GENCAT + funciones HTML hardcoded.
- Puerto 5050 elegido para evitar conflicto con AirPlay en macOS (puerto 5000).
- Hubo un problema al abrir OpenCode en este proyecto tras mover la carpeta (error "Fallo al listar archivos"). Se resuelve cerrando y reabriendo OpenCode desde la nueva ubicacion.
- Git status actual: 2 ficheros modificados (scraper, servidor) + 7 untracked (AGENTS.md, Memory.md, opencode.json, manual v2/v3, Prompt/, Biblioteca/). Nada staged.
