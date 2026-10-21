<script setup>
// Scopo: FE-2 — il dialog che dichiara la DATA DOCUMENTO con cui numerare.
//   Serve i DUE perimetri dell'atto fiscale con un componente solo, perche' e'
//   la stessa domanda su due insiemi: un LOTTO (`lottoId`, dal drawer/lista) o
//   un MESE DI COMPETENZA (`competenzaMese`, dalla Dashboard Competenza, che
//   tocca N lotti e vuole UNA data per tutti — decisione 5 del brief).
//
// ⭐ PERCHE' ESISTE. Fino al 2026-08-25 la data della fattura era il
//   `current_date` del momento in cui era nata la BOZZA, e non si poteva
//   correggere da nessuna parte: un lotto rimasto indietro portava una data
//   vecchia, e numerandolo dopo lotti piu' recenti produceva un numero alto su
//   una data bassa. Dal cancello di `fn_get_next_progressivo` quel caso ora
//   viene RIFIUTATO — quindi senza questo dialog l'operatore avrebbe un rifiuto
//   e nessun modo di rimediare.
//
// ⛔ LA `minDate` NON E' UN ABBELLIMENTO. Sul registro Back-office la politica
//   e' `FINE_MESE_COMPETENZA`: ogni lotto di competenza ARRETRATA nasce con una
//   data anteriore all'ultimo numero emesso. Senza il pavimento a video il
//   dialog proporrebbe ogni volta una data che il DB rifiuta, e l'operatore
//   imparerebbe a leggere l'errore invece della targa.
//
// ⚠️ Il pavimento e' un SUGGERIMENTO, non una garanzia: la lettura e' fail-open
//   sotto RLS (una fattura fuori perimetro non entra nel massimo). Il rifiuto
//   vero resta del DB. Questo dialog non decide niente — mostra e chiede.
//
// Non conosce l'API di numerazione: riceve il verbo come prop `azione(data)` e
// lascia al chiamante la chiamata, i toast e il refresh (che sono suoi).
//
// ⭐ IL DIALOG RESTA APERTO FINO ALL'ESITO (2026-10-21, ok Tid). `azione`
//   risponde `true` se il verbo e' andato e `false` se no: solo col `true` il
//   dialog si chiude; intanto il pulsante gira. E' cio' che da' un confine al
//   GESTO dell'idempotenza (`useChiaveGesto`): un reinvio dopo un timeout
//   avviene QUI DENTRO, con la stessa key, e il backend risponde con l'esito
//   della prima esecuzione; chiudere e riaprire e' un gesto nuovo (chi apre il
//   dialog azzera la key). Prima il dialog si chiudeva al clic, e «riaprire»
//   e «riprovare» erano lo stesso gesto: a separarli restava solo il tempo.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'
import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { displayDate, parseIsoDate, toDateString } from '../../core/utils/date'
import { getFinestraNumerazione } from '../api/lotti'
import { MODO_DATA_DOCUMENTO } from '../constants'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'
import { DATE_FORMAT } from '../../core/constants'

