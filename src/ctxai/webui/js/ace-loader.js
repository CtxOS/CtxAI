let _acePromise = null;

/**
 * Lazily loads the Ace editor core and CSS.
 * Returns a promise that resolves to the `ace` global.
 * Safe to call multiple times — the script is only loaded once.
 */
export function ensureAce() {
  if (_acePromise) return _acePromise;
  if (globalThis.ace) return Promise.resolve(globalThis.ace);

  _acePromise = new Promise((resolve, reject) => {
    // Load CSS (idempotent — browser deduplicates identical <link> tags)
    if (!document.querySelector('link[href$="/ace-min/ace.min.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/vendor/ace-min/ace.min.css";
      document.head.appendChild(link);
    }

    const script = document.createElement("script");
    script.src = "/vendor/ace-min/ace.js";
    script.onload = () => resolve(globalThis.ace);
    script.onerror = (e) => {
      _acePromise = null;
      reject(e);
    };
    document.head.appendChild(script);
  });

  return _acePromise;
}
