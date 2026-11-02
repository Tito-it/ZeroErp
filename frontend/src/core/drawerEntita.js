// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL REGISTRO «TIPO DI ENTITA' → DRAWER DI DETTAGLIO»: dato un codice
//        (`config.sorgenti.codice_interno`, lo stesso vocabolario di
//        `config.tipi_entita`) e un id, quale drawer si apre, con quale prop
//        id e se accetta `mode`.
//
// ⭐ Dal 2026-09-26 sta in `core` e i domini SI ISCRIVONO (decisione Tid,
//    frontend-standards §«Confini fra domini»). Prima era
//    `vendite/_shared/documenti/documentoDrawers.js` e ne scriveva le voci a
//    mano: lo leggevano `App.vue` e `core/bersagli.js`, cioe' `core` dipendeva
//    da vendite — e i documenti di acquisti avrebbero dovuto iscriversi dentro
//    `vendite/`. Ora le voci vendite stanno in `vendite/iscrizioni.js`.
//
// Storia: promosso a BB cross-dominio il 2026-07-25 (era
// `_shared/lineage/lineageDrawers`, regola del 2 — 2o consumatore).
//
// ⚠️ I drawer si iscrivono con un import DINAMICO (`load`), di proposito: ogni
//    drawer documento importa staticamente `DocumentoCollegamentiBar`, che
//    monta l'host — un import statico chiuderebbe il ciclo drawer → barra →
//    host → drawer. L'host ATTENDE `load` e poi rende il componente RISOLTO
//    (non un `defineAsyncComponent`): cosi' il drawer monta con
//    `visible=false` e osserva la transizione false→true che innesca
//    `@after-show` (bug «primo click apre vuoto, riapertura ok»).
// ------------------------------------------------------------
import { creaRegistro } from './registri'

// Chiavi del registry — fonte unica per i caller (mai literal sparsi).
// I primi 7 sono codici sorgente veri (`config.sorgenti.codice_interno`, gli
// stessi che il BE mette in from_doc_tipo/to_doc_tipo del lineage);
// COMMESSA_GESTIONE e' una chiave NON-sorgente, vedi sotto.
export const DOCUMENTO_DRAWER_TIPI = Object.freeze({
  PREVENTIVO: 'PREVENTIVO',
  OFFERTA_COMMERCIALE: 'OFFERTA_COMMERCIALE',
  ORDINE_VENDITA: 'ORDINE_VENDITA',
  CONTRATTO: 'CONTRATTO',
  DDT_VENDITA: 'DDT_VENDITA',
  RESO_VENDITA: 'RESO_VENDITA',
  FATTURA: 'FATTURA',
  COMMESSA: 'COMMESSA',
  COMMESSA_GESTIONE: 'COMMESSA_GESTIONE',
})

// Chiavi NON-sorgente: drawer raggiungibili per id ma senza un
// `config.sorgenti.codice_interno` corrispondente. Tenute a parte perche' i
// consumatori che partono da un TIPO SORGENTE (lineage) non devono vederle.
const CHIAVI_NON_SORGENTE = [DOCUMENTO_DRAWER_TIPI.COMMESSA_GESTIONE]

const registro = creaRegistro('drawer-entita')

// Scopo: iscrive il drawer di un tipo. Se il tipo e' una SORGENTE lo dice il
//        vocabolario qui sopra, non chi si iscrive.
// ⛔ Un tipo fuori vocabolario e' un ERRORE all'avvio: un refuso
//    (`'FATTURE'`) iscriverebbe una voce che nessuno legge, e il tipo vero
//    resterebbe senza drawer — tappe non apribili, senza nessun errore.
//    Un dominio con tipi nuovi (acquisti) li aggiunge a DOCUMENTO_DRAWER_TIPI.
export function iscriviDrawerEntita(tipo, { load, idProp, hasMode = false }) {
  if (!Object.values(DOCUMENTO_DRAWER_TIPI).includes(tipo)) {
    throw new Error(`Drawer entita': tipo sconosciuto «${tipo}»`)
  }
  registro.iscrivi(tipo, { load, idProp, hasMode, sorgente: !CHIAVI_NON_SORGENTE.includes(tipo) })
}

// Scopo: la voce di un tipo — `{ load, idProp, hasMode, sorgente }` — o
//        `null` se nessun dominio sa aprirlo.
export function drawerEntita(tipo) {
  return registro.voce(tipo)
}

// Scopo: una tappa del grafo lineage e' apribile se ha un id di dominio
//        risolto dal BE e un tipo SORGENTE con drawer iscritto. Regola UNICA:
//        la usa chi decide se rendere il codice come link e chi apre il
//        drawer. `docId` null = documento fuori scope RLS → tappa consultiva.
export function isTappaApribile(row) {
  if (row?.docId == null) return false
  return drawerEntita(row.tipoCodice)?.sorgente === true
}
