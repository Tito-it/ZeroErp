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
//        Usa la ragione sociale del soggetto emittente e affianca il codice
//        come secondario, allineato al pattern degli altri Select wrapper
//        (es. IvaSelect: "descrizione (codice)").
//        Il vecchio fallback `|| opt.descrizione` e' stato tolto il 2026-08-02:
//        esisteva perche' una sola delle sorgenti (il record denormalizzato)
//        portava `emittenti_fiscali.descrizione`, e faceva mostrare allo stesso
//        campo due valori diversi a seconda del percorso. Ora TUTTE le sorgenti
//        (lookup admin, record denormalizzato, profilo operatore) portano la
//        ragione sociale del soggetto: il fallback era codice morto e teneva in
//        vita una colonna in via di eliminazione. Vedi
//        `brief-emittente-ragione-sociale-dal-soggetto.md`.
export function formatEmittenteOptionLabel(opt) {
  if (!opt) return ''
  const main = opt.ragione_sociale || ''
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

  // Default value per la form all'apertura del drawer in create: l'emittente su
  // cui la SESSIONE scrive.
  //
  // 🔴 CORRETTO IL 2026-09-02 (rilievo di Tid). Prima era
  //    `isAdminMode ? null : currentEmittente?.id`, cioe' guardava solo
  //    l'emittente di PERMESSO e per il super admin rispondeva `null` **anche
  //    dopo che aveva scelto** l'emittente di lavoro dalla topbar: il drawer gli
  //    ripresentava una scelta gia' fatta, con la combo vuota. Il difetto e'
  //    d'epoca — questo composable e' del modello 1-a-1 e l'impersonazione di
  //    scope (`emittente_attivo`) e' arrivata dopo, il 2026-08-04, senza che
  //    nessuno tornasse qui.
  // ⭐ La risposta ora sta in UN posto solo (`auth.emittenteScritturaId`), che
  //    e' l'unico modo perche' il drawer e la topbar non dicano due cose
  //    diverse sullo stesso emittente.
  // ⚠️ `null` resta possibile, e vuol dire «questa sessione non ha un emittente
  //    su cui scrivere» (super admin in «Tutti gli emittenti»). Non e' un caso
  //    da riempire con un default: e' lo stato in cui il verbo di creazione va
  //    spento — e sulle liste configurabili lo spegne gia' il cancello di
  //    perimetro (P-2b), che `useListaConfigurabilePage` propaga a TUTTE le
  //    azioni di pagina, «Nuovo» compreso.
  const defaultEmittenteId = computed(() => auth.emittenteScritturaId)

  // Scopo: la RIGA DEL LOOKUP che corrisponde all'emittente di scrittura della
  //        sessione — cioe' il posto dove stanno il suo nome, il suo codice e
  //        il suo `soggetto_ruolo_id`.
  //
  // ⭐ Estratto il 2026-09-02 alla seconda occorrenza: `EmittenteFiscaleField`
  //    la cercava per mostrarne l'etichetta, `CanaleIncassoDrawer` per
  //    ricavarne il soggetto-ruolo con cui chiede i conti. Due copie della
  //    stessa ricerca sullo stesso elenco: il giorno che una cambia chiave,
  //    due schermate dicono cose diverse sullo stesso emittente.
  // ⚠️ `null` finche' il lookup non e' arrivato (o se e' fallito): chi la usa
  //    non deve ripiegare su un altro emittente — deve non dire niente.
  const opzioneSessione = computed(() => {
    const id = defaultEmittenteId.value
    if (id == null) return null
    return (emittentiOptions.value || []).find((o) => o.id === id) ?? null
  })

  return {
    isAdminMode,
    currentEmittente,
    defaultEmittenteId,
    opzioneSessione,
    emittentiOptions,
    emittentiLoading,
    emittentiError,
    loadOptions,
    formatEmittenteOptionLabel,
  }
}
