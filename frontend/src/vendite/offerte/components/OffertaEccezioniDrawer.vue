<script setup>
// Scopo: Sub-drawer eccezioni offerta commerciale (master-detail inline).
//        Lista paginata + form sotto. Editabile solo se offerta in BOZZA
//        (readonly propagato dal parent + lock locale su stato).
//
// Specchio strutturale di ContrattoRigheDrawer.vue ma versione semplificata:
// niente preview prezzi, niente integrazione BoM, niente componenti
// compositi. Le eccezioni offerta sono il mirror di contratti_righe ma
// in v1 si limitano a tipo + articolo + prezzo/quantita + fonte/erogazione.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

import ArticoloLookup from '../../../core/components/ArticoloLookup.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerFooter from '../../../core/components/DrawerFooter.vue'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../../core/constants'
import { displayDate } from '../../../core/utils/date'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { FONTE_QUANTITA_ATTESA, TIPO_ECCEZIONE, TIPO_EROGAZIONE } from '../../constants'
import { useOfferteStore } from '../stores/offerte'

const { t } = useI18n()
const store = useOfferteStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const parentReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  offertaId: { type: Number, required: true },
  offertaCodice: { type: String, default: '' },
  offertaStatoCodice: { type: String, default: '' },
  offertaStatoDescrizione: { type: String, default: '' },
  offertaCliente: { type: String, default: '' },
  offertaValiditaDal: { type: String, default: null },
  offertaValiditaAl: { type: String, default: null },
  eccezioniIniziali: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'changed'])

// Readonly cumulativo: permesso area + stato non-BOZZA. Niente logica locale
// di workflow nei sub-drawer (frontend-standards §"Drawer di entita' con
// sub-drawer — catena readonly"): qui combiniamo solo il parent readonly
// con la regola di stato locale.
const isReadonly = computed(
  () => parentReadonly.value || props.offertaStatoCodice !== 'BOZZA',
)

const eccezioni = ref([])
const formMode = ref(null) // null | 'create' | 'edit'
const editingId = ref(null)
const selectedRow = ref(null)
const form = ref({})

const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// --- Enum options ---

const tipoEccezioneOptions = [
  { value: TIPO_ECCEZIONE.OVERRIDE, label: 'OVERRIDE' },
  { value: TIPO_ECCEZIONE.ESCLUSIONE, label: 'ESCLUSIONE' },
  { value: TIPO_ECCEZIONE.AGGIUNTA, label: 'AGGIUNTA' },
]

const tipoErogazioneOptions = [
  { value: TIPO_EROGAZIONE.CANONE, label: t('vendite.offerte.tipo_erogazione_canone') },
  { value: TIPO_EROGAZIONE.UNA_TANTUM, label: t('vendite.offerte.tipo_erogazione_una_tantum') },
  { value: TIPO_EROGAZIONE.CONSUMO, label: t('vendite.offerte.tipo_erogazione_consumo') },
]

// Matrice tipo_erogazione → fonti ammesse (specchio ridotto della logica
// di contratti_righe; il CHECK DB applica gli stessi vincoli su
// offerte_commerciali_eccezioni).
const _FONTI_PER_TIPO = {
  [TIPO_EROGAZIONE.CANONE]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  [TIPO_EROGAZIONE.UNA_TANTUM]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  [TIPO_EROGAZIONE.CONSUMO]: [
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.LETTURE, default: true },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
}

function _fontiPerTipo(tipo) {
  return _FONTI_PER_TIPO[tipo] || []
}

function _defaultFontePerTipo(tipo) {
  return _fontiPerTipo(tipo).find((f) => f.default)?.value ?? null
}

const fonteOptions = computed(() => _fontiPerTipo(form.value?.tipo_erogazione).map((f) => ({
  value: f.value,
  label: f.value,
})))

// --- CRUD ---

async function reload() {
  const list = await store.loadEccezioni(props.offertaId)
  eccezioni.value = list
  emit('changed')
}

watch(() => props.visible, async (val) => {
  if (!val) {
    formMode.value = null
    editingId.value = null
    selectedRow.value = null
    return
  }
  // All'apertura partiamo dalla snapshot ricevuta dal parent, poi ricarichiamo
  // per coerenza con eventuali modifiche concorrenti.
  eccezioni.value = [...(props.eccezioniIniziali || [])]
  await reload()
})

function newForm() {
  return {
    tipo_eccezione: TIPO_ECCEZIONE.OVERRIDE,
    articolo_id: null,
    articolo_obj: null,
    tipo_erogazione: TIPO_EROGAZIONE.CANONE,
    fonte_quantita_attesa: _defaultFontePerTipo(TIPO_EROGAZIONE.CANONE),
    prezzo_unitario: null,
    quantita: null,
    uom_operativa_id: null,
    attivo: true,
    ordine: null,
  }
}

