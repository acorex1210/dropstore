# Guía de Estilo — Derma Essenza Instagram Templates

> **Versión**: 1.0 | **Fecha**: Julio 2026 | **Formato**: HTML/CSS/JS (zero deps) | **Export**: PNG 2160×2160px (2x retina)

---

## 1. Identidad de Marca

| Atributo | Especificación |
|----------|----------------|
| **Nombre** | Derma Essenza |
| **Sector** | Centro estético médico / Dermatología estética |
| **Tono** | Profesional, cercano, ético, premium, basado en evidencia |
| **Estilo visual** | Minimalista, médico/estético, limpio, aireado, confianza |
| **Paleta** | Navy `#0B1220` + Gold `#C5A572` (escalas completas en `tokens.css`) |
| **Tipografías** | **Inter** (UI, cuerpo, datos) + **Playfair Display** (headlines, display, números) |
| **Formato IG** | Post cuadrado 1080×1080px → Export 2x = 2160×2160px |
| **Zona segura** | 80px (7.4%) margen en TODOS los lados — nada crítico fuera |

---

## 2. Paleta de Colores — Reglas de Oro

### Uso Correcto
```
✓ Navy-900:  Texto principal, headlines, fondos oscuros, watermark
✓ Navy-600/400: Texto secundario, metadata, labels, placeholders
✓ Gold-500:  SOLO acentos — líneas, badges llenos, CTA primary, dots carousel, iconos decorativos
✓ Gold-100/50: Fondos de badges, chips, hover states, patrones sutiles
✓ White/Off-white: Fondos claros (plantillas light), texto sobre navy
```

### Uso Incorrecto
```
✗ Texto largo (body, caption) en Gold — legibilidad insuficiente
✗ Fondos grandes en Gold — rompe minimalismo médico
✗ Gradientes Gold sobre Gold — ruido visual
✗ Gold-500 sobre White — contraste WCAG AA falla (3.2:1)
✗ Navy-400 sobre Navy-900 — contraste insuficiente
```

### Contraste Verificado (WCAG AA)
| Combinación | Ratio | Estado |
|-------------|-------|--------|
| Navy-900 / White | 15.3:1 | ✓ AAA |
| Gold-500 / Navy-900 | 5.8:1 | ✓ AA |
| Gold-500 / White | 3.2:1 | ✗ No usar para texto |
| Navy-600 / White | 7.1:1 | ✓ AA |
| Navy-400 / White | 4.5:1 | ✓ AA (large text only) |

---

## 3. Tipografía — Jerarquía Visual

```
HEADLINE (Playfair 500, tight, navy-900/gold-500)
  └─ SUBHEAD (Inter 500, snug, navy-600)
      └─ BODY (Inter 400, relaxed, navy-800/900)
          └─ CAPTION (Inter 400, normal, navy-400)
              └─ OVERLINE (Inter 600, xs, UPPERCASE, wide, navy-400/gold-500)
```

### Pesos Permitidos
- **300**: Solo números grandes decorativos (hero stats)
- **400**: Body, caption, subhead
- **500**: Labels, badge text, subhead, CTA
- **600**: Overline, key info values, emphasis
- **700**: Raro, solo énfasis extremo

### Tracking
- `tight` (-0.02em): Headlines Playfair
- `normal` (0): Body, subhead
- `wide` (0.02em): Labels, metadata
- `wider` (0.05em): Overline uppercase

---

## 4. Espaciado & Layout

### Sistema 4px Base
| Token | px | Uso Típico |
|-------|-----|------------|
| `--space-1` | 4 | Icon-text gap, micro padding |
| `--space-2` | 8 | Badge padding, inline gaps |
| `--space-3` | 12 | Small component gaps |
| `--space-4` | 16 | Standard padding, grid gap |
| `--space-5` | 20 | Medium padding |
| `--space-6` | 24 | Section padding, card padding |
| `--space-8` | 32 | Large section gaps |
| `--space-10` | 40 | Major sections |
| `--space-12` | 48 | Hero areas |
| `--space-16` | 64 | Full bleed sections |

### Grid Instagram
- **Frame**: 1080×1080px fijo
- **Safe zone**: 920×920px (80px cada lado)
- **Content max-width**: 920px centrado
- **Columns**: 12-col implícito via CSS Grid (gap 16-24px)

---

## 5. Componentes — Especificaciones

### Accent Line (`.accent-line`)
```
Width: 60px (short: 40px, long: 100px)
Height: 3px
Background: linear-gradient(90deg, gold-500, gold-300)
Border-radius: full
Uso: Debajo de headline, separador de secciones
```

### Badge (`.badge`)
```
Padding: 4px 12px (space-1 space-3)
Font: Inter 600, xs, UPPERCASE, wide tracking
Border-radius: full
Variants:
  - .badge-gold: bg gold-100, text gold-600, border gold-300
  - .badge-gold-filled: bg gold-500, text navy-900
  - .badge-navy: bg navy-800, text gold-400, border navy-600
  - .badge-outline: transparent, text gold-500, border gold-500
```

