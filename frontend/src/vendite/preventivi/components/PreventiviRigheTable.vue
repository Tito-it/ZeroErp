<script setup>
// Scopo: Sezione master-detail inline righe preventivo (Fase 3.F3).
//        Tabella sopra + form sotto nello stesso drawer, niente Dialog
//        annidato (pattern coerente con ContrattoRigheDrawer / VersioneDrawer,
//        frontend-standards §Master-detail inline).
//        Le righe si caricano dall'endpoint /righe/ autonomo (Fase 3.F6:
//        il detail preventivo non le embedda piu', solo righe_count).
//        Modifica = click riga; azioni secondarie (elimina) in RowActionsMenu
//        kebab.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { usePreventiviStore } from '../stores/preventivi'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import PreventiviRigaForm from './PreventiviRigaForm.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import NewButton from '../../../core/components/NewButton.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  isModificabile: { type: Boolean, default: true }
})

const righe = ref([])
// formMode: null (nessun form attivo), 'create', 'edit'. Pattern master-detail
// inline (frontend-standards): governa visibilita' e comportamento del form
// sottostante senza apertura di Dialog annidato.
const formMode = ref(null)
const rigaSelezionata = ref(null)
// Selezione riga DataTable: evidenzia visivamente la riga in edit (pattern
// ContrattoRigheDrawer). Sincronizzata con rigaSelezionata.
const selezione = ref(null)

// Scopo: Carica righe dal backend (endpoint /righe/ autonomo, Fase 3.F6).
async function loadRighe() {
  if (!props.preventivoId) return
  righe.value = await store.loadRighe(props.preventivoId)
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

// Scopo: Salva riga (crea o aggiorna): chiude form + ricarica lista.
async function onRigaSaved() {
  chiudiForm()
  await loadRighe()
}

// Scopo: Elimina riga con conferma. Se sto editando proprio questa riga, chiude il form.
function onDeleteRiga(riga) {
  confirmAction({
    message: t('preventivi.conferma_elimina_riga'),
    accept: async () => {
      await execute(
        () => store.eliminaRiga(props.preventivoId, riga.id),
        { successMessage: t('preventivi.riga_eliminata') }
      )
      if (rigaSelezionata.value?.id === riga.id) chiudiForm()
      await loadRighe()
    }
  })
}

// Scopo: severity Tag per stato approvazione prezzo (workflow L3 Sprint E).
// Mappa coerente: PENDING=warn (in corso), APPROVED=success, REJECTED=danger.
function approvazioneSeverity(stato) {
  if (stato === 'APPROVED') return 'success'
  if (stato === 'REJECTED') return 'danger'
  return 'warn'  // PENDING
}

function approvazioneLabel(stato) {
  if (stato === 'APPROVED') return t('preventivi.badge_approvazione_approved')
  if (stato === 'REJECTED') return t('preventivi.badge_approvazione_rejected')
  return t('preventivi.badge_approvazione_pending')
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
      icon: 'pi pi-trash',
      severity: 'danger',
      visible: props.isModificabile,
      disabled: riga?.stato_approvazione_prezzo === 'PENDING',
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
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
      <h4 style="margin: 0;">{{ t('preventivi.section_righe') }}</h4>
      <NewButton v-if="isModificabile" :tooltip="t('preventivi.aggiungi_riga')" @click="onNuovaRiga" />
    </div>

    <DataTable :value="righe" striped-rows size="small" class="app-datatable"
      data-key="id"
      :row-hover="isModificabile"
      :selection-mode="isModificabile ? 'single' : null"
      v-model:selection="selezione"
      @row-click="onRowClick">
      <Column field="articolo_codice" :header="t('preventivi.riga_articolo')" style="min-width: 140px;" />
      <Column field="descrizione" :header="t('preventivi.riga_descrizione')" style="min-width: 180px;" />
      <Column field="quantita" :header="t('preventivi.riga_quantita')" style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('preventivi.riga_uom')" style="width: 70px;" />
      <Column field="prezzo_unitario" :header="t('preventivi.riga_prezzo')" style="width: 130px;">
        <template #body="{ data }">
          <div style="display: flex; flex-direction: column; gap: 0.15rem; align-items: flex-start;">
            <span>{{ formatCurrency(data.prezzo_unitario) }}</span>
            <Tag
              v-if="data.stato_approvazione_prezzo"
              :severity="approvazioneSeverity(data.stato_approvazione_prezzo)"
              :value="approvazioneLabel(data.stato_approvazione_prezzo)"
              v-tooltip.top="data.pratica_approvazione_prezzo_id
                ? t('preventivi.badge_approvazione_pending_tooltip', { pratica_id: data.pratica_approvazione_prezzo_id })
                : ''"
            />
          </div>
        </template>
      </Column>
      <Column field="sconto_percentuale" :header="t('preventivi.riga_sconto')" style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_percentuale ? `${data.sconto_percentuale}%` : '' }}</template>
      </Column>
      <Column field="importo_riga" :header="t('preventivi.riga_importo')" style="width: 120px;">
        <template #body="{ data }">{{ formatCurrency(data.importo_riga) }}</template>
      </Column>
      <Column field="iva_descrizione" :header="t('preventivi.riga_iva')" style="width: 80px;" />
      <Column v-if="isModificabile" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <!-- Form master-detail inline (Fase 3.F3): visibile SOLO quando attivo,
         titolo dipende da formMode. PreventiviRigaForm gia' espone Salva/Annulla
         interni nel proprio template (no DrawerFooter perche' e' una sezione,
         non un drawer). -->
    <div v-if="formMode" class="app-drawer-section" style="margin-top: 1rem;">
      <h4>{{ formMode === 'edit' ? t('preventivi.modifica_riga') : t('preventivi.nuova_riga') }}</h4>
      <PreventiviRigaForm
        :preventivo-id="preventivoId"
        :riga="rigaSelezionata"
        @saved="onRigaSaved"
        @cancel="chiudiForm"
      />
    </div>
  </div>
</template>
