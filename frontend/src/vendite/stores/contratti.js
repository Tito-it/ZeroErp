// Store Pinia contratti v5. Lista + detail + CRUD testata + azioni righe + cambio stato.
// Filtro data obbligatorio (regola standard liste con date): floor `data_da`
// unico di progetto (oggi-60gg al primo del mese), vedi core/utils/date.
//
// ⭐ Dal 2026-09-18 la lista e' `useListaStoreCore`, chiamato qui dentro: era
//    una copia a mano del suo `buildParams` su `useListaEmptyStateFetch`. Non
//    passa da una factory perche' lo store e' anche righe, emissione
//    e cambio stato: la lista e' una parte.
import { defineStore } from 'pinia'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import {
  listContratti, getContratto, createContratto, updateContratto, cambiaStatoContratto,
  emettiContratto,
  addRigaContratto, updateRigaContratto, deleteRigaContratto,
} from '../api/contratti'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'
import { STATO_CONTRATTO } from '../constants'
import { avvisaDocumentiCollegati } from '../_shared/annullo/avvisoDocumentiCollegati'

const defaultDataDa = defaultFiltroDataDaString()

export const useContrattiStore = defineStore('vendite-contratti', () => {
  const { emitDataChanged } = useTabEvents()

  // Parte piena: questa lista si e' sempre caricata anche senza filtri (il
  // `fetchList` originale non aveva guardie di empty-state). Il default
  // `data_da` la popolerebbe comunque, ma dichiararlo evita che togliendo quel
  // default la lista diventi muta.
  const lista = useListaStoreCore({
    fetchPage: listContratti,
    startsEmpty: false,
    filterDefaults: {
      billing_account_id: null,
      stato_doc_contratto_id: null,
      utility_id: null,
      ambito: null,
      listino_id: null,
      data_da: defaultDataDa,
      data_a: null,
      scadenza_mese: null,
    },
    // Il piu' recente in cima. ⚠️ Il ripiego del verso resta `asc` (default
    // del core), com'era nella copia a mano: e' un ramo dormiente, e
    // un'estrazione appiana la duplicazione, non le differenze.
    orderBy: 'valido_dal',
    orderDir: 'desc',
  })

  async function fetchDetail(id) {
    const res = await getContratto(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createContratto(payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateContratto(id, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
    return res.data.data
  }

  // `validoAl` opzionale (ISO YYYY-MM-DD): cessazione atomica con data.
  // NB refactor 2026-05-28: DRAFT->ATTIVO non passa piu' da qui — usare
  // `emetti()` sotto (orchestra atomic state + documento + allegati via
  // ContrattoEmissioneDialog). Il BE rifiuta con E_VENDITE_VALIDAZIONE.
  // `dichiarazione`: la conferma dell'annullo con legami; l'annullo riapre i
  // documenti dall'altra parte (l'offerta torna trasformabile), e se ne
  // avvisano i tab.
  async function cambiaStato(id, codiceInterno, { validoAl = null, dichiarazione = {} } = {}) {
    const res = await cambiaStatoContratto(id, codiceInterno, { validoAl, dichiarazione })
    emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
    if (codiceInterno === STATO_CONTRATTO.ANNULLATO) avvisaDocumentiCollegati(emitDataChanged)
    return res.data.data
  }

  // DRAFT -> ATTIVO (multipart). Cambia stato + genera documento + allegati
  // in transazione atomica lato BE. Mirror del flusso offerta/preventivo.
  // Invocata dal ContrattoEmissioneDialog (ContrattoDrawer intercetta
  // l'action target_state='ATTIVO' e apre il dialog invece di cambiaStato).
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiContratto(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
    return res.data.data
  }

  // Righe
  async function addRiga(contrattoId, payload) {
    const res = await addRigaContratto(contrattoId, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }
  async function updateRiga(contrattoId, rigaId, payload) {
    const res = await updateRigaContratto(contrattoId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }
  async function deleteRiga(contrattoId, rigaId) {
    const res = await deleteRigaContratto(contrattoId, rigaId)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }

  return {
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,
    fetchDetail, create, update, cambiaStato, emetti,
    addRiga, updateRiga, deleteRiga,
  }
}, {
  // Reset automatico al logout (autoResetPlugin): items + filters dell'utente
  // non devono persistere per l'eventuale utente successivo sullo stesso browser.
  userScoped: true,
})