const props = defineProps({
  visible: { type: Boolean, required: true },
  // ⭐ DUE MODI, e la differenza NON e' cosmetica.
  //   `numera`    — si sta per numerare: la data e' OBBLIGATORIA (si conferma
  //                 quella proposta) e confermare puo' SPOSTARE le date dei
  //                 documenti, quindi il dialog lo dice prima.
  //   `creazione` — si sta per creare i lotti: la data e' FACOLTATIVA, e
  //                 lasciarla vuota non vuol dire «oggi» — vuol dire «la
  //                 decide la politica del registro». ⛔ Qui NON si legge la
  //                 finestra di numerazione, ne' la data corrente ne' il
  //                 pavimento: parlano dei lotti GIA' esistenti, e sono la
  //                 risposta a un'altra domanda. Vedi `carica()`.
  // ⛔ `validator` e non solo un default: un refuso nel valore ricadrebbe in
  //    silenzio sul modo `numera`, che e' la direzione PERICOLOSA — il dialog
  //    di creazione pretenderebbe una data e annuncerebbe «niente da numerare»
  //    su lotti che non esistono ancora. Meglio un errore in console che una
  //    schermata che dice il falso.
  modo: {
    type: String,
    default: MODO_DATA_DOCUMENTO.NUMERA,
    validator: (v) => Object.values(MODO_DATA_DOCUMENTO).includes(v),
  },
  // Esattamente uno dei tre. Tutti vuoti = il dialog non chiede niente.
  lottoId: { type: [Number, null], default: null },
  competenzaMese: { type: [String, null], default: null },
  // ⭐ Il perimetro SELEZIONATO (lista Lotti). ⚠️ Il limite si ricalcola a ogni
  //   cambio di selezione — è nelle dipendenze del `watch` che chiama
  //   `carica()` — perché il pavimento è di ogni SEZIONALE: spuntare un lotto
  //   di un altro registro può spostarlo in avanti, e un limite calcolato una
  //   volta all'apertura sarebbe quello di una selezione che non esiste più.
  lotti: { type: Array, default: null },
  // ⭐ La frase del perimetro, quando il chiamante ne ha una piu' precisa della
  //   nostra. In creazione e' il PESO di cio' che sta per succedere — «3 gruppi,
  //   47 attivita'» — che prima stava nella conferma secca: assorbendo quella
  //   conferma, questo dialog deve assorbirne anche il testo, o l'operatore
  //   perderebbe l'informazione piu' importante delle due.
  perimetroTesto: { type: String, default: '' },
  // Il verbo: `async (dataDocumento) => boolean` (vedi la testa del file).
  azione: { type: Function, required: true },
})
const emit = defineEmits(['update:visible'])

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const dataScelta = ref(null)
const minima = ref(null)     // pavimento del sezionale (Date | null)
const corrente = ref(null)   // data che i documenti portano oggi (Date | null)
// ⛔ «CARICATO» E' UNO STATO SUO, e serve a non dire una bugia. Senza, una
//   lettura FALLITA e una lettura RIUSCITA CON PERIMETRO VUOTO sono
//   indistinguibili — entrambe lasciano `corrente` a null — e il dialog
//   annuncerebbe «non c'e' niente da numerare» su una chiamata che non ha
//   nemmeno risposto. Un errore travestito da dato tranquillo.
//   Copre anche il primo render, prima che `carica()` parta.
const caricato = ref(false)
// ⛔ QUANTI LOTTI L'ATTO TOCCHERA', e lo dice il SERVER — non il chiamante.
//   Sono due numeri diversi: una selezione puo' contenere lotti non piu'
//   numerabili (li ha presi un altro giro, un collega li ha resi definitivi), e
//   sul perimetro MESE il chiamante quel numero non ce l'ha proprio.
//   ⚠️ La prima versione lo riceveva come prop e la lista Lotti gli passava `0`
//   sull'atto di mese: il dialog annunciava «l'atto numera 0 lotti» mentre stava
//   per numerarli tutti.
const nLottiPerimetro = ref(0)

// Scopo: la data da proporre. Se quella che i documenti portano gia' va bene,
//   si propone QUELLA — confermare non cambia niente ed e' il caso normale.
//   Solo se e' sotto il pavimento si propone il pavimento, che e' il primo
//   giorno in cui quei documenti possono prendere un numero.
// ⚠️ Nessun ripiego su «oggi»: se non c'e' ne' una data corrente ne' un
//   pavimento non c'e' niente da numerare, e il dialog lo dice.
function proponi() {
  if (!corrente.value) return minima.value
  if (minima.value && corrente.value < minima.value) return minima.value
  return corrente.value
}

const inCreazione = computed(() => props.modo === MODO_DATA_DOCUMENTO.CREAZIONE)

