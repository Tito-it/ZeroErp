// Scopo: Composable riusabile per il campo `emittente_fiscale_id` nei
//        drawer dell'area documenti (e potenzialmente altri).
//
//        Modello permessi 1-a-1 (refactor operatore-emittenti, vedi
//        commento in stores/auth.js: ogni operatore e' legato a UN solo
//        emittente fiscale, oppure e' admin globale senza emittente).
//        Quindi il campo NON e' una "scelta" per l'operatore standard:
//        e' derivato dal profilo. Solo l'admin globale deve davvero
//        scegliere fra N emittenti.
//
//        Comportamento:
//        - operatore con emittente -> il valore e' `auth.emittenteCorrente.id`,
//          la UI lo mostra come testo read-only ("codice - ragione sociale").
//          Niente combo: non c'e' scelta da fare.
//        - admin globale -> serve combo. Riusa `listEmittentiFiscali()`
//          (`/api/v1/amm-software/lookup/emittenti-fiscali/`, AdminAPIView):
//          essendo la combo visibile solo all'admin, il vincolo admin-only
//          dell'endpoint NON produce 403 a operatori (che non vedono la combo).
//
//        Il composable e' un "data provider": non scrive nella form. Spetta
//        al consumer applicare il default (autopopulate) e renderizzare il
//        markup giusto.

import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useGlobalLookup } from './useGlobalLookup'
import { listEmittentiFiscali } from '../../amministrazione/api/amministrazione'

// Chiave cache modulo-level. Coerente con altri lookup admin gia' usati.
const LOOKUP_KEY = 'amm.emittenti_fiscali'

// Scopo: Compone il label di una option lookup (admin combo).
//        Preferisce ragione_sociale (piu' parlante) e affianca il codice
//        come secondario, allineato al pattern degli altri Select wrapper
//        (es. IvaSelect: "descrizione (codice)").
export function formatEmittenteOptionLabel(opt) {
  if (!opt) return ''
  const main = opt.ragione_sociale || opt.descrizione || ''
  const codice = opt.codice || ''
  if (main && codice) return `${main} (${codice})`
  return main || codice || ''
}

export function useEmittenteFiscaleField() {
  const auth = useAuthStore()

  // Admin globale = nessun emittente personale -> serve combo.
  const isAdminMode = computed(() => auth.isAdminGlobale)

  // Emittente dell'operatore corrente (null per admin globale).
  const currentEmittente = computed(() => auth.emittenteCorrente)

  // Lookup admin (lazy: load() chiamato solo dove isAdminMode = true).
  // Cache modulo-level: invalidata al logout dal resetter centralizzato.
  const {
    items: emittentiOptions,
    loading: emittentiLoading,
    error: emittentiError,
    load: loadOptions,
  } = useGlobalLookup(LOOKUP_KEY, () => listEmittentiFiscali())

  // Default value per la form al primo apertura del drawer in create:
  // - operatore con emittente -> id derivato dal profilo (campo non
  //   sara' editabile, valore necessario per il payload BE);
  // - admin globale -> null, l'admin sceglie via Select.
  // Centralizza la logica di autopopulate: i drawer chiamano una sola
  // riga `form.emittente_fiscale_id = defaultEmittenteId.value` invece
  // di duplicare il branching.
  const defaultEmittenteId = computed(() => {
    if (isAdminMode.value) return null
    return currentEmittente.value?.id ?? null
  })

  return {
    isAdminMode,
    currentEmittente,
    defaultEmittenteId,
    emittentiOptions,
    emittentiLoading,
    emittentiError,
    loadOptions,
    formatEmittenteOptionLabel,
  }
}
