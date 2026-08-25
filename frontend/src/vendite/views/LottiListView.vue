<script setup>
// Scopo: Registro dei giri di fatturazione (cockpit Fase B, B-2). Lista dei
//        lotti con filtri competenza/stato, scope emittente applicato dal BE
//        (RLS + get_scope_user_id). Non è il percorso quotidiano: serve per le
//        eccezioni (errori, reset, recuperi) e per il gate fiscale. Il click
//        apre il LottoDrawer diagnostico (step corrente, fatture, task-run,
//        segnalazioni) con le azioni di governo. Nessuna logica di dominio:
//        stato/step/gate vivono nel motore, la lista rende e naviga.
import { ref, computed, nextTick, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { registraDrawerChiudibile } from '../../core/composables/useDrawerChiusuraGlobale'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import DashMesiSidebar from '../../core/components/dash/DashMesiSidebar.vue'
import DashMeseStepper from '../../core/components/dash/DashMeseStepper.vue'
import LottiLista from '../components/LottiLista.vue'
import LottoDrawer from '../components/LottoDrawer.vue'
import NumerazioneDataDialog from '../components/NumerazioneDataDialog.vue'
import FatturazioneEsitiPanel from '../components/FatturazioneEsitiPanel.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useListaDrawerPaginata } from '../../core/composables/useListaDrawerPaginata'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Message from 'primevue/message'
import { useLottoAzioni } from '../composables/useLottoAzioni'
import { useDashMesiNav } from '../../core/composables/useDashMesiNav'
import { extractApiError } from '../../core/utils/apiError'
import { READONLY_DOMAINS } from '../../core/constants'
import { exportLotti, listLotti, listLottiMensile } from '../api/lotti'
import { useLottiStore } from '../stores/lotti'

const { t } = useI18n()
const notify = useNotify()
// Servono al deep-link `?open=<id>` (vedi `applicaDeepLink` piu' sotto).
const route = useRoute()
const router = useRouter()
// Il valore serve anche qui, non solo ai figli: in sola lettura il kebab di
// riga non propone azioni di governo (il BE resta il guard vero).
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.VENDITE)
const store = useLottiStore()

// Filtro stato lotto (select statico sui valori di dominio; una nuova voce si
// mostra comunque via fail-visible).
const statoFilter = ref(null)

// Navigazione anno/mese — stesso telaio della Lente Competenza (BB condiviso
// useDashMesiNav + DashMesiSidebar): anno in alto, 12 mesi sotto. C'è SEMPRE un
// mese selezionato (niente "tutti i mesi": lo storico si naviga con le frecce
// anno). Default = mese corrente, la competenza che si sta fatturando.
const oggi = new Date()
const anno = ref(oggi.getFullYear())
const meseIdx = ref(oggi.getMonth())

// `onMeseChange`/`onAnnoChange` sono dichiarazioni di funzione (hoisted): il
// telaio le riceve qui ma le invoca solo su interazione.
const { nomiMesi, competenzaCorrente, selezionaMese, cambiaAnno, stepMese } = useDashMesiNav({
  anno,
  meseIdx,
  onMeseChange: onFilterChange,
  onAnnoChange: loadMensile,
})

// Competenza in formato API (YYYY-MM-01): è già la forma di competenzaCorrente,
// condivisa da lista ed esiti (unica derivazione, non possono divergere).
const competenzaParam = computed(() => competenzaCorrente.value)

// Conteggi lotti/mese dell'anno per il badge della sidebar: mappa
// competenza→n. I 12 mesi sono SEMPRE presenti (0-riempiti) e reattivi
// all'anno, così la sidebar non "lampeggia" vuota prima della fetch.
const conteggiMese = ref({})
const mesi = computed(() =>
  Array.from({ length: 12 }, (_, m) => {
    const cm = `${anno.value}-${String(m + 1).padStart(2, '0')}-01`
    return { competenza_mese: cm, n_lotti: conteggiMese.value[cm] ?? 0 }
  })
)

const statoOptions = computed(() => [
  { value: 'DRAFT', label: t('vendite.lotti.stato_draft') },
  { value: 'IN_ESECUZIONE', label: t('vendite.lotti.stato_in_esecuzione') },
  { value: 'COMPLETATO', label: t('vendite.lotti.stato_completato') },
  { value: 'ERRORE', label: t('vendite.lotti.stato_errore') },
])

