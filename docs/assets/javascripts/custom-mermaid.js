/* ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
*/

// Versione con error handling
document$.subscribe(() => {
  try {
    if(window.mermaid) {
      mermaid.initialize({
        theme: 'default',
        er: {
          layoutDirection: 'LR' // Prova Left-to-Right se TB non funziona
        },
        securityLevel: 'loose'
      });
      
      const mermaidElements = document.querySelectorAll('.mermaid, pre code.language-mermaid');
      mermaidElements.forEach(el => {
        if(el.tagName === 'CODE') {
          const container = document.createElement('div');
          container.className = 'mermaid';
          container.textContent = el.textContent;
          el.parentNode.replaceWith(container);
        }
      });
      
      mermaid.init();
    }
  } catch(e) {
    console.error("Mermaid error:", e);
  }
});