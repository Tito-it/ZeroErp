<script setup>
// Scopo: Drawer RAPIDO delle code di lavoro (FE-3, brief gestione-code —
//        D-B): aperto dal badge top bar. Mostra lo stato dei worker drainer
//        («coda impegnata» vs «worker giù») e poi, per OGNI coda, il suo
//        blocco completo: conteggi vivi + le sue ultime righe.
//        Sola lettura: le azioni di governo (annulla/requeue/archivia) vivono
//        nella vista completa.
//
// ⭐ Dal 2026-09-04 le due code sono SIMMETRICHE (richiesta di Tid). Prima la
//    coda lavori aveva i conteggi qui e l'elenco delle sue ultime righe in
//    fondo, dopo i conteggi della stampa, e la coda stampa un elenco non ce
//    l'aveva affatto: chi leggeva doveva ricucire da sé che quelle righe erano
//    dei lavori e non delle stampe, e sulla stampa non aveva niente da leggere.
//    ⛔ Il difetto non era la disposizione: era che il pannello descriveva DUE
//    code con UNA struttura sola.
//
// ⭐ E il titolo di ogni sezione è il MODO di arrivarci: apre la vista completa
//    già sulla scheda di quella coda (deep-link `?tab=`). Da qui è sparito il
//    pulsante «Apri gestione completa», che portava sempre e comunque sulla
//    scheda di default — cioè faceva ripartire dalla coda sbagliata metà delle
//    volte.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'
import AppDrawer from './AppDrawer.vue'
import { useNotify } from '../composables/useNotify'
import { useDrawerClose } from '../composables/useDrawerClose'
import { extractApiError } from '../utils/apiError'
import { displayTimestamp } from '../utils/date'
import { formatFatturaNumero } from '../utils/format'
import { statoCodaLavoriSeverity, statoCodaStampaSeverity } from '../utils/severity'
import { CODE_TABS, DRAWER_WIDTH, MANAGE_ICONS, STATUS_ICONS } from '../constants'
import { NAV_ICONS } from '../navigation'
import { getCodeConteggi, listCodaLavori, listCodaStampa } from '../api/tracciamento'
import { STATI_CODA_VIVI, contaVivi, workerOkDaConteggi } from '../composables/useQueueCountsPolling'



const { t } = useI18n()
const notify = useNotify()
const router = useRouter()

