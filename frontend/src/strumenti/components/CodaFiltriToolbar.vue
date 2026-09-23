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
import SelectButton from 'primevue/selectbutton'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { parseIsoDate } from '../../core/utils/date'

// ⛔ UN SOLO CONDOTTO VERSO LO STATO DEI FILTRI: lo store.
//    Fino al 2026-09-23 questo componente ne aveva DUE — un `defineModel`
//    (`filtri`) per stato/ambito/archiviate e la prop `store` per il periodo e
//    per il segno — con un commento che *asseriva* che fossero lo stesso
//    oggetto. Lo erano, ma per abitudine dell'unico chiamante: niente lo
//    imponeva, e un secondo chiamante con un `:filtri` diverso avrebbe scritto
//    il periodo nello store e tutto il resto altrove, in silenzio.
//    ⭐ Con lo store in mano, `filtri` era derivabile: due sedi che possono
//    divergere si tengono solo quando non se ne puo' avere una.
const props = defineProps({
  // Lo store-coda: da qui passano TUTTI i filtri — quelli scritti diretti
  // (`store.filters.stato`), il periodo (`bindPeriodo`, che porta l'invariante
  // `da <= a`) e il segno dei filtri attivi di `FiltriLista`.
  store: { type: Object, required: true },
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
const emit = defineEmits(['change'])
const { t } = useI18n()

// Il periodo e' UN filtro con due estremi: un binding, un componente.
// ⛔ I FILTRI PASSANO DAI BINDER, e qui c'e' una ragione in piu' del solito:
//    lo store arriva come PROP, e scrivere `v-model="store.filters.x"` sarebbe
//    mutare una prop dall'interno (`vue/no-mutating-props`). Il binder chiede
//    il cambio con una funzione, quindi la proprieta' dello stato resta dove
//    deve stare — ed e' la stessa cosa che un `v-model` fa, detta a voce.
const { bindSelect, bindToggle, bindPeriodo } = useStoreFilterBindings(
  props.store, () => emit('change'),
)
const { value: statoFiltro, onChange: onStatoChange } = bindSelect('stato')
const { value: ambitoFiltro, onChange: onAmbitoChange } = bindSelect('ambito')
// `on`/`off` espliciti: lo store dichiara `false`, e `buildCodaParams` manda il
// parametro solo quando e' acceso (`if (f.archiviate)`).
const { value: archiviateFiltro, onChange: onArchiviateChange } = bindToggle(
  'archiviate', { on: true, off: false },
)
// ⭐ La coda vuole sempre un floor su `data_da`: svuotandolo torna il default
//    di progetto, invece di aprire l'elenco su tutto lo storico.
const periodo = bindPeriodo('data_da', 'data_a', {
  clearToDa: () => parseIsoDate(props.store.filtriDefault.data_da),
})
</script>

<template>
  <div class="app-page-toolbar">
    <FiltriLista :store="store" :inert="filtriInerti">
      <div class="form-field">
        <label>{{ t('strumenti.code.filtro_stato') }}</label>
        <Select
          v-model="statoFiltro"
          :options="statoOptions"
          option-label="label"
          option-value="value"
          show-clear
          :placeholder="t('common.all')"
          @update:model-value="onStatoChange"
        />
      </div>
      <FiltroPeriodo :periodo="periodo" />
      <div class="form-field">
        <label>{{ t('strumenti.code.filtro_ambito') }}</label>
        <SelectButton
          v-model="ambitoFiltro"
          :options="ambitoOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          @update:model-value="onAmbitoChange"
        />
      </div>
      <!-- «Mostra archiviate (N)»: BB FiltroToggle col conteggio, lo stesso
           del «Mostra annullati» della lista Lotti. Uno solo, qui: le due schede lo
           ereditano dal telaio. Nessuna etichetta sopra — il testo sta
           nell'interruttore — e il campo si allinea in basso, alla riga dei
           controlli dei vicini. -->
      <div class="form-field app-coda-filtri-toggle">
        <FiltroToggle
          v-model="archiviateFiltro"
          :label="t('strumenti.code.filtro_archiviate')"
          :hint="t('strumenti.code.filtro_archiviate_hint')"
          :count="archiviateCount"
          @change="onArchiviateChange"
        />
      </div>
    </FiltriLista>
    <PageActionsBar :actions="pageActions">
      <template #suffix>
        <!-- Slot per i badge di stato lista (es. ListaConfigStatusTag). -->
        <slot name="actions-suffix" />
      </template>
    </PageActionsBar>
  </div>
</template>

<style scoped>
/* I vicini sono «etichetta sopra + controllo sotto»; questo campo ha il solo
   interruttore (l'etichetta e' dentro). Si stira all'altezza della riga e
   spinge il controllo in basso, cosi' resta allineato agli altri. */
.app-coda-filtri-toggle {
  align-self: stretch;
  justify-content: flex-end;
}
</style>