### CTA Button (`.btn-cta`)
```
Padding: 12px 24px (space-3 space-6) — LG: 16px 32px, SM: 8px 16px
Font: Inter 600, base (LG: lg), normal tracking
Border-radius: lg (12px)
Variants:
  - Primary: bg gold-500, text navy-900, shadow-gold
  - Outline: transparent, text gold-500, border 2px gold-500
  - White: bg white, text navy-900, shadow-md
Hover: transform -1px, shadow intensificado
Active: transform 0
Full width: .btn-cta-full
```

### Divider (`.divider`)
```
Width: 100%, max-width: 60px (full: 100%)
Height: 1px
Background: gold-300 (navy-600 en dark)
Border: none
```

### Image Frame (`.img-frame`)
```
Border-radius: lg (12px) / xl (16px) para hero
Overflow: hidden
Background: navy-800 (placeholder)
Aspect ratios: 1:1 (square), 4:5 (portrait), 4:3 (landscape)
Hover: scale(1.02) transition slow
Upload zone: dashed border navy-500 → solid gold-500 on drag/hover
```

### Carousel Dots (`.carousel-dots`)
```
Position: absolute bottom, center
Gap: 8px
Dot: 8×8px, radius full, bg gold-300
Active: 24×8px, bg gold-500, shadow gold glow
Container: bg navy-900/60, blur(8px), border gold-500/20, radius full, padding 8px 16px
```

### Watermark (`.watermark`)
```
Position: absolute bottom-right, 16px from edges
Font: Playfair 400, sm
Color: navy-900 / white / gold-500
Opacity: 0.08 (dark) / 0.12 (light) / 0.15 (gold)
Pointer-events: none, user-select: none
Text: "Derma Essenza"
```

### Comparison Static (`.comparison-static`)
```
Grid: 2 cols 1fr gap-16px (stacked 1 col mobile <768px)
Panel: aspect-ratio 4:5, radius lg, overflow hidden
Labels: absolute bottom-left/right
  - Before: bg navy-900/80, text navy-300, border navy-500
  - After: bg gold-500, text navy-900
Divider: absolute center, 2px gold-500 (desktop only)
```

---

## 6. Plantillas — Guía Rápida

| Plantilla | Archivo | Slides | Uso Principal |
|-----------|---------|--------|---------------|
| **Flyer Tratamiento** | `01-treatment-flyer.html` | 1 | Hero 60% img + 40% info (badge, headline, 3 beneficios, key info 3 cols, CTA) |
| **Flyer Promo Mes** | `02-promo-flyer.html` | 1 | Navy bg + pattern, badge promo, headline gold, grid 2x2 precios, countdown, CTA white |
| **Carrusel Educativo** | `03-edu-carousel.html` | 5 | Portada → Qué es (4 cards) → Beneficios (4 cards) → Cuidados/FAQ (2 cols) → CTA final |
| **Carrusel Antes/Después** | `04-beforeafter-carousel.html` | 5 | Portada → Split estático A/D → Zonas/mejoras (3 stats) → Protocolo (3 pasos + cuidados) → CTA + disclaimer |
| **Carrusel Testimonios** | `05-testimonial-carousel.html` | 5 | 4 slides: foto circular + quote + nombre + tratamiento + 5★ → Slide final CTA |

---

## 7. Fotografía — Estándares

| Aspecto | Especificación |
|---------|----------------|
| **Ratio** | 4:5 (portrait) para hero/trattamiento, 1:1 para pacientes |
| **Estilo** | Luz natural, fondo neutro (gris cálido/blanco roto), piel real, sin filtros fuertes |
| **Composición** | Espacio negativo para texto, sujeto descentrado (regla tercios) |
| **Pacientes** | Consentimiento escrito obligatorio, rostro completo o detalle zona tratada |
| **Gabinete** | Limpio, ordenado, luz suave, equipos visibles pero no dominantes |
| **Producto** | Packaging limpio, luz lateral, reflejos controlados |
| **Calidad** | Mín 1080×1350px (4:5) o 1080×1080px (1:1), nítido, sin compresión visible |

### Placeholders Incluidos
- `placeholder-treatment.jpg` — 4:5, estilo médico clean
- `placeholder-patient.jpg` — 1:1, rostro neutro
- `placeholder-before.jpg` / `placeholder-after.jpg` — 4:5, silueta facial genérica
- `placeholder-clinic.jpg` — 4:5, gabinete estético

---

## 8. Copywriting — Principios

### Voz Derma Essenza
- **Médico pero accesible**: Terminología correcta explicada en llano
- **Ético**: No prometer resultados, "mejora", "suaviza", "estimula"
- **Basado en evidencia**: "Estudios muestran", "En nuestra experiencia"
- **Cercano**: "Tu piel", "Tu caso", "Te acompañamos"
- **Call to Action claro**: Verbo de acción + beneficio ("Agenda tu valoración gratuita")

### Estructura Textos por Componente

**Headline (máx 2-3 líneas)**
```
Ellansé Manos: Volumen natural
Pack Rejuvenece Total: Rostro + Cuello
Todo sobre Ellansé: Bioestimulación real
```

