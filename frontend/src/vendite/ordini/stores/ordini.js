// Store Pinia per gli ordini di vendita (lista, dettaglio, CRUD testata,
// righe, emissione, push singolo a commessa).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser (memoria feedback_pinia_userscoped).
//
// Niente revisioni ne' listino in testata (a differenza di preventivi/offerte):
// gli ordini fissano i prezzi alle righe alla conferma.

import { defaultFiltroDataDaString } from '../../../core/utils/date'
import { defineStore } from 'pinia'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaStoreCore } from '../../../core/composables/useListaStoreCore'
import { TAB_ENTITIES } from '../../../core/constants'
import { STATO_ORDINE } from '../constants'
import { avvisaDocumentiCollegati } from '../../_shared/annullo/avvisoDocumentiCollegati'
import {
  aggiornaDateConsegna as postDateConsegna,
  cambiaDataConsegnaConfermata as postDataConsegnaConfermata,
  cambiaStatoOrdine,
  createOrdine,
  createRiga,
  deleteOrdine,
  deleteRiga,
  emettiOrdine,
  generaDdtFromOrdine,
  getOrdine,
  getRiepilogoIva,
  listOrdini,
  listRighe,
  pushOrdineACommessa,
  updateOrdine,
  updateRiga,
} from '../api/ordiniApi'

export const useOrdiniStore = defineStore('vendite-ordini', () => {
  const { emitDataChanged } = useTabEvents()

  // Floor temporale di default delle liste: vedi `defaultFiltroDataDaString`
  // (oggi-60gg al primo del mese). Regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  // Lista con guardia empty-state standard: `data_da` col default standard
  // conta come filtro attivo (`gateKeys`), quindi la lista si popola al mount.
  // Convenzione comune dei documenti di vendita: search >= 3, stato, BA,
  // utility, range date (gemello BE `extract_doc_list_filters`).
  const lista = useListaStoreCore({
    fetchPage: listOrdini,
    filterDefaults: {
      stato_codice_interno: null,
      billing_account_id: null,
      utility_id: null,
      data_da: defaultDataDa,
      data_a: null,
    },
    gateKeys: ['stato_codice_interno', 'billing_account_id', 'utility_id', 'data_da', 'data_a'],
    // Default `data desc`: ordini con data piu' recente in cima (allineato al
    // default backend e al defaultSortField della OrdiniSearchTable). Il
    // ripiego del verso segue.
    orderBy: 'data',
    orderDir: 'desc',
    orderDirDefault: 'desc',
  })

  // Scopo: Dettaglio testata ordine + capability (righe_count, can_edit_*,
  //        can_conferma, can_push_commessa).
  async function fetchDetail(id) {
    const res = await getOrdine(id)
    return res.data.data
  }

  // Scopo: Crea nuovo ordine BOZZA. Il numero arriva dal trigger DB.
  async function create(payload) {
    const res = await createOrdine(payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata ordine (solo in DRAFT).
  async function update(id, payload) {
    const res = await updateOrdine(id, payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Scopo: Hard-delete ordine BOZZA orfano (flusso abbandono drawer create).
  async function elimina(id) {
    const res = await deleteOrdine(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // --- Transizioni / integrazione ---

  // DRAFT -> CONFERMATO (multipart): conferma + genera documento + allegati in
  // transazione atomica lato BE. Invocata da OrdineEmissioneDialog (il drawer
  // intercetta l'action 'conferma' e apre il dialog). È l'unica conferma: la
  // sola transizione senza PDF (`/conferma/`) è ritirata dal 2026-10-25 (M-2).
  // Mirror del flusso emissione preventivo/offerta.
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiOrdine(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Push singolo a commessa (ordine CONFERMATO). Ritorna il report orchestrator.
  async function push(id) {
    const res = await pushOrdineACommessa(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Transizione di stato generica data-driven (es. annulla). `statoCodice` =
  // target_state dell'azione; il trigger DB valida l'ammissibilita'.
  // `dichiarazione`: la conferma dell'annullo con legami; l'annullo riapre i
  // documenti dall'altra parte, e se ne avvisano i tab.
  async function cambiaStato(id, statoCodice, dichiarazione = {}) {
    const res = await cambiaStatoOrdine(id, statoCodice, dichiarazione)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    if (statoCodice === STATO_ORDINE.ANNULLATO) avvisaDocumentiCollegati(emitDataChanged)
    return res.data.data
  }

  // --- Righe ---

  async function loadRighe(ordineId) {
    const res = await listRighe(ordineId)
    return res.data.data
  }

  async function addRiga(ordineId, payload) {
    const res = await createRiga(ordineId, payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  async function aggiornaRiga(ordineId, rigaId, payload) {
    const res = await updateRiga(ordineId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  async function eliminaRiga(ordineId, rigaId) {
    const res = await deleteRiga(ordineId, rigaId)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  // --- Date di consegna (brief-db-date-consegna-righe-in-blocco) ---

  // Scopo: la data di consegna confermata di UNA riga, anche dopo la
  //        conferma. Scrive sull'ordine, quindi avvisa come ogni scrittura
  //        (frontend-standards §«Producer cross-tab»).
  async function cambiaDataConsegnaConfermata(ordineId, rigaId, data) {
    const res = await postDataConsegnaConfermata(ordineId, rigaId, data)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  // Scopo: «Aggiorna date di consegna»: una data su piu' righe. Si avvisa
  //        solo quando si scrive: l'anteprima conta e basta.
  // ⚠️ Ritorna la RESPONSE, non l'esito: l'esito ha una chiave `data` (la data
  //    scritta) e `useApiHandler.execute` lo scambierebbe per un envelope,
  //    restituendo la sola data.
  async function aggiornaDateConsegna(ordineId, payload) {
    const res = await postDateConsegna(ordineId, payload)
    if (!payload.anteprima) emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res
  }

  // --- Evasione ---

  // Scopo: Evade l'ordine generando un DDT (in DRAFT) dalle righe scelte, o
  //        da tutto il residuo con `righe = null`. Il verbo scrive su DUE
  //        entita' — l'ordine (residui, stato) e il DDT che nasce — e lo store
  //        le avvisa entrambe (frontend-standards §«Producer cross-tab»).
  async function generaDdt(ordineId, righe = null) {
    const res = await generaDdtFromOrdine(ordineId, righe)
    const data = res.data.data
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    if (data?.ddt_id) emitDataChanged(TAB_ENTITIES.DDT, data.ddt_id)
    return data
  }

  // --- Riepilogo IVA ---

  // Scopo: Carica il riepilogo IVA aggregato dell'ordine (una entry per
  //        aliquota, regola fiscale DPR 633/72 art. 21). Calcolo derivato lato
  //        DB dalle righe attive: il FE legge solo lo stato corrente.
  async function loadRiepilogoIva(ordineId) {
    const res = await getRiepilogoIva(ordineId)
    return res.data.data
  }

  return {
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,
    // testata
    fetchDetail, create, update, elimina,
    // transizioni
    emetti, push, cambiaStato,
    // righe
    loadRighe, addRiga, aggiornaRiga, eliminaRiga,
    // date di consegna
    cambiaDataConsegnaConfermata, aggiornaDateConsegna,
    // evasione
    generaDdt,
    // riepilogo IVA
    loadRiepilogoIva,
  }
}, {
  userScoped: true,
})
