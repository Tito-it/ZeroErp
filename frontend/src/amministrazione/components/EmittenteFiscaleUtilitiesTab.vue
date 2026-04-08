<script setup>
// Scopo: Tab autonomo riusabile per la matrice utility -> emittente fiscale.
// Mostra l'elenco dei record (utility, soglie, arrotondamento, attivo),
// consente add tramite combo utility ammesse per ruolo EF, edit inline soglie/attivo
// e delete previa conferma. Reagisce automaticamente al cambio di emittenteId.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { TIPO_RUOLO } from '../../core/constants'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const { execute } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  emittenteId: { type: Number, required: true }
})

// Metodi di arrotondamento: codici fissi DB, label localizzate.
// Allineati al CHECK constraint chk_emittenti_fiscali_utilities_metodo_arrotondamento:
//   metodo_arrotondamento_importi IN ('UP','DOWN','HALF_UP','HALF_DOWN')
// Vincoli decimali allineati al CHECK constraint chk_emittenti_fiscali_utilities_arrotondamento_dec.
const DECIMALI_LIMITS = { MIN: 0, MAX: 6 }
const metodiArrotondamento = computed(() => [
  { label: t('amm_emittenti_fiscali.metodo_half_up'), value: 'HALF_UP' },
  { label: t('amm_emittenti_fiscali.metodo_half_down'), value: 'HALF_DOWN' },
  { label: t('amm_emittenti_fiscali.metodo_up'), value: 'UP' },
  { label: t('amm_emittenti_fiscali.metodo_down'), value: 'DOWN' }
])

const NEW_RECORD_DEFAULT = {
  utility_id: null,
  arrotondamento_importi_dec: 2,
  metodo_arrotondamento_importi: 'HALF_UP',
  minimo_soglia_min: null,
  minimo_soglia_max: null
}

const newRecord = ref({ ...NEW_RECORD_DEFAULT })

function resetNewRecord() {
  newRecord.value = { ...NEW_RECORD_DEFAULT }
}

watch(() => props.emittenteId, async (id) => {
  if (!id) {
    store.clearUtilitiesRecords()
    return
  }
  try {
    await store.fetchUtilitiesRecords(id)
  } catch (e) {
    store.clearUtilitiesRecords()
  }
}, { immediate: true })

async function addRecord() {
  if (!newRecord.value.utility_id) {
    notify.warn(t('amm_emittenti_fiscali.ut_select_required'))
    return
  }
  const result = await execute(
    () => store.addUtilityRecord(props.emittenteId, { ...newRecord.value }),
    { successMessage: t('amm_emittenti_fiscali.ut_added') }
  )
  if (result !== null) resetNewRecord()
}

// Toggle attivo/disattivo (PATCH inline). Il trigger DB blocca disattivazione
// se il record e' referenziato da altre tabelle child.
async function toggleAttivo(row) {
  await execute(
    () => store.patchUtilityRecord(props.emittenteId, row.id, { attivo: !row.attivo })
  )
}

function removeRecord(row) {
  confirmAction({
    title: t('common.confirm'),
    message: t('amm_emittenti_fiscali.ut_remove_confirm', { codice: row.utility_codice }),
    danger: true,
    onAccept: () => {
      execute(
        () => store.removeUtilityRecord(props.emittenteId, row.id),
        { successMessage: t('amm_emittenti_fiscali.ut_removed') }
      )
    }
  })
}
</script>

<template>
  <div class="app-tab-content">
    <Message severity="info" :closable="false" class="mb-3">
      {{ t('amm_emittenti_fiscali.ut_help') }}
    </Message>
    <Message severity="warn" :closable="false" class="mb-3">
      {{ t('amm_emittenti_fiscali.ut_guard_required') }}
    </Message>

    <div v-if="!isReadonly" class="form-grid mb-3">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amm_emittenti_fiscali.ut_select_utility') }} *</label>
          <UtilityPerRuoloSelect
            v-model="newRecord.utility_id"
            :tipo-ruolo-codice="TIPO_RUOLO.EMITTENTE_FISCALE"
            :placeholder="t('amm_emittenti_fiscali.ut_select_utility')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amm_emittenti_fiscali.ut_metodo') }} *</label>
          <Select
            v-model="newRecord.metodo_arrotondamento_importi"
            :options="metodiArrotondamento"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amm_emittenti_fiscali.ut_dec') }} *</label>
          <InputNumber
            v-model="newRecord.arrotondamento_importi_dec"
            :min="DECIMALI_LIMITS.MIN" :max="DECIMALI_LIMITS.MAX"
            showButtons class="w-full"
          />
        </div>
        <div class="form-field" style="align-self: flex-end;">
          <Button
            :label="t('common.add')"
            icon="pi pi-plus"
            class="w-full"
            @click="addRecord"
          />
        </div>
      </div>
    </div>

    <DataTable :value="store.utilitiesRecords" striped-rows class="app-datatable">
      <Column field="utility_codice" :header="t('amm_emittenti_fiscali.ut_col_codice')" style="width: 100px;" />
      <Column field="utility_descrizione" :header="t('amm_emittenti_fiscali.ut_col_descrizione')" />
      <Column field="minimo_soglia_min" :header="t('amm_emittenti_fiscali.ut_col_soglia_min')" style="width: 130px;">
        <template #body="{ data }">{{ data.minimo_soglia_min ?? '—' }}</template>
      </Column>
      <Column field="minimo_soglia_max" :header="t('amm_emittenti_fiscali.ut_col_soglia_max')" style="width: 130px;">
        <template #body="{ data }">{{ data.minimo_soglia_max ?? '—' }}</template>
      </Column>
      <Column field="arrotondamento_importi_dec" :header="t('amm_emittenti_fiscali.ut_col_dec')" style="width: 80px;" />
      <Column field="metodo_arrotondamento_importi" :header="t('amm_emittenti_fiscali.ut_col_metodo')" style="width: 130px;" />
      <Column field="attivo" :header="t('amm_emittenti_fiscali.ut_col_attivo')" style="width: 100px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.attivo" :disabled="isReadonly" @change="toggleAttivo(data)" />
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('amm.col_actions')" style="width: 70px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <Button
            icon="pi pi-trash"
            text rounded size="small"
            severity="danger"
            v-tooltip.bottom="t('common.delete')"
            @click="removeRecord(data)"
          />
        </template>
      </Column>
      <template #empty>
        <div class="app-empty">{{ t('amm_emittenti_fiscali.ut_empty') }}</div>
      </template>
    </DataTable>
  </div>
</template>
