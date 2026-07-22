<script setup>
// Scopo: Toolbar filtri condivisa dei tab code (estratta alla 2ª copia,
//        regola del 2): stato + range date + ambito miei/tutti (visibile solo
//        con code_manage) + azioni pagina (ricarica). Stato/opzioni arrivano
//        da useCodaFiltri; a ogni cambio emette 'change' (il tab riparte da
//        pagina 1).
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import SelectButton from 'primevue/selectbutton'
import PageActionsBar from '../../core/components/PageActionsBar.vue'

// Stato filtri del padre via defineModel: il figlio muta `filtri.xxx`
// (oggetto reactive condiviso per riferimento, pattern ContattoForm), senza
// violare no-mutating-props. Il padre lo passa con un semplice `:filtri`.
const filtri = defineModel('filtri', { type: Object, required: true })

defineProps({
  statoOptions: { type: Array, required: true },
  ambitoOptions: { type: Array, required: true },
  canManage: { type: Boolean, default: false },
  pageActions: { type: Array, required: true },
})
defineEmits(['change'])
const { t } = useI18n()
</script>

<template>
  <div class="app-page-toolbar">
    <div class="app-page-filters">
      <div class="form-field">
        <label>{{ t('strumenti.code.filtro_stato') }}</label>
        <Select
          v-model="filtri.stato"
          :options="statoOptions"
          option-label="label"
          option-value="value"
          show-clear
          :placeholder="t('common.all')"
          @update:model-value="$emit('change')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('common.data_da') }}</label>
        <DatePicker
          v-model="filtri.dataDa"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @update:model-value="$emit('change')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('common.data_a') }}</label>
        <DatePicker
          v-model="filtri.dataA"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @update:model-value="$emit('change')"
        />
      </div>
      <div v-if="canManage" class="form-field">
        <label>{{ t('strumenti.code.filtro_ambito') }}</label>
        <SelectButton
          v-model="filtri.ambito"
          :options="ambitoOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          @update:model-value="$emit('change')"
        />
      </div>
    </div>
    <PageActionsBar :actions="pageActions" />
  </div>
</template>
