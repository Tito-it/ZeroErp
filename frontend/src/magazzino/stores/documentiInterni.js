// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Gli store delle liste del DOCUMENTO INTERNO di magazzino — uno per
//        famiglia (`magazzino.inventari`, `magazzino.rettifiche`), costruiti
//        dalla STESSA configurazione, piu' i verbi di scrittura che avvisano
//        le altre tab.
// Note: ⭐ Q-1 (Tid, 2026-09-18): una implementazione, due configurazioni. Qui
//       la configurazione e' `FAMIGLIE[famiglia]` di `vocabolari.js`, e i due
//       store nascono da un ciclo — non da due file.
//       ⭐ NON E' SCRITTO A MANO: filtri, fetch paginata, cancello, reset e la
//       distinzione fra «vuota» e «non letta» vivono in `createListaStore` /
//       `useListaStoreCore`. Qui restano il floor temporale, l'ordinamento di
//       apertura e i verbi.
//       ⭐ I VERBI STANNO QUI perche' il PRODUCER cross-tab sta sempre nello
//       store (frontend-standards §Enum centralizzati): ogni scrittura riuscita
//       emette `TAB_ENTITIES.<famiglia>`, e la lista dell'altra tab si ricarica
//       da sola. I componenti li chiamano con `execute(() => store.verbo(...))`.
//       ⚠️ `userScoped: true` (default della factory): filtri e pagina sono
//       dell'operatore, non del browser.
// ------------------------------------------------------------

import { useTabEvents } from '../../core/composables/useTabEvents'
import { createListaStore } from '../../core/stores/createListaStore'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import {
  aggiornaDocumento,
  aggiornaRiga,
  cambiaStatoDocumento,
  creaDocumento,
  creaRiga,
  eliminaDocumento,
  eliminaRiga,
  getDocumento,
  listDocumenti,
  registraDocumento,
} from '../api/magazzino'
import { FAMIGLIE } from '../vocabolari'

// Scopo: costruisce lo store-lista di UNA famiglia.
function creaStoreFamiglia(f) {
  return createListaStore(`magazzino-${f.codice}`, {
    fetchPage: (params) => listDocumenti(f.codice, params),
    // Una lista di documenti parte PIENA, col floor temporale standard delle
    // liste (oggi-60gg al 1° del mese, `feedback_filtro_data_liste`): non e'
    // una coda di lavoro, e' un archivio operativo che si legge dal recente.
    startsEmpty: false,
    filterDefaults: {
      magazzino_id: null,
      stato: null,
      data_da: defaultFiltroDataDaString(),
      data_a: null,
    },
    // Il giorno piu' recente in cima: e' il default del backend (`data DESC,
    // id DESC`), quindi la lista non si riordina al primo click, e il ripiego
    // del verso segue.
    orderBy: 'data',
    orderDir: 'desc',
    orderDirDefault: 'desc',
    extend: () => {
      const { emitDataChanged } = useTabEvents()

      // Scopo: il dettaglio della testata (testata + magazzino + righe_count
      //        + piano_riepilogo). Gia' UNWRAPPATO: si chiama direttamente,
      //        non dentro `execute` (`feedback_useapihandler_solo_axios`).
      async function fetchDetail(id) {
        const res = await getDocumento(f.codice, id)
        return res.data.data
      }

      // ── i verbi: ogni scrittura riuscita avvisa le altre tab ──
      async function crea(payload) {
        const res = await creaDocumento(f.codice, payload)
        emitDataChanged(f.tabEntity, res.data.data.id)
        return res.data.data
      }

      async function aggiorna(id, payload) {
        const res = await aggiornaDocumento(f.codice, id, payload)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      async function elimina(id) {
        const res = await eliminaDocumento(f.codice, id)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      // ⛔ Solo i RICHIEDIBILI (`CONFIRM` · `CANCEL` · `DRAFT`): `POSTED` lo
      //    scrive `registra`. Il vocabolario lo tiene il backend, qui si passa.
      async function cambiaStato(id, stato) {
        const res = await cambiaStatoDocumento(f.codice, id, stato)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      // Il posting: `{movimenti, n_movimenti, documento}`. `config` porta la
      // key del GESTO (`useChiaveGesto`, nel drawer): lo store la passa e basta.
      async function registra(id, config = {}) {
        const res = await registraDocumento(f.codice, id, config)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      // ── le righe: cambiano il DOCUMENTO (righe_count, il riepilogo del
      //    piano), quindi avvisano con l'evento della famiglia. Stanno qui e
      //    non nello store delle righe, che e' di sola lettura.
      async function creaRigaDocumento(id, payload) {
        const res = await creaRiga(f.codice, id, payload)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      async function aggiornaRigaDocumento(id, rigaId, payload) {
        const res = await aggiornaRiga(f.codice, id, rigaId, payload)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      async function eliminaRigaDocumento(id, rigaId) {
        const res = await eliminaRiga(f.codice, id, rigaId)
        emitDataChanged(f.tabEntity, id)
        return res.data.data
      }

      return {
        fetchDetail, crea, aggiorna, elimina, cambiaStato, registra,
        creaRiga: creaRigaDocumento,
        aggiornaRiga: aggiornaRigaDocumento,
        eliminaRiga: eliminaRigaDocumento,
      }
    },
  })
}

// I due store, per codice di famiglia. ⛔ Chiuso come `FAMIGLIE`: una terza
// famiglia e' una riga in `vocabolari.js`, non un file qui.
const STORES = Object.fromEntries(
  Object.values(FAMIGLIE).map((f) => [f.codice, creaStoreFamiglia(f)]),
)

// Scopo: lo store della famiglia chiesta. I componenti unici (lista, drawer,
//        dialog) lo prendono da qui con la famiglia in prop.
export function useDocumentiInterniStore(famiglia) {
  const useStore = STORES[famiglia]
  if (!useStore) throw new Error(`[magazzino] famiglia sconosciuta: ${famiglia}`)
  return useStore()
}
