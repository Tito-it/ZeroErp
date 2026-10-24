// Store Pinia per i DDT di vendita (lista, dettaglio, CRUD testata, righe,
// emissione, cambio stato data-driven, push singolo a commessa).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser (memoria feedback_pinia_userscoped).
//
// Clone strutturale di stores/ordini (analisi-ddt-vendita §D-4). Differenze:
// niente conferma (l'emissione DDT non genera documento in questa slice, il
// numero lo assegna il trigger a EMESSO) e niente riepilogo IVA (fuori scope,
// nessun endpoint BE). L'evasione (genera DDT da ordine) vive nel dominio
// ordine, non qui.

import { defaultFiltroDataDaString } from '../../../core/utils/date'
import { defineStore } from 'pinia'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaStoreCore } from '../../../core/composables/useListaStoreCore'
import { TAB_ENTITIES } from '../../../core/constants'
import { STATO_DDT } from '../constants'
import { avvisaDocumentiCollegati } from '../../_shared/annullo/avvisoDocumentiCollegati'
import {
  cambiaStatoDdt,
  correggiQtaEvasa as apiCorreggiQtaEvasa,
  createDdt,
  createRiga,
  deleteDdt,
  deleteRiga,
  emettiDdt,
  getDdt,
  getRiepilogoIva,
  listDdt,
  pushDdtACommessa,
  updateDdt,
  updateRiga,
} from '../api/ddtApi'

export const useDdtStore = defineStore('vendite-ddt', () => {
  const { emitDataChanged } = useTabEvents()

  // Floor temporale di default delle liste: vedi `defaultFiltroDataDaString`
  // (oggi-60gg al primo del mese). Regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  // Lista con guardia empty-state standard: `data_da` col default standard
  // conta come filtro attivo (`gateKeys`), quindi la lista si popola al mount.
  // Convenzione comune dei documenti di vendita: search >= 3, stato, BA,
  // utility, range date (gemello BE `extract_doc_list_filters`).
  const lista = useListaStoreCore({
    fetchPage: listDdt,
    filterDefaults: {
      stato_codice_interno: null,
      billing_account_id: null,
      utility_id: null,
      data_da: defaultDataDa,
      data_a: null,
    },
    gateKeys: ['stato_codice_interno', 'billing_account_id', 'utility_id', 'data_da', 'data_a'],
    // Default `data desc`: DDT con data piu' recente in cima (allineato al
    // default backend e al defaultSortField della DdtSearchTable). Il ripiego
    // del verso segue.
    orderBy: 'data',
    orderDir: 'desc',
    orderDirDefault: 'desc',
  })

  // Scopo: Dettaglio testata DDT + `righe_count` + il blob `capabilities`
  //        (can_edit_*, can_change_state, can_push_commessa, available_actions,
  //        non_editable_fields, stato_codice).
  async function fetchDetail(id) {
    const res = await getDdt(id)
    return res.data.data
  }

  // Scopo: Crea nuovo DDT standalone BOZZA. Il numero arriva dal trigger DB solo
  //        a EMESSO (in DRAFT resta NULL).
  async function create(payload) {
    const res = await createDdt(payload)
    emitDataChanged(TAB_ENTITIES.DDT, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata DDT (solo in DRAFT).
  async function update(id, payload) {
    const res = await updateDdt(id, payload)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Scopo: Hard-delete DDT BOZZA orfano (flusso abbandono drawer create).
  async function elimina(id) {
    const res = await deleteDdt(id)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // --- Transizioni / integrazione ---

  // DRAFT -> EMESSO (multipart): assegna il numero (trigger DB) + gate
  // approvazione componenti + genera il documento accompagnatorio (+ allegati
  // opzionali) in transazione atomica lato BE. Mirror di ordini.emetti.
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiDdt(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Transizione di stato generica data-driven (SPEDITO/CONSEGNATO/RESO/ANNULLATO).
  // `statoCodice` = target_state dell'azione; il trigger DB valida l'ammissibilita'.
  // `dichiarazione`: la conferma dell'annullo di una bolla con legami (D-8).
  // ⚠️ L'annullo ritira i legami: si avvisano i tab dei documenti che si
  // riaprono (BB `avvisaDocumentiCollegati`).
  async function cambiaStato(id, statoCodice, dichiarazione = {}) {
    const res = await cambiaStatoDdt(id, statoCodice, dichiarazione)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    if (statoCodice === STATO_DDT.ANNULLATO) avvisaDocumentiCollegati(emitDataChanged)
    return res.data.data
  }

  // Push singolo a commessa (DDT SPEDITO/CONSEGNATO). Ritorna il report orchestrator.
  async function push(id) {
    const res = await pushDdtACommessa(id)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Scopo: Carica il riepilogo IVA aggregato del DDT (una entry per aliquota,
  //        regola fiscale DPR 633/72 art. 21). Calcolo derivato lato DB dalle
  //        righe attive valorizzate: il FE legge solo lo stato corrente.
  async function loadRiepilogoIva(ddtId) {
    const res = await getRiepilogoIva(ddtId)
    return res.data.data
  }

  // --- Righe ---

  async function addRiga(ddtId, payload) {
    const res = await createRiga(ddtId, payload)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    return res.data.data
  }

  async function aggiornaRiga(ddtId, rigaId, payload) {
    const res = await updateRiga(ddtId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    return res.data.data
  }

  async function eliminaRiga(ddtId, rigaId) {
    const res = await deleteRiga(ddtId, rigaId)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    return res.data.data
  }

  // La quantita' evasa di una riga legata a un ordine o a un reso (D-2): cambia
  // anche il residuo (e lo stato) dell'ordine e la copertura del reso.
  async function correggiQtaEvasa(ddtId, rigaId, qtaOperativa) {
    const res = await apiCorreggiQtaEvasa(ddtId, rigaId, qtaOperativa)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    emitDataChanged(TAB_ENTITIES.ORDINE, null)
    emitDataChanged(TAB_ENTITIES.RESO, null)
    return res.data.data
  }

  return {
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,
    // testata
    fetchDetail, create, update, elimina,
    // transizioni
    emetti, cambiaStato, push,
    // riepilogo IVA
    loadRiepilogoIva,
    // righe
    addRiga, aggiornaRiga, eliminaRiga, correggiQtaEvasa,
  }
}, {
  userScoped: true,
})
