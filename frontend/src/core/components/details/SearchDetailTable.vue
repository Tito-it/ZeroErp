<script setup>
// Scopo: tabella dettaglio universale per la ricerca — sostituisce ClienteDetail,
// FornitoreDetail e GenericDetail con un unico componente parametrico.
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useSearchDetail } from '../../composables/useSearchDetail'
import { STATO_CLIENTE_MAP } from '../../utils/severity'
import DetailActions from './DetailActions.vue'

const { t } = useI18n()

const props = defineProps({
  row: { type: Object, required: true },
  variant: { type: String, default: 'generic' }
})

const emit = defineEmits(['set-context', 'open-detail'])

const { detailRows, loading } = useSearchDetail(props)
</script>

<template>
  <div class="detail-container">
    <DataTable :value="detailRows" :loading="loading" size="small" stripedRows class="app-datatable">
      <Column field="codice" :header="t('search.detail_code')" style="width: 100px" />

      <!-- Colonne specifiche cliente -->
      <Column v-if="variant === 'cliente'" field="istanza_codice" :header="t('search.detail_instance')" style="width: 120px" />
      <Column v-if="variant === 'cliente'" field="utility_descrizione" :header="t('search.detail_utility')" style="width: 80px" />

      <!-- Colonna descrizione solo per generic -->
      <Column v-if="variant === 'generic'" field="descrizione" :header="t('search.detail_description')" />

      <Column field="indirizzo" :header="t('search.detail_address')" />
      <Column field="comune" :header="t('search.col_comune')" style="width: 140px" />

      <!-- Colonna stato: varia per variante -->
      <Column v-if="variant === 'cliente'" field="stato_descrizione" :header="t('search.detail_status')" style="width: 130px">
        <template #body="{ data }">
          <Tag
            v-if="data.stato_codice"
            :value="data.stato_descrizione"
            :severity="STATO_CLIENTE_MAP[(data.stato_codice || '').trim()] || 'secondary'"
          />
          <span v-else>-</span>
        </template>
      </Column>
      <Column v-else-if="variant === 'fornitore'" field="stato_descrizione" :header="t('search.detail_status')" style="width: 130px">
        <template #body="{ data }">
          <Tag
            :value="data.attivo ? t('search.status_active') : t('search.status_inactive')"
            :severity="data.attivo ? 'success' : 'danger'"
          />
        </template>
      </Column>

      <Column :header="t('search.col_actions')" style="width: 80px" :exportable="false">
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
