# Pipeline de Captura de Licitaciones - Cataluña

## Arquitectura por Capas

### Capa 1: Captura (Fuentes Oficiales)
| Fuente | URL | Frecuencia | Tipo |
|--------|-----|------------|------|
| Portal Barcelona | https://licitacions.bcn.cat | Diaria | API/Web |
| Contractació Generalitat | https://contractacio.gencat.cat | Diaria | RSS/API |
| Plataforma Estatal | https://contrataciondelestado.es | Diaria | CSV |
| Consorci AOC | https://consorci-aoc.cat | Semanal | Web |

### Capa 2: Limpieza
- Deduplicación por URL/expediente
- Normalización de fechas (DD/MM/AAAA)
- Estandarización de nombres de organismos
- Conversión de importes a euros

### Capa 3: Clasificación
- Área: automática por palabras clave en objeto
- Tipo organismo: mapeo manual de organismos conocidos
- Provincia: extracción de locality/NUTS
- Norma afectada: búsqueda de keywords (ISO, ENS, NIS2...)

### Capa 4: Scoring (Rúbrica)
| Criterio | Ponderación | Fórmula |
|----------|--------------|---------|
| Importe | 30% | log(importe) normalizado 0-10 |
| Norma | 25% | ISO27001/ENS/NIS2=10, ISO9001=7, ISO14001=5, otras=3 |
| Urgencia | 20% | 10-(días_hasta_fin*0.5) min=0 |
| Tipo organismo | 15% | Generalitat=10, Hospital=9, Universidad=7, Ayunt=6, Otros=5 |
| Provincia | 10% | Barcelona=10, otras=8 |

### Capa 5: Alertas
- **Urgente**: < 7 días → Email + Teams
- **Alta prioridad**: Score ≥ 8 → Email diario
- **Resumen semanal**: Todas las nuevas → Email semanal

---

## Historial de Decisiones

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-02-16 | Scoring manual inicial | Simplificar, permitir ajuste fino |
| 2026-02-16 | Deduplicación por URL | Evitar licitaciones duplicadas |
| 2026-02-16 | Vigencia 30 días post-límite | Mantener histórico pero marcarcaducadas |
| 2026-02-16 | Filtro por normativa | Requisito específico del usuario |
| 2026-02-16 | Rúbrica visual | Transparenciay reproductibilidad |

---

## Próximas Iteraciones

### Iteración 3: Automatización
- [ ] Script Python de captura periódica
- [ ] Integración con Google Sheets API
- [ ] Notificaciones automáticas

### Iteración 4: Enriquecimiento
- [ ] Datos de contacto del organismo
- [ ] Historial de adjudicatarios
- [ ] Predicción de probabilidad dewin

### Iteración 5: Producto
- [ ] Interfaz multi-usuario
- [ ] Export a PDF/Excel
- [ ] Dashboard ejecutivo
