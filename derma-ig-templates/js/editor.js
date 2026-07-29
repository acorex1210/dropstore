/**
 * Derma Essenza — Editor Module
 * ContentEditable handling, localStorage persistence, image upload
 */

const DermaEditor = (() => {
  const STORAGE_PREFIX = 'derma_ig_';
  const EDITABLE_SELECTOR = '[data-editable]';
  const IMAGE_SELECTOR = '[data-image]';
  const DEBOUNCE_MS = 300;

  let debounceTimers = new Map();
  let currentTemplate = '';

  // ===== INIT =====
  function init(templateName) {
    currentTemplate = templateName || getTemplateName();
    restoreContent();
    bindEditable();
    bindImages();
    bindKeyboardShortcuts();
    console.log(`[DermaEditor] Initialized: ${currentTemplate}`);
  }

  function getTemplateName() {
    const path = window.location.pathname;
    const match = path.match(/\/([^/]+)\.html$/);
    return match ? match[1] : 'unknown';
  }

  // ===== LOCALSTORAGE =====
  function getStorageKey(suffix = 'content') {
    return `${STORAGE_PREFIX}${currentTemplate}_${suffix}`;
  }

  function saveContent() {
    const data = {};
    document.querySelectorAll(EDITABLE_SELECTOR).forEach(el => {
      const key = el.dataset.editable || el.id || generateKey(el);
      data[key] = el.innerHTML;
    });
    localStorage.setItem(getStorageKey(), JSON.stringify(data));
  }

  function saveImages() {
    const data = {};
    document.querySelectorAll(IMAGE_SELECTOR).forEach(el => {
      const key = el.dataset.image || el.id || generateKey(el);
      if (el.src && !el.src.startsWith('data:') && !el.src.includes('placeholder')) {
        data[key] = el.src;
      }
    });
    localStorage.setItem(getStorageKey('images'), JSON.stringify(data));
  }

  function restoreContent() {
    try {
      const content = JSON.parse(localStorage.getItem(getStorageKey()) || '{}');
      const images = JSON.parse(localStorage.getItem(getStorageKey('images')) || '{}');

      Object.entries(content).forEach(([key, html]) => {
        const el = document.querySelector(`[data-editable="${key}"]`) ||
                   document.getElementById(key);
        if (el) el.innerHTML = html;
      });

      Object.entries(images).forEach(([key, src]) => {
        const el = document.querySelector(`[data-image="${key}"]`) ||
                   document.getElementById(key);
        if (el && src) el.src = src;
      });
    } catch (e) {
      console.warn('[DermaEditor] Restore failed:', e);
    }
  }

  function clearStorage() {
    localStorage.removeItem(getStorageKey());
    localStorage.removeItem(getStorageKey('images'));
  }

  // ===== EDITABLE BINDING =====
  function bindEditable() {
    document.querySelectorAll(EDITABLE_SELECTOR).forEach(el => {
      // Ensure editable
      if (!el.hasAttribute('contenteditable')) {
        el.setAttribute('contenteditable', 'true');
      }

      // Placeholder
      if (el.dataset.placeholder && !el.textContent.trim()) {
        el.textContent = '';
      }

      // Input handler with debounce
      el.addEventListener('input', debounceSave(el));

      // Paste as plain text
      el.addEventListener('paste', e => {
        e.preventDefault();
        const text = e.clipboardData.getData('text/plain');
        document.execCommand('insertText', false, text);
      });

      // Prevent new block elements on Enter (shift+enter for new line)
      el.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          if (el.tagName === 'H1' || el.tagName === 'H2' || el.tagName === 'H3' ||
              el.tagName === 'H4' || el.tagName === 'P') {
            e.preventDefault();
            document.execCommand('insertLineBreak');
          }
        }
      });

      // Visual feedback
      el.addEventListener('focus', () => el.classList.add('editing'));
      el.addEventListener('blur', () => el.classList.remove('editing'));
    });
  }

  function debounceSave(el) {
    return () => {
      const key = el.dataset.editable || el.id || generateKey(el);
      clearTimeout(debounceTimers.get(key));
      debounceTimers.set(key, setTimeout(() => saveContent(), DEBOUNCE_MS));
    };
  }

  // ===== IMAGE UPLOAD =====
  function bindImages() {
    document.querySelectorAll(IMAGE_SELECTOR).forEach(img => {
      const wrapper = img.closest('.img-upload-zone') || createUploadZone(img);
      setupDragDrop(wrapper, img);
      setupClickUpload(wrapper, img);
    });
  }

  function createUploadZone(img) {
    const zone = document.createElement('div');
    zone.className = 'img-upload-zone';
    zone.style.width = img.style.width || '100%';
    zone.style.height = img.style.height || '100%';
    zone.style.minWidth = img.width || '200px';
    zone.style.minHeight = img.height || '200px';

    img.parentNode.insertBefore(zone, img);
    zone.appendChild(img);
    return zone;
  }

  function setupDragDrop(zone, img) {
    ['dragenter', 'dragover'].forEach(evt =>
      zone.addEventListener(evt, e => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.add('drag-over');
      })
    );

    ['dragleave', 'drop'].forEach(evt =>
      zone.addEventListener(evt, e => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove('drag-over');
      })
    );

    zone.addEventListener('drop', e => {
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        loadImageFile(file, img);
      }
    });
  }

  function setupClickUpload(zone, img) {
    zone.addEventListener('click', e => {
      if (e.target === zone || e.target.classList.contains('img-upload-hint')) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = () => input.files[0] && loadImageFile(input.files[0], img);
        input.click();
      }
    });
  }

  function loadImageFile(file, img) {
    const reader = new FileReader();
    reader.onload = e => {
      img.src = e.target.result;
      img.removeAttribute('data-placeholder');
      saveImages();
    };
    reader.readAsDataURL(file);
  }

  // ===== KEYBOARD SHORTCUTS =====
  function bindKeyboardShortcuts() {
    document.addEventListener('keydown', e => {
      // Ctrl/Cmd + S = Save (prevent default, trigger save)
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveContent();
        saveImages();
        showToast('Cambios guardados');
      }
      // Escape = blur active editable
      if (e.key === 'Escape') {
        document.activeElement.blur();
      }
    });
  }

  // ===== UTILITIES =====
  function generateKey(el) {
    const tag = el.tagName.toLowerCase();
    const cls = el.className.split(' ')[0] || '';
    return `${tag}_${cls}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function showToast(message) {
    let toast = document.getElementById('derma-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'derma-toast';
      toast.style.cssText = `
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
        background: var(--navy-900); color: var(--gold-500);
        padding: 12px 24px; border-radius: var(--radius-full);
        font-family: var(--font-ui); font-size: var(--text-sm);
        font-weight: 500; z-index: var(--z-toast); opacity: 0;
        transition: opacity var(--transition-base), transform var(--transition-base);
        box-shadow: var(--shadow-lg);
      `;
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(-50%) translateY(10px)';
    }, 2000);
  }

  // ===== PUBLIC API =====
  return {
    init,
    saveContent,
    saveImages,
    restoreContent,
    clearStorage,
    showToast
  };
})();

// Auto-init on DOM ready
document.addEventListener('DOMContentLoaded', () => DermaEditor.init());

// Export for module systems
if (typeof module !== 'undefined') module.exports = DermaEditor;