const props = defineProps({
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible'])
const onClose = useDrawerClose(emit)

// Quante righe recenti per coda: è un'anteprima, non una lista — chi ne vuole
// di più apre la scheda dal titolo della sezione.
const RIGHE_RECENTI = 5

const conteggi = ref(null)
const ultimiJob = ref([])
const ultimeStampe = ref([])
const loading = ref(false)
// ⛔ `caricato` è vero solo dopo una lettura RIUSCITA, ed è ciò che autorizza
//    le frasi di vuoto («coda vuota», «nessun lavoro registrato»). Senza,
//    all'apertura — e per sempre se la chiamata fallisce — il pannello
//    dichiarerebbe che entrambe le code sono vuote: un all-clear su dati mai
//    arrivati, che è la cosa peggiore che possa dire un pannello di code.
//    Stessa regola di `DashEmptyState` sui cruscotti.
const caricato = ref(false)

// Stati mostrati come chip: sono gli stati VIVI, e l'elenco NON si riscrive
// qui — arriva da `STATI_CODA_VIVI`, la stessa sede che conta il badge in
// topbar, che le liste usano per la rotellina e che il trigger applica a
// database. Due letture della stessa coda che non concordano sono già state un
// difetto (2026-08-27).
// ⚠️ La chiave del payload dei conteggi è il codice in minuscolo (`PENDING` →
//    `pending`): è la convenzione del BE, la stessa su cui è scritto
//    `contaVivi`.
// ⚠️ Le label restano `t()` ESPLICITE — così il guard i18n le vede, che una
//    chiave composta a runtime non gliela farebbe vedere — con ripiego sul
//    CODICE grezzo: se un giorno un terzo stato entrasse in `STATI_CODA_VIVI`
//    senza la sua frase, si vedrebbe `IN_ATTESA_X` invece di una chip vuota.
const ETICHETTA_STATO_VIVO = computed(() => ({
  PENDING: t('strumenti.code.stato_pending'),
  IN_CORSO: t('strumenti.code.stato_in_corso'),
}))
const STATI_VIVI = computed(() => STATI_CODA_VIVI.map((codice) => ({
  codice,
  chiave: codice.toLowerCase(),
  label: ETICHETTA_STATO_VIVO.value[codice] ?? codice,
})))

// Predicati dalla fonte unica del polling (regola del 2: stessa definizione
// di «vivo» e «worker ok» del badge, mai due copie che possono divergere).
const workerOk = computed(() => workerOkDaConteggi(conteggi.value))
const codaImpegnata = computed(() =>
  (contaVivi(conteggi.value, 'coda_lavori') + contaVivi(conteggi.value, 'coda_stampa')) > 0,
)

// Le due code descritte con la STESSA forma, e rese da un solo blocco di
// template: sono gemelle (stessi stati, stessa nozione di «viva», stessa
// archiviazione un piano più sotto) e due blocchi quasi identici in questo
// file divergerebbero al primo che ne tocca uno.
// ⚠️ `righe` è già normalizzata a `{id, stato, testo, quando}`: la differenza
//    fra le due code sta in COME si nomina una riga — un job si nomina col
//    proprio tipo, una stampa con la sua FATTURA, che è ciò che l'operatore
//    sta guardando — e quella differenza vive nei due mapper qui sotto, non
//    nel template.
// ⚠️ `chiave` è il nome della coda nel payload dei conteggi, ed è scritto UNA
//    volta per sezione: serve sia a leggere i conteggi per stato sia a contare
//    i vivi con `contaVivi`, e ripeterlo nei due punti è il modo in cui un
//    giorno si finisce a leggere una coda e contarne un'altra.
const sezioni = computed(() => [
  {
    tab: CODE_TABS.LAVORI,
    chiave: 'coda_lavori',
    icona: NAV_ICONS.CODE_LAVORO,
    titolo: t('strumenti.code.coda_lavori'),
    severity: statoCodaLavoriSeverity,
    titoloRecenti: t('strumenti.code.ultimi_job'),
    vuotoRecenti: t('strumenti.code.nessun_job'),
    righe: ultimiJob.value.map((job) => ({
      id: job.id,
      stato: job.stato,
      testo: job.job_type,
      quando: job.started_at,
    })),
  },
  {
    tab: CODE_TABS.STAMPA,
    chiave: 'coda_stampa',
    icona: MANAGE_ICONS.STAMPA,
    titolo: t('strumenti.code.coda_stampa'),
    severity: statoCodaStampaSeverity,
    titoloRecenti: t('strumenti.code.ultime_stampe'),
    vuotoRecenti: t('strumenti.code.nessuna_stampa'),
    righe: ultimeStampe.value.map((riga) => ({
      id: riga.id,
      stato: riga.stato,
      testo: formatFatturaNumero(riga),
      quando: riga.data_update,
    })),
  },
].map((sez) => ({
  ...sez,
  conteggi: conteggi.value?.[sez.chiave] ?? null,
  vivi: contaVivi(conteggi.value, sez.chiave),
})))

// Scopo: carica conteggi + le ultime righe di ENTRAMBE le code (id/data DESC
//        dal BE, ambito proprio). Fail-visible.
//        SOLA LETTURA: nessun emit verso il topbar — il badge segue il suo
//        polling (un «changed» qui rifetcherebbe lo stesso endpoint appena
//        letto, innescando anche la race delle catene di polling).
async function load() {
  loading.value = true
  try {
    const [resConteggi, resJobs, resStampe] = await Promise.all([
      getCodeConteggi(),
      listCodaLavori({ limit: RIGHE_RECENTI, offset: 0 }),
      listCodaStampa({ limit: RIGHE_RECENTI, offset: 0 }),
    ])
    conteggi.value = resConteggi.data?.data ?? null
    ultimiJob.value = resJobs.data?.data?.results ?? []
    ultimeStampe.value = resStampe.data?.data?.results ?? []
    caricato.value = true
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => { if (v) load() })

// Scopo: apre la vista completa (Strumenti → Code di lavoro) sulla scheda
//        della coda su cui si è cliccato, e chiude il drawer.
// ⚠️ Si naviga per NOME di rotta, non per path: il path vive già in due sedi
//    (il router e `navigation.js`) e una terza copia qui si sfilerebbe in
//    silenzio il giorno che cambia — un `push` verso un indirizzo che non
//    esiste più non solleva, porta alla pagina «non trovato».
// ⚠️ Il drawer va chiuso a mano: la chiusura globale scatta sul cambio di
//    PATH, e da questa vista il path è lo stesso — cambia solo la query.
function apriCoda(tab) {
  onClose()
  router.push({ name: 'strumenti-code-lavoro', query: { tab } })
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md): la testata e' quella di
       tutti i drawer (`DrawerTitle` con l'icona delle code), non piu' la prop
       `header` di testo semplice. Sola lettura: footer «Chiudi». -->
  <AppDrawer
    :visible="visible"
    :title="t('strumenti.code.drawer_titolo')"
    :icon="NAV_ICONS.CODE_LAVORO"
    :width="DRAWER_WIDTH.SIMPLE"
    :proteggi-corpo="false"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- Stato worker: giù (nessun run recente) / coda impegnata / tutto scorre -->
    <Message v-if="workerOk === false" severity="warn" :closable="false">
      {{ t('strumenti.code.banner_worker_giu') }}
    </Message>
    <Message v-else-if="codaImpegnata" severity="info" :closable="false">
      {{ t('strumenti.code.banner_coda_impegnata') }}
    </Message>
    <Message v-else-if="conteggi" severity="success" :closable="false">
      {{ t('strumenti.code.banner_tutto_scorre') }}
    </Message>

    <!-- Un blocco per coda: titolo-comando, conteggi vivi, righe recenti. -->
    <div v-for="sez in sezioni" :key="sez.tab" class="app-code-sezione">
      <!-- ⚠️ È un CONTROLLO, non un titolo: pulsante vero (hit-area, focus da
           tastiera), colore e hover del «gestisci» blu dalla classe
           centralizzata, freccia a destra che dice dove porta. Un titolo che
           si può premere e non lo sembra non viene premuto.
           ⛔ `Button` di PrimeVue e non un <button> nudo: `.app-manage-btn` è
           definita come `.app-manage-btn.p-button` — su un elemento qualunque
           non applica niente, e il colore centralizzato sarebbe una classe
           dichiarata e mai letta. -->
      <Button
        text
        class="app-manage-btn app-code-sezione-titolo"
        v-tooltip.bottom="t('strumenti.code.apri_scheda_hint', { coda: sez.titolo })"
        @click="apriCoda(sez.tab)"
      >
        <i :class="sez.icona" />
        <span>{{ sez.titolo }}</span>
        <i class="app-code-sezione-vai" :class="MANAGE_ICONS.VAI_A" />
      </Button>

      <div class="app-code-chips">
        <!-- Finché la lettura è in volo non si afferma niente: né le chip
             (i conteggi non ci sono) né «coda vuota». -->
        <i v-if="loading" class="app-spinner-in-corso" :class="STATUS_ICONS.CARICAMENTO" />
        <template v-for="s in STATI_VIVI" :key="s.codice">
          <Tag
            v-if="(sez.conteggi?.[s.chiave] ?? 0) > 0"
            :value="`${s.label}: ${sez.conteggi[s.chiave]}`"
            :severity="sez.severity(s.codice)"
          />
        </template>
        <span v-if="caricato && sez.vivi === 0" class="app-text-muted">
          {{ t('strumenti.code.coda_vuota') }}
        </span>
      </div>

      <!-- Le ultime righe della coda, sotto i suoi conteggi: dicono COSA c'è
           dentro quel numero. La riga di titolo dice di che elenco si tratta:
           «vuota» parla dei vivi, questo elenco anche delle terminate, e
           senza l'etichetta i due si leggerebbero in contraddizione. -->
      <span class="app-code-recenti-titolo app-text-muted">
        {{ sez.titoloRecenti }}
      </span>
      <div v-if="sez.righe.length" class="app-code-jobs">
        <div v-for="riga in sez.righe" :key="riga.id" class="app-code-job">
          <Tag :value="riga.stato" :severity="sez.severity(riga.stato)" />
          <span class="app-mono app-code-job-tipo">{{ riga.testo }}</span>
          <span class="app-text-muted">
            {{ riga.quando ? displayTimestamp(riga.quando) : '—' }}
          </span>
        </div>
      </div>
      <span v-else-if="caricato" class="app-text-muted app-code-recenti-vuoto">
        {{ sez.vuotoRecenti }}
      </span>
    </div>
  </AppDrawer>
</template>

<style scoped>
.app-code-sezione {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--app-card-border);
}
/* Titolo-comando: sta nel flusso come un titolo, si comporta come un pulsante.
   Il colore e l'hover li porta `app-manage-btn` (blu «gestisci», sede unica in
   theme.css); qui restano solo larghezza, allineamento e peso del testo — un
   Button `text` di default centra il contenuto e si dimensiona sul contenuto. */
.app-code-sezione-titolo.p-button {
  width: 100%;
  justify-content: flex-start;
  gap: 0.5rem;
  padding: 0.25rem 0.35rem;
  font-weight: 600;
}
.app-code-sezione-vai {
  margin-left: auto;
  font-size: 0.85em;
}
.app-code-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.app-code-jobs {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.app-code-job {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.app-code-job-tipo {
  font-size: 0.85em;
}
.app-code-recenti-titolo,
.app-code-recenti-vuoto {
  font-size: 0.85em;
}
</style>
