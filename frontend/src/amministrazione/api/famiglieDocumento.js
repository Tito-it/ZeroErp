// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: Client API delle FAMIGLIE DI DOCUMENTO — il catalogo della REGOLA che
//        i registri di numerazione applicano.
//
// ⚠️ LE ROTTE STANNO SOTTO `/vendite/`, LA MASCHERA VIVE IN AMMINISTRAZIONE, ed
//    e' la stessa scelta gia' fatta per i registri: il DATO e' di vendite (la
//    tabella, i tre guard, le due `fn_check_*`), il posto in cui si configura e'
//    l'amministrazione. ⭐ E qui il cancello e' PIU' STRETTO che sui registri —
//    solo amministratore (D6, Tid 2026-09-01) — perche' una famiglia e' globale:
//    toccarla cambia il comportamento di ogni emittente insieme.

import api from '../../core/api'

const BASE = '/vendite/famiglie'

// Scopo: lista paginata. ⛔ `attivo` si OMETTE per avere tutte: una famiglia
//        spenta continua a occupare la SUA TABELLA (l'indice unico e' parziale
//        `WHERE attivo`... ma la riga che blocca e' proprio quella attiva), e
//        soprattutto una famiglia spenta e' cio' che spiega perche' una tabella
//        non e' piu' disponibile.
export function listFamiglie(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Scopo: export CSV/XLSX con gli stessi filtri della lista.
// ⚠️ `responseType: 'blob'` e il parametro si chiama `formato`, non `format`:
//    `format` e' un magic query parameter di DRF e verrebbe intercettato prima
//    della view (`feedback_drf_format_magic_param`).
export function exportFamiglie(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

// Scopo: le famiglie ATTIVE coi loro default, per le tendine di dominio.
// ⭐ NON e' dietro il cancello dell'amministratore: la chiama il drawer dei
//    REGISTRI, che da qui prende `prefisso_default` e `lunghezza_default` per
//    precompilare la forma del numero e `presidia_data_documento` /
//    `gestisce_serie` per sapere quali campi mostrare.
export function lookupFamiglie() {
  return api.get(`${BASE}/lookup/`)
}

// Scopo: le sorgenti fra cui si sceglie la famiglia da creare (dal 2026-10-20,
//        brief-db-grammatica-unica-documenti 2c, G-5): una famiglia e' quella di
//        una SORGENTE, e la tabella dei documenti e' la sua `target_table`.
//        Ogni voce dice se la sorgente ha gia' una famiglia
//        (`famiglia_esistente`) e chi numera gia' la sua tabella
//        (`tabella_numerata_da`): sono informazioni per spegnere la voce e dire
//        perche', il rifiuto resta al database. Cancello dell'amministratore,
//        come la creazione. Envelope `{ results }`, come il lookup.
export function listSorgentiFamiglie() {
  return api.get(`${BASE}/sorgenti/`)
}

export function getFamiglia(id) {
  return api.get(`${BASE}/${id}/`)
}

// Scopo: crea la famiglia. ⭐ La risposta porta `registri_creati`: la creazione
//        passa dalla madre, che nella stessa transazione provvede i registri
//        mancanti su ogni emittente — ed e' meta' del lavoro appena fatto.
export function createFamiglia(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateFamiglia(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Scopo: accende o spegne la famiglia — verbo suo, non un PATCH su `attivo`,
//        come sul gemello dei registri.
export function setFamigliaAttiva(id, attivo) {
  return api.post(`${BASE}/${id}/attivo/`, { attivo })
}
