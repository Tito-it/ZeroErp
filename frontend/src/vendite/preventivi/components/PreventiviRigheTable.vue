<script setup>
// Scopo: Sezione master-detail inline righe preventivo (Fase 3.F3).
//        Tabella sopra + form sotto nello stesso drawer, niente Dialog
//        annidato (pattern coerente con ContrattoRigheDrawer / VersioneDrawer,
//        frontend-standards §Master-detail inline).
//        Le righe si caricano dall'endpoint /righe/ autonomo (Fase 3.F6:
//        il detail preventivo non le embedda piu', solo righe_count).
//        Modifica = click riga; azioni secondarie (elimina) in RowActionsMenu
//        kebab.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { usePreventiviStore } from '../stores/preventivi'
import { MANAGE_ICONS } from '../../../core/constants'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import { coerceJsonbToObject } from '../../../core/utils/meta'
import { STATO_APPROVAZIONE } from '../../constants'
import PreventiviRigaForm from './PreventiviRigaForm.vue'
import PreventiviRigaComponentiPanel from './PreventiviRigaComponentiPanel.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  // Refactor cascata 2026-05-15: propaga al PreventiviRigaForm per la
  // cascata soglie L2 con livello categoria_cliente del BA.
  billingAccountId: { type: Number, default: null },
  isModificabile: { type: Boolean, default: true }
})

// Eventi:
//  - `changed`: dopo create/update/delete riga (parent ricarica detail).
//  - `form-aperto`: emesso quando il form inline (master-detail) cambia
//    stato. Il drawer parent (PreventiviDrawer) lo usa per nascondere
//    il proprio DrawerFooter Salva/Annulla testata durante edit-riga,
//    evitando duplicazione (stesso pattern distinta base BoM
//    `ArticoloBomDrawer.isFormOpen`).
const emit = defineEmits(['changed', 'form-aperto'])

const righe = ref([])
const loadingRighe = ref(false)
// formMode: null (nessun form attivo), 'create', 'edit'. Pattern master-detail
// inline (frontend-standards): governa visibilita' e comportamento del form
// sottostante senza apertura di Dialog annidato.
const formMode = ref(null)
watch(formMode, (m) => emit('form-aperto', m !== null))
const rigaSelezionata = ref(null)
// Selezione riga DataTable: evidenzia visivamente la riga in edit (pattern
// ContrattoRigheDrawer). Sincronizzata con rigaSelezionata.
const selezione = ref(null)
// Expander componenti BoM CASO A (refactor 2026-05-11): mappa {rigaId: true}
// per le righe espanse. PrimeVue DataTable usa data-key per la chiave: qui id
// e' int, quindi mappa object-style. Lo chevron e' visibile solo per righe
// con is_composito_caso_a=true (flag derivato dal BE list_righe via EXISTS
// subquery — evita N+1 fetch lato client).
const expandedRows = ref({})

function isExpanded(data) {
  return !!expandedRows.value[data.id]
}

// Scopo: toggle manuale espansione riga. Usiamo un Column custom + button al
//        posto del Column expander standard di PrimeVue per nascondere lo
//        chevron sulle righe non composite (UX: lo chevron-where-nothing-
//        happens confonde l'operatore).
function toggleExpansion(data) {
  const next = { ...expandedRows.value }
  if (next[data.id]) delete next[data.id]
  else next[data.id] = true
  expandedRows.value = next
}
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: loadRighe,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('preventivi.aggiungi_riga'),
    icon: MANAGE_ICONS.ADD,
    visible: props.isModificabile,
    command: onNuovaRiga,
  },
])

// Scopo: Carica righe dal backend (endpoint /righe/ autonomo, Fase 3.F6).
async function loadRighe() {
  if (!props.preventivoId) return
  loadingRighe.value = true
  try {
    righe.value = await store.loadRighe(props.preventivoId)
  } finally {
    loadingRighe.value = false
  }
}

watch(() => props.preventivoId, loadRighe, { immediate: true })

// Scopo: Attiva form in modalita' create (rimuove eventuale selezione corrente).
function onNuovaRiga() {
  rigaSelezionata.value = null
  selezione.value = null
  formMode.value = 'create'
}

