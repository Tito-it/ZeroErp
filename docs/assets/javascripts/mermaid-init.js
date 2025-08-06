/* ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
*/


document$.subscribe(() => {
  const config = {
    startOnLoad: false,
    theme: 'default',
    er: { 
      layoutDirection: 'TB',
      diagramPadding: 15
    }
  };
  
  mermaid.initialize(config);
  
  document.querySelectorAll('.mermaid').forEach((el) => {
    el.style.display = 'block';
    el.style.textAlign = 'center';
  });
  
  mermaid.run({
    querySelector: '.language-mermaid, .mermaid',
    nodes: document.querySelectorAll('.language-mermaid, .mermaid')
  });
});
