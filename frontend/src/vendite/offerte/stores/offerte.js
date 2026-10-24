// Store Pinia per la gestione offerte commerciali (lista, dettaglio, CRUD,
// transizioni stato, revisioni, push contratto, eccezioni).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser.
//
// Utility 1:1: gestita inline nel payload `create` / `update` testata
// (atomicita' BE via `OfferteService._add_utility_inline` /
// `_upsert_utility_inline`). Nessuna action dedicata nello store:
// l'esposizione separata (POST/PATCH `/utility/`) resta come endpoint BE
// per smoke test e consumer esterni, ma il drawer FE non la usa.
//
// ⭐ Dal 2026-09-18 la lista e' `useListaStoreCore`, chiamato qui dentro: era
//    una copia a mano del suo `buildParams` su `useListaEmptyStateFetch`. La
//    sola cosa che il core non sapeva dire — e che teneva questa copia in
//    piedi — era il NOME SUL FILO delle due date (`validita_dal_min/max`), che
//    ora e' `paramNames`. Non passa da una factory perche' lo store e' anche
//    transizioni, revisioni, push a contratto, eccezioni: la lista e' una parte.

import { defaultFiltroDataDaString } from '../../../core/utils/date'
import { defineStore } from 'pinia'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaStoreCore } from '../../../core/composables/useListaStoreCore'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  annullaOfferta,
  createEccezione,
  createOfferta,
  creaRevisioneOfferta,
  deleteEccezione,
  deleteOfferta,
  emettiOfferta,
  generaOrdineFromOfferta,
  getContrattoSovrapposto,
  getOfferta,
  listOfferte,
  pushOffertaAContratto,
  registraEsitoOfferta,
  updateEccezione,
  updateOfferta,
} from '../api/offerteApi'

