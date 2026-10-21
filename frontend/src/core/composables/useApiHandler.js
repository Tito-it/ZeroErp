// Composable per chiamate API con gestione automatica errori e notifiche toast.
// Tutti i componenti di dominio devono usare questo invece di chiamare api.js direttamente.
//
// Uso:
//   const { execute, loading } = useApiHandler()
//   const data = await execute(() => api.get('/vendite/fatture/'), {
//     successMessage: t('notifications.save_success'),
//     errorMessage: t('notifications.generic_error')
//   })
//
// Campi in errore (dal 2026-08-08): il backend, quando lo sa, dice QUALI campi
// del form l'operatore deve correggere (envelope `error.fields`, api.md).
//
//   const { execute, campiErrati } = useApiHandler()
//   <InputText v-model="form.codice" :invalid="campiErrati.includes('codice')" />
//
// Prima esisteva solo il messaggio nel toast: l'operatore leggeva «campo
// obbligatorio» e doveva cercarselo. Il nome arriva dal service, quindi vale
// anche per le regole che il frontend non conosce.
// ⚠️ Si azzera a ogni `execute`: descrive l'ultimo errore, non la storia del
// drawer. Un campo resta rosso finche' non si riprova a salvare.
//
// ⭐ BERSAGLI (dal 2026-08-24): l'ALTRA META' della stessa idea. `campiErrati`
// dice quale campo correggere DENTRO la pagina dove l'operatore gia' si trova;
// i bersagli dicono a quale ALTRA cosa deve andare (envelope `error.targets`,
// forma `[{type, id}]`). E la differenza e' tutto il punto: il primo evidenzia
// un input, il secondo fa comparire un GESTO — «Apri la fattura 820».
//
// ⚠️ Il gesto NON va disegnato dal chiamante: lo compone questo composable e lo
// consegna al toast, cosi' che i 122 file che usano `execute` lo abbiano senza
// una riga di modifica. `bersagli` resta esposto per chi ha una superficie
// propria dove metterlo (il pannello degli esiti, l'icona di riga).
// Brief: docs/it/dev/work-in-progress/brief-db-bersaglio-errore.md §7-bis.
//
// ⭐ SOLUZIONE (dal 2026-09-09): la TERZA meta', ed e' quella che mancava.
// `campiErrati` dice quale campo correggere, `bersagli` a quale altra cosa
// andare — la soluzione dice **cosa fare adesso** (envelope `error.hint`). E'
// la frase che il team DB scrive a catalogo per ogni codice e che
// `script.fn_log_and_raise_error` consegna nel canale HINT dell'eccezione:
// «Numerare prima i documenti che questo rettifica, poi ripetere».
//
// ⛔ Fino a quel giorno era il caso di scuola che `api.md` descrive di suo
// pugno — *un campo dichiarato e mai letto sembra presidiato e non presidia
// niente*: il database la scriveva, il backend la trasportava con cinque punti
// di traduzione allineati e un BB dedicato, e lo schermo la buttava.
// ⚠️ Stessa regola del gesto: la mette a video QUESTO composable, non il
// chiamante — sotto il messaggio, nel `detail` del toast.

import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useNotify } from './useNotify'
import { estraiBersagli } from '../bersagli'
import { azioniDaBersagli } from '../bersaglioGesto'

// Codici che NON producono un toast, perche' a video c'e' gia' una schermata
// che dice la stessa cosa meglio: due messaggi identici, di cui uno rosso,
// fanno sembrare guasto quello che e' solo una scelta da fare.
//
// ⚠️ Sopprime il TOAST, non l'errore: `execute` ritorna `null` come sempre e
//    la chiamata resta fallita. Deve restare CORTISSIMA: un codice qui dentro
//    non si vede piu', e se la schermata che lo spiega cambia il rifiuto
//    diventa silenzioso. Presidiata da
//    `apps/core/tests/test_perimetro_emittente_copertura.py` (i codici devono
//    esistere a catalogo).
//
// ⚠️ `Set` e non un oggetto: `MAPPA[codice]` eredita dal prototipo, quindi un
//    codice chiamato `toString` risulterebbe «presente».
const CODICI_SENZA_TOAST = new Set([
  // Cancello di perimetro emittente (P-2b): `<ListaConfigurabile>` mostra gia'
  // il pannello «scegli un emittente» al posto della tabella.
  // ⭐ Si sopprime QUI e non evitando la chiamata nei caller perche' la config
  //    (che porta `richiede_scelta_emittente`) arriva DOPO che la fetch e'
  //    partita — si caricano in parallelo: evitarla del tutto vorrebbe dire
  //    far ASPETTARE ogni lista la config di un componente figlio.
  //    Dalla config in poi la lista si sospende da se'
  //    (`store.fetchSospesa`, in `useListaConfigurabilePage`), quindi qui
  //    passa la PRIMA chiamata e nessun'altra.
  'E_UI_LISTA_EMITTENTE_DA_SCEGLIERE',
])

