<script setup>
// Scopo: Registro dei giri di fatturazione (cockpit Fase B, B-2). Lista dei
//        lotti con filtri competenza/stato, scope emittente applicato dal BE
//        (RLS + get_scope_user_id). Non è il percorso quotidiano: serve per le
//        eccezioni (errori, reset, recuperi) e per il gate fiscale. Il click
//        apre il LottoDrawer diagnostico (step corrente, fatture, task-run,
//        segnalazioni) con le azioni di governo. Nessuna logica di dominio:
//        stato/step/gate vivono nel motore, la lista rende e naviga.
import { ref, computed, onActivated } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import DashMesiSidebar from '../../core/components/dash/DashMesiSidebar.vue'
import DashMeseStepper from '../../core/components/dash/DashMeseStepper.vue'
import LottoDrawer from '../components/LottoDrawer.vue'
import FatturazioneEsitiPanel from '../components/FatturazioneEsitiPanel.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useLottoAzioni } from '../composables/useLottoAzioni'
import { useDashMesiNav } from '../../core/composables/useDashMesiNav'
import { extractApiError } from '../../core/utils/apiError'
import { READONLY_DOMAINS } from '../../core/constants'
import { statoLottoSeverity } from '../../core/utils/severity'
import { exportLotti, listLottiMensile } from '../api/lotti'
import { useLottiStore } from '../stores/lotti'

const { t } = useI18n()
const notify = useNotify()
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

// Scopo: carica la lista con toast d'errore (fail-visible: lo store propaga).
async function load() {
  try {
    await store.fetchList()
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
})

// Drawer diagnostico.
const drawerVisible = ref(false)
const drawerLottoId = ref(null)

// Scopo: accesso alla riga con il click, come le liste standard. Il kebab
//        (tolto il 2026-07-31, quando l'unica azione era «apri», cioè lo stesso
//        gesto) torna il 2026-08-04 con le azioni di governo: la colonna
//        `azioni` del catalogo è stata riattivata dal team DB.
function apriLotto(row) {
  drawerLottoId.value = row.id
  drawerVisible.value = true
}

// Azioni di riga: stesso composable del drawer — conferme, chiamate e testi
// stanno in una sede sola. La lista non ha il blob capability (scelta del team
// DB: nessuna lista del progetto lo consuma per riga), quindi il kebab propone
// i verbi PLAUSIBILI per lo stato della riga e la verifica vera avviene al
// click, leggendo la capability di quel lotto: se il DB dice no, l'operatore
// legge il motivo invece di veder fallire l'azione.
const { azioniRiga, loading: azioniLoading } = useLottoAzioni({
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
          <div class="app-page-filters">
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
        <ListaConfigurabile
          ref="listaRef"
          codice="vendite.lotti"
          :rows="store.items"
          :total="store.totalRecords"
          :loading="store.loading"
          :paginator-options="paginatorProps"
          :page="tablePage"
          :sort-field="paginatorProps.sortField"
          :sort-order="paginatorProps.sortOrder"
          @page="onPage"
          @sort="onSort"
          @row-click="apriLotto"
          @config-loaded="onConfigLoaded"
        >
          <template #cell-codice="{ data }">
            <strong>{{ data.codice }}</strong>
          </template>
          <template #cell-tipo_lotto="{ data }">
            <Tag :value="data.tipo_lotto" severity="secondary" />
          </template>
          <template #cell-stato_lotto="{ data }">
            <Tag :value="data.stato_lotto" :severity="statoLottoSeverity(data.stato_lotto)" />
          </template>
          <!-- Stato operativo: informazione interna della pipeline, resa come
               Tag neutro — non è uno stato di dominio come `stato_lotto` e non
               deve competere con lui a colpo d'occhio. -->
          <template #cell-stato_operativo="{ data }">
            <Tag v-if="data.stato_operativo" :value="data.stato_operativo" severity="secondary" />
            <span v-else>—</span>
          </template>
          <template #cell-stato_doc_fiscale="{ data }">
            <Tag
              v-if="data.stato_doc_fiscale_descrizione"
              :value="data.stato_doc_fiscale_descrizione"
              severity="info"
            />
            <span v-else>—</span>
          </template>

          <!-- Azioni di governo del lotto senza passare dal drawer: avanza /
               rilancia step, rendi definitive, ristampa, annulla, riporta in
               lavorazione. Le voci proposte dipendono dallo stato della riga;
               il verdetto vero (e il motivo di un rifiuto) arriva dal DB al
               click — vedi useLottoAzioni. -->
          <template #actions="{ data, compact }">
            <RowActionsMenu
              :row="data"
              :actions="azioniRiga(data, { readonly: isReadonly })"
              :disabled="azioniLoading"
              :force-compact="compact"
            />
          </template>

          <template #empty>
            <div class="app-empty-state">
              <i class="pi pi-server" />
              <p>{{ t('vendite.lotti.nessun_lotto') }}</p>
            </div>
          </template>
        </ListaConfigurabile>
      </div>
    </div>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <LottoDrawer
      v-model:visible="drawerVisible"
      :lotto-id="drawerLottoId"
      @changed="load"
    />
  </div>
</template>

<style scoped>
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