export const useOfferteStore = defineStore('vendite-offerte', () => {
  const { emitDataChanged } = useTabEvents()

  // Floor temporale di default delle liste: vedi `defaultFiltroDataDaString`
  // (oggi-60gg al primo del mese). Regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  // Lista con guardia empty-state standard: `data_da` col default standard
  // conta come filtro attivo (`gateKeys`), quindi la lista si popola al mount.
  const lista = useListaStoreCore({
    fetchPage: listOfferte,
    filterDefaults: {
      stato_codice_interno: null,
      billing_account_id: null,
      utility_id: null,
      listino_id: null,
      data_da: defaultDataDa,
      data_a: null,
      // Filtro revisione attiva (mirror preventivi): default true = mostra solo
      // l'ultima revisione viva per lineage. Toggle "Mostra storico revisioni"
      // lo nega (false) per vedere tutte le revisioni incluse SUPERATA/ANNULLATA.
      // ⚠️ Viaggia sempre, anche a `true`: il BE lo legge con
      //    `qp_bool(..., default=True)`, quindi «vero» e «assente» sono la
      //    stessa cosa, e «falso» esplicito e' cio' che serve al toggle.
      solo_ultima_revisione: true,
    },
    // ⛔ IL VALORE CHE NON RESTRINGE, dichiarato (2026-09-23). «Mostra storico»
    //    acceso scrive `false`, che deve viaggiare sul filo — il BE e'
    //    `qp_bool(..., default=True)` — ma la lista in quello stato e' la piu'
    //    LARGA possibile: senza questa riga il segno dei filtri attivi contava 1
    //    proprio quando l'operatore aveva tolto la restrizione, cioe' il numero
    //    saliva allargando. Il perche' per intero sta su `segnoFiltri`.
    filtriNeutri: { solo_ultima_revisione: false },
    gateKeys: [
      'stato_codice_interno', 'billing_account_id', 'utility_id', 'listino_id',
      'data_a', 'data_da',
    ],
    // I filtri data BE si chiamano validita_dal_min / validita_dal_max (vedi
    // views_offerte.py): si applicano sul `validita_dal` della testata. Nello
    // store restano `data_da`/`data_a`, che sono i nomi che `useSearchTable`
    // azzera sul deep-link e che `useStoreFilterBindings` lega ai DatePicker.
    paramNames: { data_da: 'validita_dal_min', data_a: 'validita_dal_max' },
    // Default coerente con `OfferteSearchTable.useSearchTable.defaultSortField`:
    // entrambi devono puntare a una colonna visibile e sortable, altrimenti
    // PrimeVue genera un sort-indicator "fantasma" (underline anomala
    // sotto le label) sulla riga header. Allineare se si cambia uno dei due.
    // Default `validita_dal desc`: offerte con inizio validita' piu' recente
    // in cima (allineato al pattern preventivi/contratti); il ripiego del verso
    // segue.
    orderBy: 'validita_dal',
    orderDir: 'desc',
    orderDirDefault: 'desc',
  })

  // Scopo: Dettaglio completo offerta (testata + eccezioni + utility 1:1).
  async function fetchDetail(id) {
    const res = await getOfferta(id)
    return res.data.data
  }

  // Scopo: Crea nuova offerta BOZZA. Il codice OFC-* arriva dal trigger DB.
  async function create(payload) {
    const res = await createOfferta(payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata offerta (solo se in BOZZA).
  async function update(id, payload) {
    const res = await updateOfferta(id, payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // Scopo: Hard-delete offerta BOZZA orfana (flusso abbandono drawer create).
  async function elimina(id) {
    const res = await deleteOfferta(id)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // --- Transizioni stato ---

  // BOZZA -> EMESSA. Genera+persiste documento + allegati (multipart) lato
  // BE in transazione atomica. `allegati` = array di File (opzionale).
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiOfferta(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // EMESSA -> ACCETTATA / RIFIUTATA. Motivazione obbligatoria su RIFIUTATA.
  async function registraEsito(id, { esito, motivazione }) {
    const res = await registraEsitoOfferta(id, { esito, motivazione })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // BOZZA o ACCETTATA -> ANNULLATA. Motivazione obbligatoria.
  async function annulla(id, { motivazione }) {
    const res = await annullaOfferta(id, { motivazione })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // EMESSA -> rev.N+1 (BOZZA). La fn DB marca la rev.N corrente come SUPERATA.
  async function creaRevisione(id) {
    const res = await creaRevisioneOfferta(id)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    // Emette anche per la nuova rev (la lista deve aggiornare entrambe).
    if (res.data.data?.id != null) {
      emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, res.data.data.id)
    }
    return res.data.data
  }

  // ACCETTATA -> ordine DRAFT (conversione §7.4, verbo DB
  // `fn_genera_ordine_da_offerta`). Ritorna { ordine_id, numero,
  // documento_origine }. Emette per il nuovo ordine (apre/refresh tab ordini).
  // Un'offerta genera al massimo un ordine vivo.
  async function generaOrdine(id) {
    const res = await generaOrdineFromOfferta(id)
    if (res.data.data?.ordine_id != null) {
      emitDataChanged(TAB_ENTITIES.ORDINE, res.data.data.ordine_id)
    }
    return res.data.data
  }

  // ACCETTATA -> contratto DRAFT (idempotente). Ritorna
  // { contratto_id, contratto_codice, sorgente_uid }.
  // `chiudiEsistente`: successione su overlap (chiude il contratto
  // sovrapposto prima di creare il nuovo). Default false: su overlap il BE
  // solleva E_CONTRATTO_OVERLAP_ESISTENTE (il drawer apre il dialog di
  // successione).
  async function pushAContratto(id, { praticaId = null, chiudiEsistente = false } = {}) {
    const res = await pushOffertaAContratto(id, { praticaId, chiudiEsistente })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    // Emette anche per il contratto generato (apre/refresh tab contratti).
    if (res.data.data?.contratto_id != null) {
      emitDataChanged(TAB_ENTITIES.CONTRATTO, res.data.data.contratto_id)
    }
    return res.data.data
  }

  // Contratto attivo sovrapposto al push (read-only). Alimenta il dialog di
  // successione quando il push fallisce con E_CONTRATTO_OVERLAP_ESISTENTE.
  // Ritorna l'oggetto contratto { id, numero, valido_dal, valido_al } o null.
  async function loadContrattoSovrapposto(id) {
    const res = await getContrattoSovrapposto(id)
    return res.data.data?.contratto ?? null
  }

  // --- Eccezioni ---

  async function addEccezione(offertaId, payload) {
    const res = await createEccezione(offertaId, payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, offertaId)
    return res.data.data
  }

  async function aggiornaEccezione(offertaId, eccezioneId, payload) {
    const res = await updateEccezione(offertaId, eccezioneId, payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, offertaId)
    return res.data.data
  }

  async function eliminaEccezione(offertaId, eccezioneId) {
    const res = await deleteEccezione(offertaId, eccezioneId)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, offertaId)
    return res.data.data
  }

  return {
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,
    // testata (utility 1:1 atomica via payload.utility inline)
    fetchDetail, create, update, elimina,
    // transizioni
    emetti, registraEsito, annulla, creaRevisione, pushAContratto,
    generaOrdine,
    loadContrattoSovrapposto,
    // eccezioni
    addEccezione, aggiornaEccezione, eliminaEccezione,
  }
}, {
  userScoped: true,
})
