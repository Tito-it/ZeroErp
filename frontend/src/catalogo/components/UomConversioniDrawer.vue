<script setup>
// Scopo: Sub-drawer per gestione conversioni UoM di una specifica unita' di misura.
// Layout: lista conversioni sempre visibile in alto con fattore editabile inline,
// form inserimento nuova conversione in basso (solo "A" selezionabile, "Da" e' la UoM corrente).

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { listConversioniUom, createConversioneUom, updateConversioneUom } from '../api/catalogo'
import { lookupCodici } from '../../core/apiCore'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate } from '../../core/utils/date'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'



const ALWAYS_VALID_FROM = '1900-01-01'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()
const uomLookup = useGlobalLookup(
  'catalogo.unita_misura',
  () => lookupCodici('catalogo.unita_misura', { page_size: 200 }),
  { immediate: true }
)

const props = defineProps({
  visible: { type: Boolean, default: false },
  uomId: { type: [Number, null], default: null },
  uomCodice: { type: String, default: '' },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible', 'saved'])

const conversioniList = ref([])
const listLoading = ref(false)
const adding = ref(false)

function defaultForm() {
  return {
    uom_to_id: null,
    fattore: 1,
    valido_dal: parseIsoDate(ALWAYS_VALID_FROM),
    valido_dal_sempre: true
  }
}

const form = ref(defaultForm())
const currentTipoUomId = computed(() => {
  const selected = uomLookup.items.value.find(item => item.id === props.uomId)
  return selected?.tipo_uom_id ?? null
})

// Edit inline fattore
const editingFattoreId = ref(null)
const editingFattoreValue = ref(null)

// Scopo: Carica conversioni filtrate per la UoM corrente.
async function loadConversioni() {
  if (!props.uomId) return
  listLoading.value = true
  try {
    // `limit` esplicito: dal 2026-08-01 l'endpoint e' paginato (default 25) e
    // qui servono TUTTE le conversioni della UoM, non la prima pagina. 200 e'
    // il tetto del repository; le conversioni di una singola UoM sono poche.
    const res = await listConversioniUom({ uom_id: props.uomId, limit: 200 })
    conversioniList.value = res.data?.data?.results || []
  } catch {
    conversioniList.value = []
  } finally {
    listLoading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (!val) return
  adding.value = false
  form.value = defaultForm()
  editingFattoreId.value = null
  loadConversioni()
})

watch(currentTipoUomId, (tipoId) => {
  if (tipoId == null || form.value.uom_to_id == null) return
  const selectedTo = uomLookup.items.value.find(item => item.id === form.value.uom_to_id)
  if (selectedTo && selectedTo.tipo_uom_id !== tipoId) {
    form.value.uom_to_id = null
  }
})

function todayLocalDate() {
  return parseIsoDate(toDateString(new Date()))
}

watch(() => form.value.valido_dal_sempre, (sempre) => {
  form.value.valido_dal = sempre ? parseIsoDate(ALWAYS_VALID_FROM) : todayLocalDate()
})

// --- Inserimento nuova conversione ---

function startAdd() {
  form.value = defaultForm()
  adding.value = true
}

function cancelAdd() {
  adding.value = false
  form.value = defaultForm()
}

const canSaveNew = computed(() => {
  return form.value.uom_to_id != null && form.value.fattore > 0
})

// Scopo: Crea nuova conversione. Da = UoM corrente, A = selezionata.
async function onSaveNew() {
  const result = await execute(
    () => createConversioneUom({
      uom_from_id: props.uomId,
      uom_to_id: form.value.uom_to_id,
      fattore: form.value.fattore,
      valido_dal: form.value.valido_dal_sempre
        ? ALWAYS_VALID_FROM
        : toDateString(form.value.valido_dal),
    }),
    { successMessage: t('catalogo.conversione_creata') }
  )
  if (result === null) return
  adding.value = false
  form.value = defaultForm()
  await loadConversioni()
  emit('saved')
}

// --- Edit inline fattore ---

function startEditFattore(row) {
  editingFattoreId.value = row.id
  editingFattoreValue.value = row.fattore
}

async function confirmEditFattore(row) {
  const result = await execute(
    () => updateConversioneUom(row.id, { fattore: editingFattoreValue.value }),
    { successMessage: t('catalogo.conversione_salvata') }
  )
  if (result === null) return
  editingFattoreId.value = null
  editingFattoreValue.value = null
  await loadConversioni()
  emit('saved')
}

function cancelEditFattore() {
  editingFattoreId.value = null
  editingFattoreValue.value = null
}

// Scopo: chiusura drawer dal pulsante Chiudi del footer (modalita' lista).
// Nasconde il footer in modalita' adding per non duplicarlo con Annulla/Salva
// del form e non spingere il form sotto al fold.
const onClose = useDrawerClose(emit)

// Toolbar pagina: pulsante "Nuovo" sopra la lista (pattern standard
// frontend-standards "PageActionsBar"). Speculare a ArticoloUomDrawer.
const pageActions = computed(() => [
  {
    key: 'new-conversione',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('catalogo.nuova_conversione_uom'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    disabled: adding.value,
    command: startAdd,
  },
])
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :action="t('catalogo.gestisci_conversioni')" :title="uomCodice" :icon="NAV_ICONS.ARROWS_H" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading">
        <!-- Toolbar pagina standard: filtri (vuoti qui) + "Nuovo" prima
             della lista. Visibile sempre in modalita' lista (non in adding),
             cosi' anche l'empty state ha il pulsante "Nuovo" accessibile. -->
        <div v-if="!adding" class="app-page-toolbar">
          <div class="app-page-filters"></div>
          <PageActionsBar :actions="pageActions" />
        </div>

        <!-- Lista conversioni -->
        <div v-if="conversioniList.length === 0 && !adding" class="app-empty-state">
          <i class="pi pi-arrows-h" />
          <p>{{ t('catalogo.nessuna_conversione') }}</p>
        </div>

        <DataTable v-if="conversioniList.length > 0" :value="conversioniList"
          class="app-datatable app-datatable--inner" striped-rows>
          <Column :header="t('catalogo.col_uom_da')" style="width: 100px;">
            <template #body="{ data }">
              <strong>{{ data.uom_from_codice }}</strong>
            </template>
          </Column>
          <Column :header="t('catalogo.col_uom_a')" style="width: 100px;">
            <template #body="{ data }">
              <strong>{{ data.uom_to_codice }}</strong>
            </template>
          </Column>
          <Column :header="t('catalogo.col_fattore')" style="width: 150px;">
            <template #body="{ data }">
              <template v-if="editingFattoreId === data.id">
                <div>
                  <InputNumber v-model="editingFattoreValue" :min="0" :min-fraction-digits="2"
                    :max-fraction-digits="10" style="width: 100px;" />
                  <Button :icon="MANAGE_ICONS.CONFIRM" text rounded size="small" class="app-action-btn"
                    @click="confirmEditFattore(data)" />
                  <Button :icon="MANAGE_ICONS.CANCEL" text rounded size="small"
                    @click="cancelEditFattore" />
                </div>
              </template>
              <template v-else>
                <span v-if="!isReadonly" class="fattore-cell" @click="startEditFattore(data)">
                  {{ data.fattore }}
                  <i class="pi pi-pencil" style="font-size: 0.7rem; margin-left: 0.25rem; opacity: 0.5;" />
                </span>
                <span v-else>{{ data.fattore }}</span>
              </template>
            </template>
          </Column>
          <Column :header="t('catalogo.field_valido_al')" style="width: 100px;">
            <template #body="{ data }">{{ displayDate(data.valido_al) || '—' }}</template>
          </Column>
        </DataTable>

        <!-- Form inserimento nuova conversione (pulsante "Nuovo" e' nella
             toolbar sopra la lista, non piu' inline qui). -->
        <template v-if="!isReadonly">
          <template v-if="adding">
            <div class="app-drawer-section">
              <h4>{{ t('catalogo.nuova_conversione_uom') }}</h4>
            </div>
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('catalogo.field_uom_a') }} *</label>
                <LookupSelect v-model="form.uom_to_id" rel="catalogo.unita_misura"
                  :placeholder="t('catalogo.select_uom_a')" filter-field="tipo_uom_id"
                  :filter-value="currentTipoUomId" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.col_fattore') }} *</label>
                <InputNumber v-model="form.fattore" :min="0" :min-fraction-digits="2"
                  :max-fraction-digits="10" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_valido_dal') }}</label>
                <DatePicker
                  v-model="form.valido_dal"
                  :date-format="DATE_FORMAT"
                  show-icon
                  show-button-bar
                  :disabled="form.valido_dal_sempre"
                  :invalid="campiErrati.includes('valido_dal')"
                />
              </div>
            </div>
            <div class="form-grid">
              <div class="form-field">
                <label>{{ t('catalogo.validita_sempre') }}</label>
                <ToggleSwitch v-model="form.valido_dal_sempre" />
              </div>
            </div>
          </template>
        </template>
      </template>

      <!-- Footer standard: in modalita' adding mostra Annulla/Salva del form,
           altrimenti close-only per chiudere il drawer (pattern speculare
           ArticoloUomDrawer). -->
      <FormFooter
        v-if="adding"
        :loading="loading"
        :disabled="!canSaveNew"
        @save="onSaveNew"
        @cancel="cancelAdd"
      />
      <FormFooter v-else close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>

<style scoped>
.fattore-cell {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  font-family: monospace;
}
.fattore-cell:hover {
  color: var(--p-primary-color);
}
</style>
