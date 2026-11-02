// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il payload di una versione di template documentale dal form del
//        drawer (`TemplateVersioneDrawer`). Funzione pura, provata a parte.
// Note: in CREAZIONE un campo con default di COLONNA lasciato vuoto non si
//       manda: vale il default del DB, che il frontend non ricopia (fino al
//       2026-10-03 i margini erano 15 mm qui e 10 nella colonna). ⛔ In
//       MODIFICA si manda com'e': un margine svuotato e' una richiesta che il
//       backend rifiuta col suo errore, non un «lascia com'era» deciso qui.
// ------------------------------------------------------------

import { toDateString } from '../../core/utils/date'

// I campi con un default di colonna su `documenti.template_documenti_versioni`.
export const CAMPI_DEFAULT_DB = Object.freeze([
  'formato_template', 'page_format', 'page_orientation',
  'margin_top_mm', 'margin_right_mm', 'margin_bottom_mm', 'margin_left_mm',
])

// Scopo: costruisce il payload; `nuova` = creazione di una versione.
export function payloadVersione(form, { nuova }) {
  const payload = {
    titolo: form.titolo.trim(),
    formato_template: form.formato_template,
    html_template: form.html_template || null,
    css_template: form.css_template || null,
    markdown_template: form.markdown_template || null,
    render_engine_id: form.render_engine_id,
    versione_contesto: form.versione_contesto,
    page_format: form.page_format,
    page_orientation: form.page_orientation,
    margin_top_mm: form.margin_top_mm,
    margin_right_mm: form.margin_right_mm,
    margin_bottom_mm: form.margin_bottom_mm,
    margin_left_mm: form.margin_left_mm,
    valido_dal: toDateString(form.valido_dal),
    valido_al: toDateString(form.valido_al),
    attivo: form.attivo,
  }
  if (nuova) {
    for (const campo of CAMPI_DEFAULT_DB) {
      if (payload[campo] === null || payload[campo] === undefined) delete payload[campo]
    }
  }
  return payload
}
