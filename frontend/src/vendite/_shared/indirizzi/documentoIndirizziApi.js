// Client API building block per gli indirizzi documento (pannello
// slot-per-tipo). Schema REST identico su tutti i domini vendite
// (preventivi/offerte/ordini/ddt/contratti — factory BE
// build_indirizzi_documento_views): qui il gemello FE, bindato al basePath
// del dominio come makeComponentiBomApi/makeNotesApi (regola del 2).
//
// GET  {base}/{id}/indirizzi/            -> { tipi_ammessi, indirizzi }
// POST {base}/{id}/indirizzi/            -> upsert uno-per-tipo:
//        picker:     { tipo_indirizzo_id, origine_indirizzo_id, snapshot? (soli contatti) }
//        una-tantum: { tipo_indirizzo_id, snapshot }
// DELETE {base}/{id}/indirizzi/{rowId}/  -> rimozione slot
//
// Lo snapshot geografico del picker e' composto SERVER-SIDE
// (script.fn_snapshot_indirizzo): il client non lo invia mai.

import api from '../../../core/api'

// Scopo: Display compatto di uno snapshot indirizzo documento (riga di
//        `indirizzi[]`): preferisce `display`, altrimenti compone
//        via/cap/citta/prov; intestazione come prefisso. Condiviso tra
//        sezione inline e drawer di gestione.
export function formatSnapshotDisplay(row) {
  const s = row?.snapshot ?? {}
  const geo = s.display
    || [s.via, [s.cap, s.citta].filter(Boolean).join(' '), s.prov]
      .filter(Boolean).join(', ')
  return [s.intestazione, geo].filter(Boolean).join(' — ')
}

// Scopo: Regola del tipo di default per il documento (decisa con Tid
//        2026-07-12): CON (Consegna, standard cross-dominio) → fallback
//        FATT → primo ammesso. Unica copia FE (sezione + drawer). Vale solo
//        per la UI: il BE `_tipo_default` non c'e' piu' (f371e614b7), alla
//        creazione gli indirizzi li assegna il DB (gli indirizzi seguono il
//        cliente).
export function pickTipoDefault(tipiAmmessi) {
  const tipi = tipiAmmessi ?? []
  return tipi.find((x) => x.tipo_indirizzo_codice_interno === 'CON')
    ?? tipi.find((x) => x.tipo_indirizzo_codice_interno === 'FATT')
    ?? tipi[0]
    ?? null
}

export function makeIndirizziDocumentoApi(base) {
  return {
    list(docId) {
      return api.get(`${base}/${docId}/indirizzi/`)
    },
    upsert(docId, payload) {
      return api.post(`${base}/${docId}/indirizzi/`, payload)
    },
    remove(docId, rowId) {
      return api.delete(`${base}/${docId}/indirizzi/${rowId}/`)
    },
  }
}
