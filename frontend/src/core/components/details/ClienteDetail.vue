<script setup>
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useSearchDetail } from '../../composables/useSearchDetail'
import DetailActions from './DetailActions.vue'

const { t } = useI18n()

const props = defineProps({
  row: { type: Object, required: true }
})

const emit = defineEmits(['set-context', 'open-detail'])

const { detailRows, loading } = useSearchDetail(props)

// Mappa stati cliente -> severity Tag PrimeVue
const STATO_SEVERITY = {
  AT: 'success',
  PR: 'info',
  RS: 'warn',
  SF: 'warn',
  SC: 'danger',
  CH: 'secondary',
  CF: 'secondary',
  CM: 'danger',
  CW: 'secondary',
  AN: 'danger',
  AG: 'danger'
}
</script>

<template>
  <div class="detail-container">
    <DataTable :value="detailRows" :loading="loading" size="small" stripedRows class="app-datatable">
      <Column field="codice" :header="t('search.detail_code')" style="width: 100px" />
      <Column field="istanza_codice" :header="t('search.detail_instance')" style="width: 100px" />
      <Column field="utility_descrizione" :header="t('search.detail_utility')" style="width: 80px" />
      <Column field="indirizzo" :header="t('search.detail_address')" />
      <Column field="comune" :header="t('search.col_comune')" style="width: 140px" />
      <Column field="stato_descrizione" :header="t('search.detail_status')" style="width: 130px">
        <template #body="{ data }">
          <Tag
            v-if="data.stato_codice"
            :value="data.stato_descrizione"
            :severity="STATO_SEVERITY[data.stato_codice] || 'secondary'"
          />
          <span v-else>-</span>
        </template>
      </Column>
      <Column :header="t('search.col_actions')" style="width: 160px" :exportable="false">
        <template #body="{ data }">
          <DetailActions
            :row="row"
            :detailRow="data"
            @set-context="emit('set-context', $event)"
            @open-detail="emit('open-detail', $event)"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.detail-container {
  padding: 0.25rem 0;
}
</style>
