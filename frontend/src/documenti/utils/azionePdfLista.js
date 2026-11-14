// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: LA VOCE «PDF» NEL KEBAB DI UNA LISTA DOCUMENTO. Dalla lista non si fa
//        anteprima: si apre la gestione dei PDF gia' generati
//        (`PdfDocumentiSorgenteDialog`), e solo dove lo stato del documento
//        li archivia (`pdf_mode` = ARCHIVE, la colonna di `config.stati_doc_*`
//        che la vista lista porta, la stessa da cui la capability del
//        dettaglio dice `pdf.mode`). Altrove la voce c'e' ma e' spenta, col
//        suo perche'.
//        Nato il 2026-11-14 (brief-db-stati-documento-dal-vocabolario FE-P2,
//        FE-V3, FE-C4, FE-D2, D-PDF (a); regola del 2, ok Tid): la scriveva
//        `OrdiniSearchTable` da `pdf_mode`, e le altre quattro liste da
//        `stato_codice_interno === 'DRAFT'` (o `'BOZZA'`).
//
// ⭐ I testi stanno sotto `<prefisso>.pdf.{label_scarica, tooltip_lista,
//    tooltip_lista_disabilitato}`: le cinque liste li hanno gia' tutti
//    (presidio: `azionePdfLista.spec.js`).
//
// Uso (in `buildRowActions(data)`):
//   azionePdfLista(t, data, { prefisso: 'vendite.ddt', apri: onPdfClick })
//   function onPdfClick(row) { pdfDialogDdt.value = row; pdfDialogVisible.value = true }
import { MANAGE_ICONS } from '../../core/constants'
import { PDF_MODE } from '../constants'

// La riga ha PDF archiviati da aprire?
export function pdfArchiviato(row) {
  return row?.pdf_mode === PDF_MODE.ARCHIVE
}

// Scopo: la voce del kebab, nella forma di `RowActionsMenu`. `apri(row)` si
//        chiama solo su una riga con PDF archiviati.
export function azionePdfLista(t, row, { prefisso, apri }) {
  const conDocumento = pdfArchiviato(row)
  // La chiave si compone a pezzi: `<prefisso>.pdf.<testo>`.
  const testo = (nome) => t([prefisso, 'pdf', nome].join('.'))
  return {
    key: 'documenti-pdf',
    label: testo('label_scarica'),
    icon: MANAGE_ICONS.PDF,
    severity: 'primary',
    disabled: !conDocumento,
    tooltip: conDocumento ? testo('tooltip_lista') : testo('tooltip_lista_disabilitato'),
    command: () => { if (conDocumento && row?.id) apri(row) },
  }
}