// Scopo: Attiva form in modalita' edit per la riga passata.
function onEditRiga(riga) {
  rigaSelezionata.value = riga
  selezione.value = riga
  formMode.value = 'edit'
}

// Scopo: Chiude il form (annulla o post-save) e deseleziona la riga.
function chiudiForm() {
  formMode.value = null
  rigaSelezionata.value = null
  selezione.value = null
}

// Scopo: Salva riga (crea o aggiorna): chiude form + ricarica lista +
//        notifica il parent (totale_* aggregato lato DB ricalcolato).
async function onRigaSaved() {
  chiudiForm()
  await loadRighe()
  emit('changed')
}

// Scopo: Mutation su un componente BoM CASO A (PATCH prezzo o DELETE):
//        ricarica le righe per riflettere il nuovo prezzo padre calcolato
//        dai trigger DB (SUM componenti × coeff_qta), MA NON chiude il form
//        — l'operatore puo' continuare a editare altri componenti.
//        Propaga `changed` al parent (drawer) per refresh totali aggregati.
async function onComponentiChanged() {
  await loadRighe()
  emit('changed')
}

// Scopo: Elimina riga con conferma. Se sto editando proprio questa riga,
//        chiude il form. Notifica il parent post-reload riga.
function onDeleteRiga(riga) {
  confirmAction({
    message: t('preventivi.conferma_elimina_riga'),
    onAccept: async () => {
      const result = await execute(
        () => store.eliminaRiga(props.preventivoId, riga.id),
        { successMessage: t('preventivi.riga_eliminata') }
      )
      if (rigaSelezionata.value?.id === riga.id) chiudiForm()
      await loadRighe()
      if (result !== null) emit('changed')
    }
  })
}

// Scopo: severity Tag per stato approvazione prezzo (workflow L3 Sprint E).
// Mappa coerente: PENDING=warn (in corso), APPROVED=success, REJECTED=danger.
function approvazioneSeverity(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return 'success'
  if (stato === STATO_APPROVAZIONE.REJECTED) return 'danger'
  return 'warn'  // PENDING
}

function approvazioneLabel(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return t('preventivi.badge_approvazione_approved')
  if (stato === STATO_APPROVAZIONE.REJECTED) return t('preventivi.badge_approvazione_rejected')
  return t('preventivi.badge_approvazione_pending')
}

// Tooltip contestuale al tag di stato approvazione. Per REJECTED leggiamo la
// motivazione denormalizzata in `meta.approvazione_rifiuto.motivazione`
// (popolata da approvazioni_prezzo_service.rifiuta()): cosi' l'operatore
// vede subito *perche'* il responsabile ha rifiutato senza navigare alla
// pratica. Per PENDING torna il riferimento alla pratica come prima.
function approvazioneTooltip(data) {
  if (data.stato_approvazione_prezzo === STATO_APPROVAZIONE.REJECTED) {
    // Coerce difensivo: meta puo' arrivare come stringa JSON (regressione
    // adapter psycopg) → senza, il tooltip resta vuoto e l'operatore vede
    // "Rifiutato" senza motivo.
    const meta = coerceJsonbToObject(data.meta)
    const rif = meta.approvazione_rifiuto || {}
    if (rif.motivazione) {
      return t('preventivi.badge_approvazione_rejected_tooltip', {
        motivazione: rif.motivazione,
      })
    }
    return t('preventivi.badge_approvazione_rejected_no_motivo')
  }
  if (data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING && data.pratica_approvazione_prezzo_id) {
    return t('preventivi.badge_approvazione_pending_tooltip', {
      pratica_id: data.pratica_approvazione_prezzo_id,
    })
  }
  return ''
}

// Scopo: costruisce le azioni di riga (kebab) per RowActionsMenu. La modifica
//        non e' qui: avviene via click riga (frontend-standards).
//        Una riga con approvazione PENDING blocca elimina (lo blocca anche il
//        backend via guard, ma il FE evita il round-trip).
function buildRowActions(riga) {
  return [
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: props.isModificabile,
      disabled: riga?.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING,
      command: () => onDeleteRiga(riga),
    },
  ]
}

// Scopo: handler click riga -> apre dialog edit. Usa @row-click DataTable.
function onRowClick(event) {
  if (!props.isModificabile) return
  onEditRiga(event.data)
}

