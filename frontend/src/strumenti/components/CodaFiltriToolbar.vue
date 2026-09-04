<script setup>
// Scopo: Toolbar filtri condivisa dei tab code (estratta alla 2ª copia,
//        regola del 2): stato + range date + ambito miei/tutti + azioni
//        pagina (ricarica). L'ambito è per TUTTI gli operatori (2026-07-23,
//        decisione Tid): la coda è una risorsa condivisa e vedere il lavoro
//        altrui che la impegna è visibilità, non gestione — le azioni restano
//        gated altrove. Stato/opzioni arrivano da useCodaFiltri; a ogni
//        cambio emette 'change' (il tab riparte da pagina 1).
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import PageActionsBar from '../../core/components/PageActionsBar.vue'

// Stato filtri del padre via defineModel: il figlio muta `filtri.xxx`
// (oggetto reactive condiviso per riferimento, pattern ContattoForm), senza
// violare no-mutating-props. Il padre lo passa con un semplice `:filtri`.
const filtri = defineModel('filtri', { type: Object, required: true })

defineProps({
  statoOptions: { type: Array, required: true },
  ambitoOptions: { type: Array, required: true },
  pageActions: { type: Array, required: true },
  // Quante righe l'archiviazione sta lasciando fuori dall'elenco (dal BE).
  // ⚠️ L'interruttore da solo non basta: spento e senza numero, «coda pulita»
  // e «tre righe messe via» si leggono uguali. E' la stessa disciplina di
  // `ritirate_count` sul giornale della fattura.
  archiviateCount: { type: Number, default: 0 },
  // Cancello di perimetro emittente (P-2b): filtrare una lista che il backend
  // rifiutera' comunque non porta da nessuna parte. `inert` e non `disabled`
  // sui singoli campi: rende il sottoalbero non cliccabile E non raggiungibile
  // da tastiera o screen reader, che e' quello che serve qui.
  filtriInerti: { type: Boolean, default: false },
})
defineEmits(['change'])
const { t } = useI18n()
</script>

<template>
  <div class="app-page-toolbar">
    <div class="app-page-filters" :inert="filtriInerti">
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
      <div class="form-field">
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
      <!-- Interruttore «mostra archiviate» + il conteggio di cio' che resta
           fuori. Uno solo, qui: le due schede lo ereditano dal telaio. -->
      <div class="form-field">
        <label>{{ t('strumenti.code.filtro_archiviate') }}</label>
        <div class="app-coda-archiviate">
          <ToggleSwitch
            v-model="filtri.archiviate"
            :aria-label="t('strumenti.code.filtro_archiviate')"
            v-tooltip.bottom="t('strumenti.code.filtro_archiviate_hint')"
            @update:model-value="$emit('change')"
          />
          <span
            v-if="!filtri.archiviate && archiviateCount > 0"
            class="app-coda-archiviate-count"
          >
            {{ t('strumenti.code.archiviate_nascoste', archiviateCount,
                  { n: archiviateCount }) }}
          </span>
        </div>
      </div>
    </div>
    <PageActionsBar :actions="pageActions">
      <template #suffix>
        <!-- Slot per i badge di stato lista (es. ListaConfigStatusTag). -->
        <slot name="actions-suffix" />
      </template>
    </PageActionsBar>
  </div>
</template>

<style scoped>
/* L'altezza e' quella dei controlli di form della stessa riga
   (`.app-form-select.p-select` in main.css): un interruttore e' piu' basso di
   una Select, e senza questo il campo si disallineerebbe dai vicini. */
.app-coda-archiviate {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.5rem;
}

.app-coda-archiviate-count {
  color: var(--p-text-muted-color);
  font-size: 0.85em;
  white-space: nowrap;
}
</style>
