// Store Pinia per la gestione preventivi vendita (lista, dettaglio, CRUD, azioni stato).
//
// ⭐ Dal 2026-09-18 la lista e' `useListaStoreCore`, chiamato qui dentro: era
//    una copia a mano del suo `buildParams` su `useListaEmptyStateFetch`. La
//    sola cosa che il core non sapeva dire — e che teneva questa copia in
//    piedi — era il NOME SUL FILO della data di fine (`data_al`), che ora e'
//    `paramNames`. Non passa da una factory perche' lo store e' anche righe,
//    revisioni, smistamento, pratica: la lista e' una parte.

import { defaultFiltroDataDaString } from '../../../core/utils/date'
import { defineStore } from 'pinia'
import {
  listPreventivi, getPreventivo, createPreventivo, updatePreventivo, deletePreventivo,
  cambiaStatoPreventivo, emettiPreventivo, creaRevisione,
  createRiga, updateRiga, deleteRiga, getRiepilogoIva,
  aggiornaDateConsegna as postDateConsegna,
  pushCommessa, getSmistamento, generaPratica, generaOrdineFromPreventivo,
} from '../api/preventiviApi'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaStoreCore } from '../../../core/composables/useListaStoreCore'
import { TAB_ENTITIES } from '../../../core/constants'
import { STATO_PREVENTIVO } from '../../constants'
import { avvisaDocumentiCollegati } from '../../_shared/annullo/avvisoDocumentiCollegati'

