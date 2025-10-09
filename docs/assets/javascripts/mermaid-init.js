/* ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
*/

// docs/assets/javascripts/mermaid-init.js

function renderMermaid() {
  // 1) se per qualche motivo i blocchi sono ancora <pre><code class="language-mermaid">, wrappali
  document.querySelectorAll('pre code.language-mermaid').forEach(code => {
    const pre = code.parentElement;
    const div = document.createElement('div');
    div.className = 'mermaid';
    div.textContent = code.textContent;
    pre.replaceWith(div);
  });

  if (!window.mermaid) {
    console.warn('Mermaid not loaded');
    return;
  }

  try {
    // inizializza una volta sola: v10/v11 tollerano reinits, ma evitiamo warning
    if (!window.__mermaidInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose'
        // il tuo %%{init: ...}%% dentro al blocco può sovrascrivere opzioni come 'er.layoutDirection'
      });
      window.__mermaidInitialized = true;
    }

    // v11: mermaid.run();  v10: mermaid.init(undefined, ".mermaid");
    if (typeof mermaid.run === 'function') {
      mermaid.run();
    } else if (typeof mermaid.init === 'function') {
      mermaid.init(undefined, '.mermaid');
    }
  } catch (e) {
    console.error('Mermaid render error:', e);
  }
}

// Supporto SPA di MkDocs Material
if (window.document$) {
  document$.subscribe(renderMermaid);
} else {
  document.addEventListener('DOMContentLoaded', renderMermaid);
}