// Scaffolding della lista configurabile (useSearchTable + export + pageActions).
// L'export riceve gli STESSI filtri della lista: il file rispecchia ciò che si
// sta guardando, ordinamento incluso.
const {
  onPage, onSort, paginatorProps, tablePage, reload,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
  perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportLotti,
  getExportParams: (fmt) => {
    const p = { formato: fmt }
    if (store.filters.competenza_mese) p.competenza_mese = store.filters.competenza_mese
    if (store.filters.stato_lotto) p.stato_lotto = store.filters.stato_lotto
    if (store.filters.order_by) {
      p.order_by = store.filters.order_by
      p.order_dir = store.filters.order_dir || 'desc'
    }
    return p
  },
})

// ⭐ LA SCHEDA «RECUPERI DEL MESE»: i lotti di competenza PRECEDENTE che hanno
//    emesso documenti nel mese filtrato. Non passa dallo store — è una seconda
//    domanda sulla stessa lista, non un secondo stato della pagina.
// ⚠️ `useListaDrawerPaginata` e non `useListaConfigurabilePage`: quest'ultimo
//    pretende uno store con la forma «ricerca + sort + limit», e qui lo store
//    non c'è. È lo stesso caso per cui quel BB è nato (una lista pilotata da un
//    contesto esterno) — il nome dice «drawer» solo perché lì è stato estratto.
const schedaAttiva = ref('lotti')

// Scopo: inoltra a `listaRef` l'istanza di `<ListaConfigurabile>` che
//        `<LottiLista>` espone, invece del wrapper.
// 🔴 Difetto pagato il 2026-08-24: con `ref="listaRef"` sul componente estratto
//    il ref puntava al WRAPPER, e `useListaConfigurabilePage` calcola
//    `configReady` come `lista.value?.config != null` — che sul wrapper è
//    sempre `null`. Effetto: «Personalizza colonne» **disabilitato**, senza
//    nessun errore da nessuna parte. È lo stesso tipo di difetto del nome di
//    slot sbagliato: tutto corretto tranne dove punta un riferimento.
// ⚠️ Si ascolta l'ANNUNCIO del figlio (`@lista-pronta`) e non si LEGGE un ref:
//    leggere significa leggere UNA volta sola, e un `null` in quell'istante
//    resterebbe tale per sempre — con l'unico sintomo di un pulsante
//    disabilitato. L'annuncio arriva dall'`onMounted` del figlio, quando la
//    lista e' certamente montata: nessuna ipotesi sull'ordine.
function registraLista(istanza) {
  listaRef.value = istanza ?? null
}
// Stesso meccanismo della scheda sopra, e per la stessa ragione: un solo modo
// di consegnare l'istanza, nessun caso che si affidi a un accesso tracciato
// attraverso il proxy di `defineExpose`.
const listaRecuperiRef = ref(null)
function registraListaRecuperi(istanza) {
  listaRecuperiRef.value = istanza ?? null
}
const listaRecuperi = useListaDrawerPaginata(({ page, pageSize, sortBy, sortDir }) =>
  listLotti({
    competenza_mese: store.filters.competenza_mese,
    // ⚠️ ANCHE `stato_lotto`: la scheda si ricarica al cambio filtro, ma senza
    // questo si ricaricherebbe IDENTICA — e un filtro che si muove sopra una
    // lista che non cambia si legge come un filtro rotto (rilievo di Tid,
    // 2026-08-24). I filtri della pagina sono due: mese e stato, e valgono per
    // entrambe le schede.
    ...(store.filters.stato_lotto ? { stato_lotto: store.filters.stato_lotto } : {}),
    recuperi_mese: true,
    page,
    page_size: pageSize,
    ...(sortBy ? { order_by: sortBy, order_dir: sortDir } : {}),
  }))

// Personalizza colonne + esporta anche sulla seconda scheda: è una lista come
// le altre. ⚠️ `?.lista`: `useListaAzioni` vuole l'istanza di
// `<ListaConfigurabile>`, che `<LottiLista>` espone.
const azioniRecuperi = useListaAzioni(() => listaRecuperiRef.value, {
  exportFn: exportLotti,
  getExportParams: (fmt) => ({
    formato: fmt,
    competenza_mese: store.filters.competenza_mese,
    // Il file È la lista, quindi porta ENTRAMBI i filtri della pagina: senza
    // `recuperi_mese` esporterebbe i lotti del mese, senza `stato_lotto`
    // esporterebbe tutti gli stati mentre a video se ne vede uno.
    ...(store.filters.stato_lotto ? { stato_lotto: store.filters.stato_lotto } : {}),
    recuperi_mese: true,
    ...(listaRecuperi.sortField.value
      ? {
          order_by: listaRecuperi.sortField.value,
          order_dir: listaRecuperi.sortOrder.value === -1 ? 'desc' : 'asc',
        }
      : {}),
  }),
})