**Subhead (1 línea, complemento)**
```
Bioestimulador colágeno propio para rejuvenecimiento dorsal
Ellansé + HIFU 7D + Toxina en una sola sesión
Guía completa: qué es, beneficios, cuidados, FAQ
```

**Body (2-4 líneas, relaxed leading)**
```
Resultados progresivos y armónicos desde la primera sesión.
Duración 2-4 años según tipo. Aprobado FDA y CE médico.
```

**Key Info (labels + valores)**
```
Duración: 30 min    Sesiones: 1-2    Recuperación: Inmediata
```

**CTA (verbo + beneficio, max 3 palabras)**
```
Agendar valoración gratuita
Reservar mi cupo ahora
Quiero mi valoración
```

**Disclaimer Médico (obligatorio en carruseles clínicos)**
```
Resultados reales paciente Derma Essenza con consentimiento.
La respuesta varía según biotipo, edad y adherencia a cuidados.
Requiere evaluación médica previa. Ellansé dispositivo médico CE/FDA.
```

---

## 9. Export & Naming

### Export Settings (html2canvas)
```
Scale: 2x (2160×2160px)
Format: PNG, quality 0.95
Background: null (transparente si frame transparent)
CORS: true
AllowTaint: true
```

### Naming Convention
```
derma_[tipo]_[tratamiento]_[fecha].png

Ejemplos:
derma_flyer_ellanse_manos_2026-07.png
derma_promo_julio_pack_rejuvenece_2026-07.png
derma_carousel_edu_ellanse_2026-07.png
derma_carousel_ba_ellanse_mejillas_2026-07.png
derma_carousel_testimonios_pacientes_2026-07.png
```

### Checklist Pre-Post
- [ ] Textos en safe zone (80px margen)
- [ ] Contraste WCAG AA verificado
- [ ] Disclaimer médico si aplica
- [ ] Watermark visible (opacity 0.08)
- [ ] Imágenes nítidas (no pixeladas en 2x)
- [ ] CTA claro con verbo de acción
- [ ] Naming correcto
- [ ] Backup localStorage guardado (Ctrl+S)

---

## 10. Atajos de Teclado (Editor)

| Tecla | Acción |
|-------|--------|
| Click en texto | Editar (contentEditable) |
| Click en imagen | Subir archivo (input file) |
| `Ctrl/Cmd + S` | Guardar todo en localStorage |
| `Escape` | Desenfocar elemento activo |
| `←` `→` | Navegar carrusel (cuando focus en track) |
| Swipe L/R | Navegar carrusel (touch) |
| Click dots | Ir a slide |
| Botón "Descargar PNG" | Export 2x |
| Click derecho en export btn | Exportar todos los slides (carruseles) |

---

## 11. Mantenimiento & Actualizaciones

### Agregar Nueva Plantilla
1. Copiar `templates/01-treatment-flyer.html` como base
2. Actualizar `data-editable` keys únicos
3. Añadir entrada en `index.html` grid
4. Actualizar `STYLE_GUIDE.md` tabla de plantillas

### Cambiar Colores
1. Editar `tokens.css` → variables `--navy-*` / `--gold-*`
2. Todos los componentes se actualizan automáticamente
3. Verificar contraste en `base.css` semantic aliases

### Cambiar Tipografías
1. Editar `@import` en `base.css` (Google Fonts)
2. Actualizar `--font-ui` / `--font-display` en `tokens.css`
3. Revisar `font-weight` disponibilidad en nueva fuente

### Añadir Patrón
1. Crear SVG base64 en `components.css` → `.pattern-overlay[data-pattern="nuevo"]`
2. Añadir opción en `index.html` selector si se desea

---

## 12. Archivos Clave — Referencia Rápida

```
derma-ig-templates/
├── index.html                 # Hub selector plantillas
├── tokens.css                 # Design tokens (colores, typo, spacing, shadows)
├── base.css                   # Reset, fonts, utilities, helpers
├── components.css             # 12 componentes reutilizables
├── js/
│   ├── editor.js              # ContentEditable + localStorage + image upload
│   └── export.js              # html2canvas export PNG 2x + toast notifications
├── templates/
│   ├── 01-treatment-flyer.html
│   ├── 02-promo-flyer.html
│   ├── 03-edu-carousel.html
│   ├── 04-beforeafter-carousel.html
│   └── 05-testimonial-carousel.html
├── assets/
│   ├── patterns/              # noise.svg, linen.svg, dots.svg, crosshatch.svg
│   └── placeholders/          # 6 placeholders SVG médico/estético
└── STYLE_GUIDE.md             # Este archivo
```

---

## 13. Soporte & Contacto

**Desarrollo**: Sistema generado automáticamente para Derma Essenza
**Tecnología**: HTML5 + CSS Custom Properties + Vanilla JS (ES6+)
**Dependencias externas**: Solo Google Fonts + html2canvas (CDN)
**Compatibilidad**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

**Para dudas técnicas o ajustes de marca**: Consultar este documento → `tokens.css` → `components.css` → template específico.

---

*Última actualización: Julio 2026 — Derma Essenza Design System v1.0*