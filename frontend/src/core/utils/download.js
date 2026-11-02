// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Helper standalone per il download di un Blob lato browser
//        senza usare `window.location` (rompe lo stato SPA) ne'
//        librerie esterne. Pattern: blob URL + `<a>` programmatico
//        + revoke ritardato (l'invocazione di `link.click()` e' async
//        in alcuni browser; revoke immediato puo' interrompere il
//        salvataggio).
// ------------------------------------------------------------

// Scopo: Salva il blob come download con il filename suggerito.
//        Idempotente, no side-effect su routing/storia. Il revoke del
//        blob URL avviene in setTimeout (default 1s) per evitare race
//        col download stream.
export function downloadBlob(blob, fileName) {
  if (!blob) return
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName || 'download'
  // `rel=noopener` non e' applicabile a `download` ma documenta intent.
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // Revoke ritardato: alcuni browser leggono `url` dopo il click.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