async function carica() {
  dataScelta.value = null
  minima.value = null
  corrente.value = null
  nLottiPerimetro.value = 0
  caricato.value = false

  // ⛔ IN CREAZIONE NON SI LEGGE NIENTE, ed è la correzione di un difetto vero
  //   (Tid, 2026-08-26). La prima versione mostrava anche qui il pavimento, con
  //   la motivazione «un lotto creato oggi con una data indietro verrebbe
  //   rifiutato al momento di numerarlo, meglio saperlo adesso».
  //   **Quel ragionamento è sbagliato**, e il messaggio che produceva era
  //   falso: il pavimento è una proprietà di UN SEZIONALE, e alla creazione il
  //   sezionale dei lotti che nasceranno **non si sa ancora** — lo decide la
  //   coppia (tipo documento, natura) delle attività che entrano. Quello che
  //   l'endpoint restituisce per un mese di competenza è il massimo fra i
  //   pavimenti dei lotti GIÀ ESISTENTI, che con i nuovi non c'entrano nulla.
  //
  //   🔴 Misurato: fatturando un gruppo che finiva sul Back-office (serie
  //   `VX1`, mai numerata, nessun pavimento) il dialog annunciava «l'ultimo
  //   numero già emesso su questo registro porta la data 24/08/2026» — che è
  //   il pavimento del **Front-office** (`VX2`), un altro sezionale. Un vincolo
  //   inesistente, dichiarato con sicurezza, su cui una persona ha poi
  //   ragionato per mezz'ora.
  //
  //   ⚠️ Senza pavimento non c'è nemmeno un `minDate`: in creazione la data è
  //   facoltativa e qualunque valore è ammesso — il cancello vero la giudicherà
  //   al momento di numerare, quando il sezionale sarà noto.
  if (inCreazione.value) {
    caricato.value = true
    fotografia.fissa()
    return
  }

  if (props.lottoId == null && !props.competenzaMese && !props.lotti?.length) return
  const res = await execute(
    () => getFinestraNumerazione({
      lottoId: props.lottoId,
      competenzaMese: props.competenzaMese,
      lotti: props.lotti,
    }),
  )
  // `!== null`: una risposta con tutti i campi a null e' un esito legittimo
  // (niente da numerare), non un errore.
  // ⚠️ Niente `silent`: se la lettura fallisce l'operatore deve vederlo. Un
  //    dialog che si apre vuoto e in silenzio e' il modo in cui un guasto
  //    diventa «non c'era niente da fare».
  if (res === null) return
  caricato.value = true
  nLottiPerimetro.value = Number(res.n_lotti ?? 0)
  minima.value = res.data_minima ? parseIsoDate(res.data_minima) : null
  corrente.value = res.data_corrente ? parseIsoDate(res.data_corrente) : null
  dataScelta.value = proponi()
  fotografia.fissa()
}

// Ricarica all'apertura, e anche se il PERIMETRO cambia sotto.
// ⚠️ Oggi il secondo caso NON si verifica, ed è giusto saperlo invece di
//   crederlo: il dialog è modale e riceve una copia della selezione presa al
//   momento dell'apertura, quindi mentre è aperto nessuno può spuntare altro.
//   Il ricalcolo c'è perché il limite dipende dal perimetro e non dal momento —
//   se un domani il limite si mostrasse accanto alla lista, mentre si spunta,
//   questo watch è già la cosa giusta. Il commento precedente descriveva quel
//   comportamento come se accadesse già: non accadeva.
// ⛔ E il limite DIPENDE davvero dal perimetro: è di ogni sezionale, e spuntare
//   un lotto di un altro registro lo sposta in avanti.
// ⚠️ La chiave è la lista ORDINATA e serializzata, non l'array: due riferimenti
//   diversi con gli stessi id sono la stessa selezione e non devono ricaricare,
//   mentre gli stessi id in ordine diverso nemmeno — è un insieme.
watch(
  () => [props.visible, [...(props.lotti ?? [])].sort((a, b) => a - b).join(',')],
  ([visibile]) => { if (visibile) carica() },
)

// Confermare SPOSTA le date dei documenti (e con esse le scadenze): e' la
// conseguenza che l'operatore non si aspetta, e va detta prima, non dopo.
const spostaLeDate = computed(() => {
  if (!dataScelta.value || !corrente.value) return false
  return toDateString(dataScelta.value) !== toDateString(corrente.value)
})