export function useApiHandler() {
  const loading = ref(false)
  const notify = useNotify()
  // ⚠️ Si legge QUI, nel setup, e non dentro il `catch`: serve al degrado del
  // bersaglio (area BLOCCATA → nessun pulsante), e `useAuthStore()` fuori dal
  // setup dipenderebbe dalla pinia attiva globale.
  const auth = useAuthStore()
  // Campi del form che il backend indica come da correggere (envelope: `fields`),
  // e come suggerisce di reagire (`ui_action`). Si azzerano a ogni chiamata: si
  // riferiscono all'ULTIMO errore, non alla storia del drawer.
  const campiErrati = ref([])
  const azioneUi = ref(null)
  // Su QUALE cosa l'errore e' successo. Stesse regole di `campiErrati`: si
  // azzera a ogni chiamata, si popola anche in `silent`.
  const bersagli = ref([])
  // ⭐ La FRASE dell'ultimo errore, gia' estratta dall'envelope. Serve a chi
  // deve RENDERLA da se' invece che nel toast — il caso e' il rifiuto
  // confermabile, dove il messaggio del database porta i numeri («restano X da
  // regolare: un importo di Y non ci rientra») e va dentro la richiesta di
  // conferma. ⚠️ Senza questo, quel chiamante dovrebbe riscriversi
  // `extractErrorMessage` coi suoi tre ripieghi: una seconda sede.
  const messaggioErrore = ref(null)
  // ⭐ La SOLUZIONE dell'ultimo errore (envelope `hint`): cosa fare adesso.
  // Stesse regole degli altri: si azzera a ogni `execute`, si popola anche in
  // `silent`. Esposta per chi ha una superficie propria dove renderla — il
  // toast la mette gia' da se'.
  const soluzione = ref(null)

  /**
   * Esegue una chiamata API con gestione errori/toast automatica.
   *
   * @param {Function} apiFn - funzione che restituisce la Promise axios (es. () => api.get(...))
   * @param {Object} options
   * @param {string} [options.successMessage] - messaggio toast su successo (null = nessun toast)
   * @param {string} [options.errorMessage] - messaggio fallback se il backend non restituisce dettagli
   * @param {boolean} [options.silent] - true = nessun toast di errore (utile per polling)
   * @param {string[]} [options.azioniGestite] - `ui_action` che il chiamante gestisce
   *        da se' (es. `['confirm_and_retry']`): su quelle il toast non parte, il
   *        resto della gestione errori resta invariata
   * @returns {*} data interna dall'envelope { data, meta } in caso di successo, null in caso di errore
   */
  async function execute(apiFn, options = {}) {
    loading.value = true
    campiErrati.value = []
    azioneUi.value = null
    bersagli.value = []
    messaggioErrore.value = null
    soluzione.value = null
    try {
      const response = await apiFn()
      if (options.successMessage) {
        notify.success(options.successMessage)
      }
      // Unwrap dell'envelope standard backend { data: {...}, meta: {...} }.
      // Se apiFn ritorna gia' un payload unwrapped (es. action store),
      // preservalo invece di trattarlo come response Axios.
      const body = response && typeof response === 'object' && 'data' in response
        ? response.data
        : response
      return (body && typeof body === 'object' && 'data' in body) ? body.data : body
    } catch (err) {
      // ⭐ L'envelope si legge UNA VOLTA SOLA. Prima del 2026-09-09 questo blocco
      //    ripeteva `err.response?.data?.error?...` per ogni campo, e ogni campo
      //    nuovo ne aggiungeva una copia: quattro allora, cinque con la
      //    soluzione. ⛔ E' la stessa forma che il backend ha smesso di avere
      //    quando ha estratto `diagnostica_db` — li' i punti di lettura erano
      //    cinque e ognuno leggeva un sottoinsieme diverso. Qui la catena e'
      //    una, e i campi si prendono da lei.
      // ⚠️ `extractErrorMessage` resta su `err` di proposito: e' l'unico che
      //    guarda anche FUORI da `error` (`data.detail` di DRF, `data.error`
      //    come stringa nuda), quindi non e' un lettore dell'envelope standard —
      //    e' il ripiego per chi quell'envelope non lo produce.
      const errore = err.response?.data?.error
      // Si leggono anche in modalita' `silent` — il chiamante puo' voler
      // evidenziare senza far comparire un toast.
      campiErrati.value = estraiCampi(errore)
      azioneUi.value = errore?.ui_action ?? null
      bersagli.value = estraiBersagli(errore)
      const codice = errore?.code
      messaggioErrore.value = extractErrorMessage(err) ?? await messaggioStatoProxy(err)
      // ⚠️ Il filtro sta a MONTE, non qui: `_apply_policy` toglie l'`hint` sui
      //    tre codici tecnici, dove quel canale non porta una soluzione a
      //    catalogo ma il testo che PostgreSQL scrive per lo sviluppatore.
      //    Ri-decidere qui sarebbe una seconda sede della stessa regola, e le
      //    due divergerebbero al primo codice nuovo.
      soluzione.value = estraiSoluzione(errore) ?? await soluzioneDiRipiego(azioneUi.value)
      // ⭐ Il chiamante puo' dichiarare di gestire da se' UNA CLASSE di
      // comportamento (`ui_action`), e allora il toast non parte: il caso e' il
      // rifiuto CONFERMABILE (`confirm_and_retry`), che non e' un fallimento ma
      // una domanda — un banner rosso direbbe la cosa sbagliata.
      // ⛔ Si dichiara l'`ui_action`, MAI un elenco di codici: il frontend
      //    riconosce il comportamento e resta cieco ai codici (Q-1 del brief
      //    incassi). Al terzo codice, un elenco se lo dimentica qualcuno.
      // ⚠️ E non si usa `silent` per ottenere lo stesso effetto: `silent` spegne
      //    il toast per QUALUNQUE errore, quindi il chiamante dovrebbe
      //    ri-decidere da se' fra errore di sistema, gesto e toast normale —
      //    cioe' riscrivere questa scelta altrove.
      const gestitoDalChiamante =
        Array.isArray(options.azioniGestite) &&
        azioneUi.value != null &&
        options.azioniGestite.includes(azioneUi.value)
      if (!options.silent && !gestitoDalChiamante && !CODICI_SENZA_TOAST.has(codice)) {
        const message = messaggioErrore.value || options.errorMessage
        const isSystem = isSystemError(err)
        // ⭐ Il gesto, quando c'e' qualcosa da raggiungere. `azioniDaBersagli`
        // scarta da se' i bersagli irraggiungibili (tipo senza destinazione,
        // area bloccata): un array vuoto = toast di prima, nessuna regressione.
        // ⚠️ Un toast CON azioni resta aperto finche' non lo si chiude: un
        // gesto che sparisce dopo cinque secondi non e' un gesto.
        const azioni = azioniDaBersagli(bersagli.value, auth)
        if (isSystem) {
          notify.systemError(message, soluzione.value)
        } else if (azioni.length) {
          notify.errorConAzioni(message, azioni, soluzione.value)
        } else {
          notify.error(message, soluzione.value)
        }
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { execute, loading, campiErrati, azioneUi, bersagli, messaggioErrore, soluzione }
}

// I due estrattori prendono l'oggetto `error` dell'envelope — non l'eccezione —
// come fa gia' `estraiBersagli`: la catena opzionale la percorre il chiamante,
// una volta sola, e questi restano funzioni pure sul contratto.

// Estrae i nomi dei campi da correggere dall'envelope: { error: { fields: [...] } }.
// Il backend manda i NOMI e mai i valori (api.md §Envelope risposte).
function estraiCampi(errore) {
  const campi = errore?.fields
  return Array.isArray(campi) ? campi.filter(c => typeof c === 'string') : []
}

// Estrae la SOLUZIONE dall'envelope: { error: { hint: "..." } }.
// ⚠️ Stringa e non vuota, o niente: il backend la omette quando non c'e'
//    (una chiave presente e vuota direbbe «guardami» senza dire niente), ma un
//    ripiego che si fida di un contratto e' un ripiego che il contratto lo
//    presidia — qui costa una riga.
function estraiSoluzione(errore) {
  const hint = errore?.hint
  return typeof hint === 'string' && hint.trim() ? hint : null
}

// Risposte che arrivano da NGINX, non da Django: niente envelope, e quindi
// nessun messaggio da leggere. Senza questo ripiego il toast mostrava un errore
// generico, e l'operatore non sapeva che cosa correggere.
// ⭐ 413 (2026-10-01, rilievo di Tid): un file sopra `client_max_body_size` si
//    ferma in Nginx PRIMA di Django — nel log del backend non resta niente, e
//    l'unico punto che puo' dire «il file e' troppo grande» e' questo.
// ⚠️ Il testo NON scrive il limite in MB: il numero vive nel vhost
//    (configurazione-django.md) e nei parametri `documenti_*_upload_max_mb`, e
//    una terza copia qui sarebbe la prima a diventare falsa.
const MESSAGGI_STATO_PROXY = {
  413: 'errors.http_413_file_troppo_grande',
}

// Scopo: Il messaggio di uno stato del proxy, quando l'envelope non ne porta
//        uno. `null` per ogni altro stato: resta il ripiego del chiamante.
// ⚠️ `i18n` si carica QUI, pigro, e non in cima al modulo: `core/i18n` legge
//    `localStorage` mentre viene valutato, e ogni file che importa questo
//    composable — anche un test senza DOM — lo pagherebbe senza usarlo.
async function messaggioStatoProxy(err) {
  const chiave = MESSAGGI_STATO_PROXY[err.response?.status]
  if (!chiave) return null
  const { default: i18n } = await import('../i18n')
  return i18n.global.t(chiave)
}

// ⭐ La SOLUZIONE di ripiego di un COMPORTAMENTO (`ui_action`), quando
//    l'envelope non ne porta una (2026-10-21). Il caso e' `show_retry_dialog`:
//    il backend lo dichiara su un conflitto momentaneo (`E_DATABASE_RETRYABLE`)
//    e su una richiesta con la stessa key ancora in corso
//    (`E_IDEMPOTENCY_IN_PROGRESS`, il reinvio di un gesto: `useChiaveGesto`),
//    e in entrambi la cosa da fare e' la stessa — aspettare e riprovare, senza
//    paura di raddoppiare: la transazione e' stata annullata, oppure la key
//    restituira' l'esito della prima.
// ⚠️ Vince sempre l'`hint` del backend: questo copre solo il suo silenzio, e
//    si dichiara il COMPORTAMENTO, mai un codice (il frontend resta cieco ai
//    codici, come per `azioniGestite`).
const SOLUZIONI_AZIONE_UI = {
  show_retry_dialog: 'errors.soluzione_riprova_fra_poco',
}

async function soluzioneDiRipiego(azione) {
  // `hasOwn`: `MAPPA[azione]` erediterebbe dal prototipo (`toString`).
  const chiave = azione && Object.hasOwn(SOLUZIONI_AZIONE_UI, azione) ? SOLUZIONI_AZIONE_UI[azione] : null
  if (!chiave) return null
  const { default: i18n } = await import('../i18n')
  return i18n.global.t(chiave)
}

// Estrae il messaggio di errore dall'envelope backend { error: { code, message } }
function extractErrorMessage(err) {
  const data = err.response?.data
  if (!data || typeof data !== 'object') return null

  // Envelope standard: { error: { code, message } }
  if (data.error?.message) return data.error.message

  // Envelope semplificata: { error: "stringa" }
  if (typeof data.error === 'string') return data.error

  // DRF default: { detail: "..." }
  if (data.detail) return data.detail

  return null
}

// Errori di sistema: 500+, network error, timeout
function isSystemError(err) {
  if (!err.response) return true
  return err.response.status >= 500
}