function fromRow(row) {
  return {
    tipo_eccezione: row.tipo_eccezione,
    articolo_id: row.articolo_id,
    articolo_obj: row.articolo_id
      ? { id: row.articolo_id, descrizione: row.articolo_display || '' }
      : null,
    tipo_erogazione: row.tipo_erogazione || TIPO_EROGAZIONE.CANONE,
    fonte_quantita_attesa: row.fonte_quantita_attesa
      || _defaultFontePerTipo(row.tipo_erogazione || TIPO_EROGAZIONE.CANONE),
    prezzo_unitario: row.prezzo_unitario,
    quantita: row.quantita,
    uom_operativa_id: row.uom_operativa_id,
    attivo: row.attivo ?? true,
    ordine: row.ordine ?? null,
  }
}

function openCreate() {
  form.value = newForm()
  editingId.value = null
  formMode.value = 'create'
  selectedRow.value = null
}

function onRowSelect(event) {
  if (isReadonly.value) return
  const row = event.data
  selectedRow.value = row
  editingId.value = row.id
  form.value = fromRow(row)
  formMode.value = 'edit'
}

function closeForm() {
  formMode.value = null
  editingId.value = null
  selectedRow.value = null
}

watch(() => form.value?.tipo_erogazione, (nuovoTipo) => {
  if (!nuovoTipo || !form.value) return
  const fontiValide = _fontiPerTipo(nuovoTipo).map((f) => f.value)
  if (!fontiValide.includes(form.value.fonte_quantita_attesa)) {
    form.value.fonte_quantita_attesa = _defaultFontePerTipo(nuovoTipo)
  }
})

function onArticoloSelected(item) {
  if (!item) {
    form.value.articolo_id = null
    form.value.articolo_obj = null
    return
  }
  form.value.articolo_id = item.id
  form.value.articolo_obj = item
}

const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  if (!f) return false
  if (!f.tipo_eccezione) return false
  if (!f.articolo_id) return false
  if (!f.fonte_quantita_attesa) return false
  return true
})

function buildPayload() {
  const f = form.value
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    fonte_quantita_attesa: f.fonte_quantita_attesa,
    prezzo_unitario: f.prezzo_unitario != null && f.prezzo_unitario !== ''
      ? String(f.prezzo_unitario) : null,
    quantita: f.quantita != null && f.quantita !== ''
      ? String(f.quantita) : null,
    uom_operativa_id: f.uom_operativa_id || null,
    attivo: f.attivo,
    ordine: f.ordine,
  }
  return payload
}

async function handleSave() {
  if (formMode.value === 'create') {
    const payload = {
      tipo_eccezione: form.value.tipo_eccezione,
      articolo_id: form.value.articolo_id,
      ...buildPayload(),
    }
    const result = await execute(
      () => store.addEccezione(props.offertaId, payload),
      { successMessage: t('vendite.offerte.eccezione_creata') },
    )
    if (result !== null) {
      await reload()
      closeForm()
    }
  } else if (formMode.value === 'edit') {
    const result = await execute(
      () => store.aggiornaEccezione(props.offertaId, editingId.value, buildPayload()),
      { successMessage: t('vendite.offerte.eccezione_aggiornata') },
    )
    if (result !== null) {
      await reload()
      closeForm()
    }
  }
}

function onDeleteRow(row, event) {
  event?.stopPropagation?.()
  if (isReadonly.value) return
  confirmAction({
    header: t('vendite.offerte.eccezione_elimina_titolo'),
    message: t('vendite.offerte.eccezione_elimina_messaggio'),
    acceptLabel: t('common.delete'),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => store.eliminaEccezione(props.offertaId, row.id),
        { successMessage: t('vendite.offerte.eccezione_eliminata') },
      )
      if (result !== null) {
        if (editingId.value === row.id) closeForm()
        await reload()
      }
    },
  })
}