export const usePreventiviStore = defineStore('vendite-preventivi', () => {
  const { emitDataChanged } = useTabEvents()

  // Floor temporale di default delle liste: vedi `defaultFiltroDataDaString`
  // (oggi-60gg al primo del mese). Regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  // Lista con guardia empty-state standard: `data_da` col default standard
  // conta come filtro attivo (`gateKeys`) e garantisce l'auto-load
  // all'apertura (frontend-standards "Filtro data standard"). Paginazione
  // limit/offset standard (riallineata 2026-06-03: il BE usa parse_list_params,
  // era l'unico dominio su page/page_size).
  const lista = useListaStoreCore({
    fetchPage: listPreventivi,
    filterDefaults: {
      stato: null,
      billing_account_id: null,
      utility_id: null,
      data_da: defaultDataDa,
      data_a: null,
      // Default true: la lista mostra solo l'ultima revisione per numero
      // (le revisioni superseded restano nello storico DB ma non in UI).
      // Toggle "Mostra storico revisioni" lo flippa. ⚠️ Viaggia sempre,
      // anche a `true`: il BE lo legge con `qp_bool(..., default=True)`, e se
      // l'operatore vuole lo storico (toggle ON => filtro OFF) deve riceverlo
      // come `false` esplicito.
      solo_ultima_revisione: true,
    },
    // ⛔ IL VALORE CHE NON RESTRINGE, dichiarato (2026-09-23). «Mostra storico»
    //    acceso scrive `false`, che deve viaggiare sul filo — il BE e'
    //    `qp_bool(..., default=True)` — ma la lista in quello stato e' la piu'
    //    LARGA possibile: senza questa riga il segno dei filtri attivi contava 1
    //    proprio quando l'operatore aveva tolto la restrizione, cioe' il numero
    //    saliva allargando. Il perche' per intero sta su `segnoFiltri`.
    filtriNeutri: { solo_ultima_revisione: false },
    gateKeys: ['stato', 'billing_account_id', 'utility_id', 'data_a', 'data_da'],
    // Il BE chiama la data di fine `data_al` (preventivi_views.py); nello store
    // resta `data_a`, che e' il nome che `useSearchTable` azzera sul deep-link
    // e che `useStoreFilterBindings` lega al DatePicker.
    paramNames: { data_a: 'data_al' },
    // Il piu' recente in cima; il ripiego del verso segue.
    orderBy: 'data',
    orderDir: 'desc',
    orderDirDefault: 'desc',
  })

  // Scopo: Dettaglio completo preventivo.
  async function fetchDetail(id) {
    const res = await getPreventivo(id)
    return res.data.data
  }

  // Scopo: Crea nuovo preventivo.
  async function create(payload) {
    const res = await createPreventivo(payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili del preventivo.
  async function update(id, payload) {
    const res = await updatePreventivo(id, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Hard-delete preventivo BOZZA orfano (flusso abbandono bozza drawer).
  async function elimina(id) {
    const res = await deletePreventivo(id)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Cambia stato preventivo (EMESSO→ACCETTATO, *→ANNULLATO, ecc.).
  // extras: payload aggiuntivo per transizioni che richiedono dati di processo.
  // Caso noto: EMESSO → ACCETTATO richiede fatturazione_immediata + competenza_mese
  // (vedi backend preventivi_service.cambia_stato gate accettazione).
  // NB refactor 2026-05-28: BOZZA->EMESSO NON passa piu' da qui — usare
  // `emetti()` sotto (orchestra atomic state + documento + allegati via
  // PreventivoEmissioneDialog). Il BE rifiuterebbe E_PREV_VALIDAZIONE.
  // Verso ANNULLATO `extras` porta la dichiarazione della conferma
  // (`{ legami_confermati }`), e l'annullo riapre i documenti dall'altra parte.
  async function cambiaStato(id, nuovoStato, extras = {}) {
    const payload = { nuovo_stato: nuovoStato, ...extras }
    const res = await cambiaStatoPreventivo(id, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    if (nuovoStato === STATO_PREVENTIVO.ANNULLATO) avvisaDocumentiCollegati(emitDataChanged)
    return res.data.data
  }

  // Scopo: BOZZA -> EMESSO (multipart). Cambia stato + genera documento +
  // allegati in transazione atomica lato BE. Mirror del flusso offerta.
  // Invocata dal PreventivoEmissioneDialog (PreventiviDrawer intercetta
  // l'action 'emetti' e apre il dialog invece di chiamare cambiaStato).
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiPreventivo(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Crea nuova revisione del preventivo.
  async function nuovaRevisione(id) {
    const res = await creaRevisione(id)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // --- Righe ---

  // Scopo: Aggiunge riga al preventivo.
  async function addRiga(preventivoId, payload) {
    const res = await createRiga(preventivoId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Aggiorna riga preventivo.
  async function aggiornaRiga(preventivoId, rigaId, payload) {
    const res = await updateRiga(preventivoId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Elimina riga preventivo (soft delete).
  async function eliminaRiga(preventivoId, rigaId) {
    const res = await deleteRiga(preventivoId, rigaId)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: «Aggiorna date di consegna» (brief-db-date-consegna-righe-in-blocco):
  //        la data richiesta su piu' righe. Si avvisa solo quando si scrive:
  //        l'anteprima conta e basta.
  // ⚠️ Ritorna la RESPONSE, non l'esito: l'esito ha una chiave `data` (la data
  //    scritta) e `useApiHandler.execute` lo scambierebbe per un envelope,
  //    restituendo la sola data.
  async function aggiornaDateConsegna(preventivoId, payload) {
    const res = await postDateConsegna(preventivoId, payload)
    if (!payload.anteprima) emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res
  }

  // Scopo: Carica riepilogo IVA aggregato del preventivo (regola fiscale
  //        DPR 633/72 art. 21). Una entry per aliquota IVA distinta. Il
  //        ricalcolo e' atomico lato DB su ogni mutazione delle righe.
  async function loadRiepilogoIva(preventivoId) {
    const res = await getRiepilogoIva(preventivoId)
    return res.data.data
  }

  // --- Integrazione ---
  // NB indirizzi: gestiti dal BB condiviso _shared/indirizzi
  // (DocumentoIndirizziPanel + makeIndirizziDocumentoApi), non dallo store.

  // Scopo: Push preventivo in commessa per fatturazione. `righeIds` opzionale:
  //        sottoinsieme righe servizio (smistamento selettivo); null = tutte.
  async function inviaACommessa(preventivoId, righeIds = null) {
    const res = await pushCommessa(preventivoId, righeIds)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Ramo merce dello smistamento: genera l'ordine dalle righe merce.
  //        Il verbo scrive su DUE entita' — il preventivo (righe smistate,
  //        transizione verso EVASO) e l'ordine che nasce — e lo store le avvisa
  //        entrambe: qualunque superficie smisti, le due liste lo sanno senza
  //        che il chiamante se ne ricordi (frontend-standards §«Producer
  //        cross-tab»).
  async function generaOrdine(preventivoId, righeIds = null) {
    const res = await generaOrdineFromPreventivo(preventivoId, righeIds)
    const data = res.data.data
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    if (data?.ordine_id) emitDataChanged(TAB_ENTITIES.ORDINE, data.ordine_id)
    return data
  }

  // Scopo: Carica lo smistamento del preventivo (aggregato per ramo + righe
  //        con stato autorevole) per il Pannello Smistamento.
  async function loadSmistamento(preventivoId) {
    const res = await getSmistamento(preventivoId)
    return res.data.data
  }

  // Scopo: Genera pratica esecutiva da preventivo.
  async function creaPratica(preventivoId, payload) {
    const res = await generaPratica(preventivoId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  return {
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,
    fetchDetail, create, update, elimina,
    cambiaStato, emetti, nuovaRevisione,
    addRiga, aggiornaRiga, eliminaRiga, aggiornaDateConsegna, loadRiepilogoIva,
    inviaACommessa, generaOrdine, loadSmistamento,
    creaPratica,
  }
}, {
  // Reset automatico al logout (autoResetPlugin): items + filters dell'utente
  // non devono persistere per l'eventuale utente successivo sullo stesso browser.
  userScoped: true,
})