// Scopo: carica la lista con toast d'errore (fail-visible: lo store propaga).
async function load() {
  try {
    await store.fetchList()
    // ⚠️ Anche la seconda scheda, e insieme alla prima: il CONTEGGIO sta
    // nell'etichetta, e un'etichetta che dice «(0)» finché non la si apre è
    // peggio di nessun conteggio. ⛔ Best-effort: se i recuperi non arrivano,
    // la lista principale si vede lo stesso.
    listaRecuperi.page.value = 1
    listaRecuperi.carica().catch(() => {})
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: conteggi lotti/mese dell'anno per il badge della sidebar. Fotografia
//        completa (nessun filtro stato): indipendente dai filtri di lista.
async function loadMensile() {
  try {
    const res = await listLottiMensile(anno.value)
    const map = {}
    for (const m of res.data?.data?.mesi ?? []) map[m.competenza_mese] = m.n_lotti
    conteggiMese.value = map
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: riversa i filtri della view (mese dalla sidebar, stato dal select)
//        nello store, che è la sola fonte che il BB legge. Il reset a pagina 1
//        avviene SOLO se un filtro è davvero cambiato: su una riattivazione
//        senza cambi (rientro nel tab) l'operatore deve ritrovare la SUA
//        pagina, non la prima — stessa filosofia del refresh idempotente di
//        useSearchTable («offset invariato, cambia solo il contenuto righe»).
function syncFiltri() {
  const competenza = competenzaParam.value
  const stato = statoFilter.value
  if (store.filters.competenza_mese !== competenza || store.filters.stato_lotto !== stato) {
    store.filters.competenza_mese = competenza
    store.filters.stato_lotto = stato
    store.filters.offset = 0
  }
}

// Scopo: cambio mese/filtro stato → lista da pagina 1 (il badge non cambia:
//        è la fotografia dell'anno, ricaricata solo al cambio anno).
function onFilterChange() {
  syncFiltri()
  load()
}

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro nel tab (feedback_keepalive_onactivated).
// ⚠️ useSearchTable registra il PROPRIO onActivated (refresh idempotente
// sulle riattivazioni) PRIMA di questo, quindi sulle riattivazioni il suo
// fetch è già in volo quando arriviamo qui: il guard su `store.loading`
// evita il doppio fetch concorrente. Al primo mount invece il suo hook si
// auto-salta (firstActivation) ed è QUESTO a fare il fetch iniziale.
onActivated(() => {
  syncFiltri()
  if (!store.loading) load()
  loadMensile()
  applicaDeepLink()
})

// Drawer diagnostico.
const drawerVisible = ref(false)
// Le sole due liste che tengono a mano lo stato del drawer invece di passare da
// `useDrawerState`: si registrano da se' nella chiusura globale, o resterebbero
// gli unici due pannelli a sopravvivere a un cambio di pagina.
registraDrawerChiudibile(() => { drawerVisible.value = false })

const drawerLottoId = ref(null)

// Scopo: accesso alla riga con il click, come le liste standard. Il kebab
//        (tolto il 2026-07-31, quando l'unica azione era «apri», cioè lo stesso
//        gesto) torna il 2026-08-04 con le azioni di governo: la colonna
//        `azioni` del catalogo è stata riattivata dal team DB.
function apriLotto(row) {
  drawerLottoId.value = row.id
  drawerVisible.value = true
}

// ⭐ DEEP-LINK `?open=<id>`: la lista apre direttamente il lotto indicato.
// Nasce per il BERSAGLIO di un errore (2026-08-24) — il pulsante «Apri Lotto
// 6034» di un toast o di un'icona di riga arriva qui — ma e' il meccanismo
// generico gia' in servizio su `vendite-contratti`, non un canale suo.
//
// ⚠️ In `onActivated` e non in un `watch immediate`, ed e' la differenza che
// conta su questa view: sta sotto KeepAlive, quindi tornarci NON rimonta il
// setup. Un `watch` sulla query funzionerebbe al primo ingresso e poi
// silenziosamente piu' (feedback_keepalive_onactivated).
// ⚠️ Il param si ripulisce subito: senza, un refresh della pagina riaprirebbe
// il pannello che l'operatore aveva appena chiuso.
function applicaDeepLink() {
  const grezzo = route.query.open
  if (!grezzo) return
  const id = Number(grezzo)
  const query = { ...route.query }
  delete query.open
  router.replace({ query })
  if (!Number.isFinite(id) || id <= 0) return
  nextTick(() => apriLotto({ id }))
}

// Azioni di riga: stesso composable del drawer — conferme, chiamate e testi
// stanno in una sede sola. La lista non ha il blob capability (scelta del team
// DB: nessuna lista del progetto lo consuma per riga), quindi il kebab propone
// i verbi PLAUSIBILI per lo stato della riga e la verifica vera avviene al
// click, leggendo la capability di quel lotto: se il DB dice no, l'operatore
// legge il motivo invece di veder fallire l'azione.
const {
  azioniRiga,
  loading: azioniLoading,
  // FE-2: stato del dialog della data, dal composable condiviso col drawer.
  numeraDialog,
  confermaNumera,
} = useLottoAzioni({
  onDone: async () => {
    await load()
    await loadMensile()
  },
})

// Azioni di pagina: quelle standard del BB (reload / personalizza / export).
// Niente «Nuovo» — un lotto non si crea da qui, lo genera la pipeline: lo
// scaffolding lo omette da sé, non ricevendo `onNew`.
// Unico adattamento: «Ricarica» aggiorna ANCHE i badge per-mese della sidebar,
// che il BB non conosce — la fotografia dell'anno deve restare coerente con la
// lista.
const azioniPagina = computed(() =>
  pageActions.value.map((a) => (a.key === 'reload'
    ? { ...a, command: () => { reload(); loadMensile() } }
    : a)),
)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('vendite.lotti.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('vendite.lotti.page_description') }}</small>
      </div>
      <PageActionsBar :actions="azioniPagina">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-dash-layout">
      <!-- Pannello laterale anno + 12 mesi (BB condiviso con la Lente
           Competenza): badge = numero lotti generati nel mese. -->
      <DashMesiSidebar
        :anno="anno"
        :mesi="mesi"
        :mese-idx="meseIdx"
        :nomi-mesi="nomiMesi"
        @seleziona-mese="selezionaMese"
        @cambia-anno="cambiaAnno"
      >
        <template #badge="{ idx }">
          <span
            v-if="mesi[idx].n_lotti > 0"
            class="app-dash-mese-lotti"
            v-tooltip.right="t('vendite.lotti.mese_lotti', { n: mesi[idx].n_lotti })"
          >
            <i class="pi pi-server" /> {{ mesi[idx].n_lotti }}
          </span>
        </template>
      </DashMesiSidebar>

      <div class="app-dash-main">
        <!-- Stepper compatto anno/mese (BB condiviso): solo piccoli schermi. -->
        <DashMeseStepper
          :anno="anno"
          :mese-idx="meseIdx"
          :nomi-mesi="nomiMesi"
          @step="stepMese"
        >
          <template #badge>
            <span v-if="mesi[meseIdx].n_lotti > 0" class="app-dash-mese-lotti">
              <i class="pi pi-server" /> {{ mesi[meseIdx].n_lotti }}
            </span>
          </template>
        </DashMeseStepper>

        <!-- Esiti fatturazione (C-5): stato coda stampa + giri del mese
             selezionato. La competenza è la STESSA della lista: pannello e
             lista raccontano lo stesso periodo. -->
        <FatturazioneEsitiPanel :competenza-mese="competenzaParam" />

        <div class="app-page-toolbar">
          <div class="app-page-filters" :inert="perimetroBloccato">
            <div class="form-field">
              <label>{{ t('vendite.lotti.filtro_stato') }}</label>
              <Select
                v-model="statoFilter"
                :options="statoOptions"
                option-label="label"
                option-value="value"
                show-clear
                :placeholder="t('common.all')"
                @update:model-value="onFilterChange"
              />
            </div>
          </div>
        </div>

        <!-- Colonne, ordine e visibilità arrivano dal catalogo `vendite.lotti`:
             qui restano solo le celle che hanno un rendering proprio. Le altre
             (documento, utility, area geografica, creato, creato da) le rende il
             BB dal `formato` del catalogo. -->
        <!-- ⭐ DUE SCHEDE (decisione di Tid, 2026-08-24). La seconda esiste
             perché una commessa di competenza GIUGNO fatturata ad AGOSTO
             produce un documento con data agosto dentro un lotto di giugno:
             chi lavora sul mese di agosto non lo trova, perché lo cerca —
             giustamente — per la data del documento e non per la competenza
             della commessa.
             ⚠️ Stesso componente in entrambe: stesse colonne, stesse azioni per
             costruzione. -->
        <Tabs v-model:value="schedaAttiva">
          <TabList>
            <Tab value="lotti">{{ t('vendite.lotti.tab_lotti_mese') }}</Tab>
            <Tab value="recuperi">
              {{ t('vendite.lotti.tab_recuperi') }}
              <template v-if="listaRecuperi.totale.value"> ({{ listaRecuperi.totale.value }})</template>
            </Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="lotti">
              <LottiLista
                @lista-pronta="registraLista"
                :rows="store.items"
                :total="store.totalRecords"
                :loading="store.loading"
                :paginator-options="paginatorProps"
                :page="tablePage"
                :sort-field="paginatorProps.sortField"
                :sort-order="paginatorProps.sortOrder"
                :build-row-actions="(data) => azioniRiga(data, { readonly: isReadonly })"
                :azioni-disabled="azioniLoading"
                @page="onPage"
                @sort="onSort"
                @row-click="apriLotto"
                @config-loaded="onConfigLoaded"
              />
            </TabPanel>

            <TabPanel value="recuperi">
              <!-- ⚠️ La riga che spiega la scheda: senza, un elenco di lotti di
                   giugno dentro la pagina filtrata su agosto si legge come un
                   filtro che non ha funzionato. -->
              <Message severity="secondary" :closable="false" class="app-mb-1">
                {{ t('vendite.lotti.recuperi_lista_nota') }}
              </Message>
              <!-- Personalizza colonne + esporta anche qui: è una lista come le
                   altre, e l'export porta con sé il filtro della scheda. -->
              <div class="app-page-toolbar">
                <span class="app-page-filters" />
                <PageActionsBar :actions="azioniRecuperi.azioniLista.value">
                  <template #suffix>
                    <ListaConfigStatusTag :dirty="azioniRecuperi.dirty.value" />
                  </template>
                </PageActionsBar>
              </div>
              <LottiLista
                @lista-pronta="registraListaRecuperi"
                :rows="listaRecuperi.righe.value"
                :total="listaRecuperi.totale.value"
                :loading="listaRecuperi.loading.value"
                :paginator-options="listaRecuperi.paginatorOptions.value"
                :page="listaRecuperi.page.value"
                :sort-field="listaRecuperi.sortField.value"
                :sort-order="listaRecuperi.sortOrder.value"
                :build-row-actions="(data) => azioniRiga(data, { readonly: isReadonly })"
                :azioni-disabled="azioniLoading"
                empty-key="vendite.lotti.nessun_recupero_lista"
                empty-icon="pi pi-history"
                @page="listaRecuperi.onPage"
                @sort="listaRecuperi.onSort"
                @row-click="apriLotto"
                @config-loaded="listaRecuperi.onConfigLoaded"
              />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </div>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <!-- Dialog di export della seconda scheda: separato perché i filtri sono
         diversi, e un dialog solo esporterebbe la lista sbagliata. -->
    <ExportDialog
      v-model:visible="azioniRecuperi.exportDialogVisible.value"
      :loading="azioniRecuperi.exportLoading.value"
      @export="azioniRecuperi.onExportConfirm"
    />

    <LottoDrawer
      v-model:visible="drawerVisible"
      :lotto-id="drawerLottoId"
      @changed="load"
    />

    <!-- FE-2: stesso dialog del drawer, stesso stato: il kebab della lista e la
         barra del drawer non possono chiedere la data in due modi diversi. -->
    <NumerazioneDataDialog
      v-model:visible="numeraDialog.visible"
      :lotto-id="numeraDialog.lottoId"
      @conferma="confermaNumera"
    />
  </div>
</template>

<style scoped>
.app-lotto-stato-cella {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
/* Rosso dal token PrimeVue, mai un esadecimale a mano: e' la convenzione gia'
   in uso per le spie di stato (`CodaStampaTab`). */
.app-lotto-spia-errore {
  color: var(--p-red-500);
}
/* Badge "numero lotti generati" nel mese (sidebar/stepper anno-mese). Neutro:
 * è un conteggio informativo, non un allarme (diverso dai badge errori/fermi
 * della Lente Competenza). */
.app-dash-mese-lotti {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
</style>