const pageActions = computed(() => [
  {
    key: 'nuova',
    kind: 'primary',
    label: t('vendite.offerte.eccezione_nuova'),
    icon: MANAGE_ICONS.ADD,
    disabled: isReadonly.value || formMode.value === 'create',
    hideWhenReadonly: true,
    command: openCreate,
  },
])

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
    @update:visible="(val) => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="t('common.manage')"
        :title="t('vendite.offerte.eccezioni_titolo')"
        :icon="MANAGE_ICONS.RIGHE"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">

        <DrawerEntityHeader>
          <Tag :value="props.offertaCodice" severity="secondary" />
          <span v-if="props.offertaCliente" class="app-drawer-header-muted">
            {{ props.offertaCliente }}
          </span>
          <span
            v-if="props.offertaValiditaDal"
            class="app-drawer-header-muted"
          >
            {{ displayDate(props.offertaValiditaDal) }} —
            {{ props.offertaValiditaAl ? displayDate(props.offertaValiditaAl) : '∞' }}
          </span>
          <template #status>
            <Tag
              :value="props.offertaStatoDescrizione"
              :severity="statoOffertaSeverity(props.offertaStatoCodice)"
            />
          </template>
        </DrawerEntityHeader>

        <div class="app-page-toolbar mt-2">
          <div class="app-page-filters" />
          <PageActionsBar :actions="pageActions" />
        </div>

        <DataTable
          :value="eccezioni"
          :loading="loading"
          paginator
          :rows="10"
          :rows-per-page-options="[10, 25]"
          paginator-position="top"
          striped-rows
          scrollable
          scroll-height="flex"
          class="app-datatable app-datatable--inner"
          selection-mode="single"
          v-model:selection="selectedRow"
          data-key="id"
          @row-select="onRowSelect"
        >
          <Column
            field="tipo_eccezione"
            :header="t('vendite.offerte.col_tipo_eccezione')"
            style="width: 130px;"
          >
            <template #body="{ data }">
              <Tag :value="data.tipo_eccezione" severity="info" />
            </template>
          </Column>
          <Column
            field="articolo_display"
            :header="t('vendite.offerte.col_articolo')"
            style="min-width: 180px;"
          >
            <template #body="{ data }">{{ data.articolo_display || data.articolo_id }}</template>
          </Column>
          <Column
            field="tipo_erogazione"
            :header="t('vendite.offerte.col_tipo_erogazione')"
            style="width: 130px;"
          />
          <Column
            field="prezzo_unitario"
            :header="t('vendite.offerte.col_prezzo_unitario')"
            style="width: 120px;"
          />
          <Column
            field="quantita"
            :header="t('vendite.offerte.col_quantita')"
            style="width: 100px;"
          />
          <Column
            field="attivo"
            :header="t('vendite.offerte.col_attivo')"
            style="width: 90px;"
          >
            <template #body="{ data }">
              <Tag
                :value="data.attivo ? t('common.si') : t('common.no')"
                :severity="data.attivo ? 'success' : 'secondary'"
              />
            </template>
          </Column>
          <Column
            :header="t('common.col_azioni')"
            class="app-col-actions"
            :exportable="false"
            style="width: 70px;"
          >
            <template #body="{ data }">
              <Button
                :icon="MANAGE_ICONS.DELETE"
                text
                rounded
                size="small"
                class="app-delete-btn"
                :disabled="isReadonly"
                @click="(event) => onDeleteRow(data, event)"
              />
            </template>
          </Column>
        </DataTable>

        <!-- Form dettaglio (create/edit). -->
        <div
          v-if="formMode"
          class="app-drawer-section mt-3"
          style="border-top: 1px solid var(--app-drawer-section-border); padding-top: 1rem;"
        >
          <h4>
            {{ formMode === 'create'
              ? t('vendite.offerte.eccezione_nuova')
              : t('vendite.offerte.eccezione_modifica') }}
          </h4>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_tipo_eccezione') }} *</label>
              <Select
                v-model="form.tipo_eccezione"
                :options="tipoEccezioneOptions"
                option-label="label"
                option-value="value"
                :disabled="formMode === 'edit'"
                class="w-full"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_articolo') }} *</label>
              <ArticoloLookup
                v-if="formMode === 'create'"
                :model-value="form.articolo_obj"
                @update:model-value="onArticoloSelected"
              />
              <Tag
                v-else
                :value="form.articolo_obj?.descrizione || form.articolo_id"
                severity="info"
              />
            </div>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_tipo_erogazione') }}</label>
              <Select
                v-model="form.tipo_erogazione"
                :options="tipoErogazioneOptions"
                option-label="label"
                option-value="value"
                show-clear
                class="w-full"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_fonte_quantita') }} *</label>
              <Select
                v-model="form.fonte_quantita_attesa"
                :options="fonteOptions"
                option-label="label"
                option-value="value"
                class="w-full"
              />
            </div>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_prezzo_unitario') }}</label>
              <InputNumber
                v-model="form.prezzo_unitario"
                class="w-full"
                :min-fraction-digits="0"
                :max-fraction-digits="6"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_quantita') }}</label>
              <InputNumber
                v-model="form.quantita"
                class="w-full"
                :min-fraction-digits="0"
                :max-fraction-digits="6"
              />
            </div>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_uom_operativa') }}</label>
              <LookupSelect
                v-model="form.uom_operativa_id"
                rel="catalogo.unita_misura"
                show-clear
                class="w-full"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_ordine') }}</label>
              <InputNumber v-model="form.ordine" class="w-full" :min="0" />
            </div>
          </div>

          <div class="form-field">
            <label style="display: inline-flex; gap: 0.5rem; align-items: center;">
              <ToggleSwitch v-model="form.attivo" />
              {{ t('vendite.offerte.field_attivo') }}
            </label>
          </div>

          <div
            style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem;"
          >
            <Button
              :label="t('common.cancel')"
              text
              severity="secondary"
              @click="closeForm"
            />
            <Button
              :label="t('common.save')"
              icon="pi pi-save"
              severity="primary"
              :loading="loading"
              :disabled="!canSave"
              @click="handleSave"
            />
          </div>
        </div>

        <DrawerFooter v-if="!formMode" close-only @cancel="onClose" />
      </template>
    </div>
  </Drawer>
</template>