// Solo nel modo `numera`: in creazione non c'e' niente da numerare per
// definizione, e dirlo sarebbe un avviso su una cosa che nessuno ha chiesto.
const nienteDaNumerare = computed(
  () => !inCreazione.value && caricato.value && !corrente.value,
)
// Lettura non riuscita: il dialog non sa niente e non deve fingere di sapere.
const nonCaricato = computed(() => !inCreazione.value && !loading.value && !caricato.value)

function onHide() { emit('update:visible', false) }

const inviando = ref(false)

async function conferma() {
  // ⚠️ In creazione il vuoto e' una risposta legittima — «non dichiaro niente,
  //    decida il registro» — e viaggia come `null`, non come la data di oggi.
  if (inviando.value || (!inCreazione.value && !dataScelta.value)) return
  inviando.value = true
  try {
    const ok = await props.azione(dataScelta.value ? toDateString(dataScelta.value) : null)
    if (ok === true) onHide()
  } finally {
    inviando.value = false
  }
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ dataScelta: dataScelta.value }), { visibile: () => props.visible, fissaAllApertura: false })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    width="sm"
    :header="t(inCreazione ? 'vendite.numerazione_data.titolo_creazione' : 'vendite.numerazione_data.titolo')"
    :loading="loading || inviando"
    :save-disabled="(!inCreazione && !dataScelta) || nienteDaNumerare || nonCaricato"
    :save-label="t(inCreazione ? 'vendite.numerazione_data.conferma_creazione' : 'vendite.numerazione_data.conferma')"
    save-severity="success"
    @update:visible="onHide"
    @save="conferma"
  >
    <!-- ⚠️ Perimetro e pavimento in UN messaggio, non in un paragrafo con una
         classe nuova: nel foglio comune non c'e' una classe «testo introduttivo
         di dialog», e inventarla qui vorrebbe dire aggiungere CSS a un
         componente invece che al foglio (feedback_css_centralizzazione). -->
    <Message v-if="nonCaricato" severity="warn" :closable="false">
      {{ t('vendite.numerazione_data.non_caricato') }}
    </Message>
    <Message v-else-if="nienteDaNumerare" severity="info" :closable="false">
      {{ t('vendite.numerazione_data.niente_da_numerare') }}
    </Message>
    <Message v-else-if="!loading" severity="info" :closable="false">
      <template v-if="perimetroTesto">{{ perimetroTesto }}</template>
      <template v-else-if="inCreazione">
        {{ t('vendite.numerazione_data.perimetro_creazione') }}
      </template>
      <template v-else-if="lottoId != null">
        {{ t('vendite.numerazione_data.perimetro_lotto') }}
      </template>
      <template v-else>
        {{ t('vendite.numerazione_data.perimetro_competenza', { n: nLottiPerimetro }) }}
      </template>
      <!-- ⚠️ Due frasi, perché i due perimetri NON dicono la stessa cosa: su un
           lotto il pavimento è di quel sezionale; su un mese è il PIÙ ALTO fra
           i sezionali che l'atto tocca. Dire «questo registro» nel secondo caso
           è la stessa imprecisione che in creazione era una bugia. -->
      <template v-if="minima">
        {{ ' ' }}{{ t(
          lottoId != null
            ? 'vendite.numerazione_data.pavimento'
            : 'vendite.numerazione_data.pavimento_perimetro',
          { data: displayDate(minima) },
        ) }}
      </template>
    </Message>

    <!-- ⛔ L'avviso che conta: confermando si SPOSTANO le date dei documenti e
         si RIGENERANO le scadenze. Chi non lo dice lo nasconde. -->
    <Message v-if="spostaLeDate" severity="warn" :closable="false">
      {{ t('vendite.numerazione_data.sposta_le_date', {
        da: displayDate(corrente),
        a: displayDate(dataScelta),
      }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t(inCreazione ? 'vendite.numerazione_data.campo_data_creazione' : 'vendite.numerazione_data.campo_data') }}</label>
        <DatePicker
          v-model="dataScelta"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          :min-date="minima || undefined"
          :disabled="nienteDaNumerare"
        />
      </div>
    </div>
  </AppDialog>
</template>