defineExpose({ loadRighe })
</script>

<template>
  <div>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h4 style="margin: 0;">{{ t('preventivi.section_righe') }}</h4>
      </div>
      <PageActionsBar :actions="pageActions" />
    </div>

    <DataTable :value="righe" striped-rows size="small" class="app-datatable app-datatable--inner"
      data-key="id"
      :loading="loadingRighe"
      :row-hover="isModificabile"
      :selection-mode="isModificabile ? 'single' : null"
      v-model:selection="selezione"
      v-model:expanded-rows="expandedRows"
      paginator
      :rows="10"
      :rows-per-page-options="[10, 25, 50]"
      paginator-position="top"
      sort-field="descrizione"
      :sort-order="1"
      removable-sort
      @row-click="onRowClick">
      <!-- Expander custom per componenti BoM CASO A: chevron visibile solo
           dove `is_composito_caso_a=true`. @click.stop evita che il click
           apra anche il drawer di edit della riga. -->
      <Column style="width: 2.5rem;" :exportable="false">
        <template #body="{ data }">
          <Button v-if="data.is_composito_caso_a"
            :icon="isExpanded(data) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
            text rounded size="small"
            v-tooltip.top="t('preventivi.componenti_section_title')"
            @click.stop="toggleExpansion(data)" />
        </template>
      </Column>
      <Column field="articolo_codice" :header="t('preventivi.riga_articolo')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('preventivi.riga_descrizione')" sortable />
      <Column field="quantita" :header="t('preventivi.riga_quantita')" sortable style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('preventivi.riga_uom')" style="width: 70px;" />
      <Column field="prezzo_unitario" :header="t('preventivi.riga_prezzo')" sortable style="width: 130px;">
        <template #body="{ data }">
          <div style="display: flex; flex-direction: column; gap: 0.15rem; align-items: flex-start;">
            <span>{{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 6, maximumFractionDigits: 6 }) }}</span>
            <Tag
              v-if="data.stato_approvazione_prezzo"
              :severity="approvazioneSeverity(data.stato_approvazione_prezzo)"
              :value="approvazioneLabel(data.stato_approvazione_prezzo)"
              v-tooltip.top="approvazioneTooltip(data)"
            />
          </div>
        </template>
      </Column>
      <Column field="sconto_percentuale" :header="t('preventivi.riga_sconto')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_percentuale ? `${data.sconto_percentuale}%` : '' }}</template>
      </Column>
      <Column field="importo_riga" :header="t('preventivi.riga_importo')" sortable style="width: 120px;">
        <template #body="{ data }">{{ formatCurrency(data.importo_riga) }}</template>
      </Column>
      <Column field="iva_descrizione" :header="t('preventivi.riga_iva')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.iva_descrizione || data.iva_codice || '' }}</template>
      </Column>
      <Column v-if="isModificabile" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
      <!-- Sub-tabella componenti BoM CASO A — read-only nell'expander.
           L'edit fine dei prezzi componente avviene nel form dettaglio riga
           (click sulla riga → PreventiviRigaForm con sezione componenti edit). -->
      <template #expansion="{ data }">
        <div style="padding: 0.25rem 0 0.5rem 2rem; background: var(--app-table-stripe-bg);">
          <PreventiviRigaComponentiPanel
            :preventivo-id="preventivoId"
            :riga-id="data.id"
            :readonly="true" />
        </div>
      </template>
    </DataTable>

    <!-- Form master-detail inline (Fase 3.F3): visibile SOLO quando attivo,
         titolo dipende da formMode. PreventiviRigaForm gia' espone Salva/Annulla
         interni nel proprio template (no DrawerFooter perche' e' una sezione,
         non un drawer). -->
    <div v-if="formMode" class="app-drawer-section" style="margin-top: 1rem;">
      <h4>{{ formMode === 'edit' ? t('preventivi.modifica_riga') : t('preventivi.nuova_riga') }}</h4>
      <PreventiviRigaForm
        :preventivo-id="preventivoId"
        :billing-account-id="billingAccountId"
        :riga="rigaSelezionata"
        @saved="onRigaSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="chiudiForm"
      />
    </div>
  </div>
</template>
