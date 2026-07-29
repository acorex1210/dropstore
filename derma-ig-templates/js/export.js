/**
 * Derma Essenza — Export Module
 * PNG export via html2canvas, filename generation
 */

const DermaExport = (() => {
  let html2canvasLoaded = false;
  let loadPromise = null;

  // ===== LOAD HTML2CANVAS =====
  function loadHtml2Canvas() {
    if (html2canvasLoaded) return Promise.resolve();
    if (loadPromise) return loadPromise;

    loadPromise = new Promise((resolve, reject) => {
      if (window.html2canvas) {
        html2canvasLoaded = true;
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
      script.onload = () => {
        html2canvasLoaded = true;
        resolve();
      };
      script.onerror = () => reject(new Error('Failed to load html2canvas'));
      document.head.appendChild(script);
    });

    return loadPromise;
  }

  // ===== GENERATE FILENAME =====
  function generateFilename(templateName, customName = '') {
    const date = new Date();
    const dateStr = date.toISOString().slice(0, 10).replace(/-/g, '');
    const timeStr = date.toTimeString().slice(0, 5).replace(':', '');
    const parts = ['derma', templateName];
    if (customName) parts.push(customName);
    parts.push(dateStr, timeStr);
    return parts.join('_') + '.png';
  }

  // ===== EXPORT PNG =====
  async function exportPNG(options = {}) {
    const {
      selector = '.ig-frame',
      filename = null,
      templateName = getTemplateName(),
      scale = 2,
      backgroundColor = null,
      onProgress = null,
      onComplete = null,
      onError = null
    } = options;

    const frame = document.querySelector(selector);
    if (!frame) {
      const err = new Error(`Element not found: ${selector}`);
      onError?.(err);
      throw err;
    }

    // Show loading
    showExportToast('Preparando exportación...', 'loading');

    try {
      await loadHtml2Canvas();

      // Hide export button during capture
      const exportBtn = document.querySelector('.export-btn');
      const exportBtnVisible = exportBtn?.style.display !== 'none';
      if (exportBtn) exportBtn.style.display = 'none';

      // Hide any editing indicators
      const editingEls = frame.querySelectorAll('.editing, [data-editable]:focus');
      editingEls.forEach(el => el.blur());

      const canvas = await window.html2canvas(frame, {
        scale,
        useCORS: true,
        allowTaint: true,
        backgroundColor,
        logging: false,
        imageTimeout: 15000,
        onclone: clonedDoc => {
          // Remove editor-only elements from clone
          clonedDoc.querySelectorAll('.img-upload-hint, .img-upload-zone::before, .export-btn, .carousel-nav, .carousel-dots').forEach(el => el.remove());
          // Ensure watermarks are visible
          clonedDoc.querySelectorAll('.watermark').forEach(w => {
            w.style.opacity = '0.08';
            w.style.display = 'block';
          });
        }
      });

      // Restore export button
      if (exportBtn && exportBtnVisible) exportBtn.style.display = '';

      const finalFilename = filename || generateFilename(templateName);

      // Download
      canvas.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = finalFilename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showExportToast(`Guardado: ${finalFilename}`, 'success');
        onComplete?.(finalFilename);
      }, 'image/png', 0.95);

    } catch (err) {
      console.error('[DermaExport] Export failed:', err);
      showExportToast('Error al exportar: ' + err.message, 'error');
      onError?.(err);
    }
  }

  // ===== EXPORT ALL SLIDES (CAROUSEL) =====
  async function exportCarouselSlides(options = {}) {
    const {
      selector = '.ig-frame',
      slideSelector = '.carousel-slide',
      templateName = getTemplateName(),
      scale = 2
    } = options;

    const frame = document.querySelector(selector);
    if (!frame) throw new Error(`Frame not found: ${selector}`);

    const slides = frame.querySelectorAll(slideSelector);
    if (slides.length === 0) throw new Error('No slides found');

    await loadHtml2Canvas();

    showExportToast(`Exportando ${slides.length} slides...`, 'loading');

    const originalTransform = frame.querySelector('.carousel-track')?.style.transform;
    const track = frame.querySelector('.carousel-track');

    for (let i = 0; i < slides.length; i++) {
      // Navigate to slide
      if (track) {
        track.style.transform = `translateX(-${i * 100}%)`;
        // Wait for transition
        await new Promise(r => setTimeout(r, 300));
      }

      const filename = generateFilename(`${templateName}_slide${i + 1}`);
      const canvas = await window.html2canvas(frame, {
        scale,
        useCORS: true,
        allowTaint: true,
        backgroundColor: null,
        logging: false
      });

      canvas.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }, 'image/png', 0.95);

      showExportToast(`Slide ${i + 1}/${slides.length} listo`, 'info');
    }

    // Restore
    if (track && originalTransform !== undefined) {
      track.style.transform = originalTransform;
    }

    showExportToast(`${slides.length} slides exportados`, 'success');
  }

  // ===== GET TEMPLATE NAME =====
  function getTemplateName() {
    const path = window.location.pathname;
    const match = path.match(/\/([^/]+)\.html$/);
    return match ? match[1].replace(/^\d+-/, '') : 'template';
  }

  // ===== TOAST =====
  function showExportToast(message, type = 'info') {
    let toast = document.getElementById('derma-export-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'derma-export-toast';
      toast.style.cssText = `
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px);
        padding: 14px 28px; border-radius: var(--radius-full);
        font-family: var(--font-ui); font-size: var(--text-sm);
        font-weight: 500; z-index: var(--z-toast); opacity: 0;
        transition: all var(--transition-base);
        box-shadow: var(--shadow-xl);
        display: flex; align-items: center; gap: 8px;
      `;
      document.body.appendChild(toast);
    }

    const colors = {
      loading: { bg: 'var(--navy-900)', color: 'var(--gold-500)', icon: '⏳' },
      success: { bg: 'var(--navy-900)', color: 'var(--gold-500)', icon: '✓' },
      error: { bg: 'var(--navy-900)', color: '#e04848', icon: '✕' },
      info: { bg: 'var(--navy-900)', color: 'var(--gold-400)', icon: 'ℹ' }
    };

    const c = colors[type] || colors.info;
    toast.style.background = c.bg;
    toast.style.color = c.color;
    toast.innerHTML = `<span>${c.icon}</span><span>${message}</span>`;

    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';

    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(-50%) translateY(20px)';
    }, type === 'loading' ? 10000 : 3000);
  }

  // ===== CREATE EXPORT BUTTON =====
  function createExportButton(options = {}) {
    const {
      selector = '.ig-frame',
      templateName = getTemplateName(),
      text = 'Descargar PNG',
      ariaLabel = 'Exportar como PNG'
    } = options;

    const btn = document.createElement('button');
    btn.className = 'btn-cta btn-cta-primary export-btn';
    btn.setAttribute('aria-label', ariaLabel);
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-cta-icon">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      <span>${text}</span>
    `;

    btn.addEventListener('click', () => exportPNG({ selector, templateName }));

    // Also support right-click -> "Export all slides" for carousels
    btn.addEventListener('contextmenu', e => {
      e.preventDefault();
      const frame = document.querySelector(selector);
      if (frame?.querySelector('.carousel-track')) {
        exportCarouselSlides({ selector, templateName });
      }
    });

    document.body.appendChild(btn);
    return btn;
  }

  // ===== PUBLIC API =====
  return {
    exportPNG,
    exportCarouselSlides,
    createExportButton,
    generateFilename,
    loadHtml2Canvas
  };
})();

// Auto-create export button on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Small delay to ensure frame is rendered
  setTimeout(() => DermaExport.createExportButton(), 100);
});

// Export for module systems
if (typeof module !== 'undefined') module.exports = DermaExport;