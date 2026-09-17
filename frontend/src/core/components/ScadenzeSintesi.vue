<script setup>
// Scopo: building block "valore scadenza" per la scheda di un documento —
//        mostra la prossima rata per data e, se il piano ne ha più di una, il
//        conteggio posizionale (`2/3`) con l'elenco completo in popover.
//
// Due ingressi, per vivere in contesti diversi senza duplicare la regola:
//   1. `scadenze` (array completo) — il caso DRAWER: il documento è già
//      caricato, quindi il popover può mostrare tutte le rate;
//   2. `prossima-data` + `count` (campi già risolti dal BE) — il caso LISTA,
//      dove non si può spedire il piano rate di ogni riga (display field via
//      JOIN). Qui il conteggio è testuale e non apre nulla: l'elenco si vede
//      aprendo il documento.
//
// ⚠️ Semantica TEMPORALE, non di pagamento: vedi l'avvertenza in
// `useScadenzeSintesi` — «prossima» = prossima per data, mai «da incassare».
// Per questo qui non esiste alcuna decorazione di insoluto/sollecito.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Popover from 'primevue/popover'

import { sintesiScadenze } from '../composables/useScadenzeSintesi'
import { displayDate } from '../utils/date'
import { formatCurrency } from '../utils/format'

const { t } = useI18n()

const props = defineProps({
  // Modo 1 — piano rate completo (drawer).
  scadenze: { type: Array, default: () => [] },
  // Modo 2 — campi risolti dal BE (lista). Ignorati se `scadenze` è popolato.
  prossimaData: { type: [String, Date, null], default: null },
  count: { type: [Number, null], default: null },
  // Titolo del popover; default `common.scadenze_titolo`.
  titolo: { type: String, default: null },
  // Placeholder per documento senza rate (allineato al resto della scheda).
  placeholder: { type: String, default: '—' },
})

const popover = ref(null)

// La regola vive nel composable: qui si sceglie solo QUALE fonte usare.
const sintesi = computed(() => sintesiScadenze(props.scadenze))
const haPiano = computed(() => props.scadenze.length > 0)

// Vista unificata dei due modi, così il template non si biforca.
const vista = computed(() => {
  if (haPiano.value) {
    const s = sintesi.value
    return { data: s.prossima?.data_scadenza ?? null, indice: s.indice, count: s.count }
  }
  return { data: props.prossimaData, indice: 0, count: Number(props.count ?? 0) }
})

// Il popover richiede l'elenco: nel modo "lista" non c'è nulla da aprire.
const apribile = computed(() => haPiano.value && sintesi.value.count > 1)

// Scopo: apre/chiude l'elenco rate ancorato al chip.
function toggle(event) {
  popover.value?.toggle(event)
}
</script>

<template>
  <span class="app-scadenze-sintesi">
    <span v-if="!vista.data">{{ placeholder }}</span>
    <template v-else>
      <span>{{ displayDate(vista.data) }}</span>

      <!-- Piano rateizzato con elenco disponibile: chip posizionale cliccabile. -->
      <Button
        v-if="apribile"
        type="button"
        text
        size="small"
        icon="pi pi-list"
        icon-pos="right"
        :label="`${vista.indice}/${vista.count}`"
        :aria-label="t('common.scadenze_vedi_tutte')"
        v-tooltip.top="t('common.scadenze_vedi_tutte')"
        class="app-scadenze-chip"
        @click="toggle"
      />

      <!-- Modo lista: il conteggio informa, il dettaglio sta nel documento. -->
      <span v-else-if="vista.count > 1" class="app-scadenze-conteggio">
        {{ t('common.scadenze_n_rate', { n: vista.count }) }}
      </span>
    </template>

    <Popover v-if="apribile" ref="popover" :style="{ width: '420px' }">
      <h4>{{ titolo || t('common.scadenze_titolo') }}</h4>
      <DataTable
        :value="sintesi.rate"
        class="app-datatable"
        striped-rows
        size="small"
        data-key="id"
        scrollable
        scroll-height="240px"
      >
        <Column
          field="numero_rata"
          :header="t('common.scadenze_col_rata')"
          style="width: 60px;"
        />
        <Column field="data_scadenza" :header="t('common.scadenze_col_scadenza')">
          <template #body="{ data }">{{ displayDate(data.data_scadenza) }}</template>
        </Column>
        <Column
          field="importo"
          :header="t('common.scadenze_col_importo')"
          header-style="text-align: right;"
          body-style="text-align: right;"
        >
          <template #body="{ data }">
            {{ formatCurrency(data.importo, { placeholder: '—' }) }}
          </template>
        </Column>
      </DataTable>

      <!-- Quadratura del piano: la somma delle rate. Non la si confronta col
           totale del documento — se divergono è un dato da guardare, non da
           correggere a video. -->
      <div class="app-doc-totali">
        <div class="app-doc-totali-riga app-doc-totali-riga--forte">
          <span class="app-doc-totali-label">{{ t('common.scadenze_totale') }}</span>
          <span class="app-doc-totali-value">{{ formatCurrency(sintesi.totale) }}</span>
        </div>
      </div>
    </Popover>
  </span>
</template>

<style scoped>
.app-scadenze-sintesi {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
}
/* Chip compatto: non deve pesare come un pulsante d'azione. */
.app-scadenze-chip {
  padding: 0 0.25rem;
  height: 1.4rem;
  font-size: var(--app-font-size-sm);
}
.app-scadenze-conteggio {
  color: var(--app-text-muted);
  font-size: var(--app-font-size-sm);
}
</style>
