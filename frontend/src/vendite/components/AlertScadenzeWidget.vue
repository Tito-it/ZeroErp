<script setup>
// Scopo: Widget che mostra le versioni listino ATTIVE in scadenza senza successore.
//        Usabile nella toolbar della lista listini o in una dashboard vendite.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { alertScadenze } from '../api/listini'
import { displayDate } from '../../core/utils/date'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { STATUS_ICONS } from '../../core/constants'

const { t } = useI18n()

const props = defineProps({
  giorni: { type: Number, default: 15 }
})

const items = ref([])
const count = ref(0)
const loading = ref(false)
const op = ref(null)

async function load() {
  loading.value = true
  try {
    const res = await alertScadenze(props.giorni)
    const data = res.data.data
    items.value = data.results || []
    count.value = data.count || 0
  } catch {
    items.value = []
    count.value = 0
  } finally {
    loading.value = false
  }
}

function toggle(event) {
  op.value.toggle(event)
}

onMounted(load)
</script>

<template>
  <span v-if="count > 0" class="alert-scadenze-widget">
    <Button type="button" :icon="STATUS_ICONS.ERRORE" severity="warn"
      text rounded size="small" @click="toggle" :loading="loading">
      <template #icon>
        <i :class="STATUS_ICONS.ERRORE" />
        <Badge :value="count" severity="danger" class="alert-scadenze-badge" />
      </template>
    </Button>

    <Popover ref="op" :style="{ width: '550px' }">
      <h4>{{ t('vendite.listini.alert_scadenze_titolo') }}</h4>
      <DataTable :value="items" striped-rows class="app-datatable" data-key="versione_id"
        scrollable scroll-height="250px">
        <Column field="listino_codice" :header="t('vendite.listini.col_codice')" style="width: 120px;" />
        <Column field="codice_versione" :header="t('vendite.listini.col_codice_versione')" style="width: 110px;" />
        <Column field="valido_al" :header="t('vendite.listini.field_valido_al')" style="width: 110px;">
          <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
        </Column>
        <Column :header="t('vendite.listini.col_stato')" style="width: 110px;">
          <template #body="{ data }">
            <span v-if="data.giorni_rimanenti <= 0" class="font-bold">
              {{ t('vendite.listini.alert_scadenze_scaduto') }}
            </span>
            <span v-else>
              {{ t('vendite.listini.alert_scadenze_giorni_rimanenti', { giorni: data.giorni_rimanenti }) }}
            </span>
          </template>
        </Column>
      </DataTable>
    </Popover>
  </span>
</template>

<style scoped>
.alert-scadenze-widget {
  position: relative;
  display: inline-flex;
}
.alert-scadenze-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  font-size: 0.65rem;
  min-width: 1.1rem;
  height: 1.1rem;
}
</style>
