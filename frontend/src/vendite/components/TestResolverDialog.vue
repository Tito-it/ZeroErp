<script setup>
// Scopo: Dialog modale per testare il resolver prezzo listino.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { extractApiError } from '../../core/utils/apiError'
import { testResolverPrezzo } from '../api/listini'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { DATE_FORMAT, DRAWER_WIDTH } from '../../core/constants'
import { toDateString } from '../../core/utils/date'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])

const form = ref({
  articolo_obj: null,
  uom_id: null,
  data_riferimento: new Date(),
  ba_obj: null,
})
const result = ref(null)
const errorMsg = ref(null)

const canTest = computed(() => form.value.articolo_obj?.id && form.value.uom_id && form.value.data_riferimento)

const matchLevelDescriptions = {
  1: 'BA + Utility + Emittente',
  2: 'BA + Utility',
  3: 'BA + Emittente',
  4: 'BA',
  5: 'Utility + Emittente',
  6: 'Utility',
  7: t('listini.resolver_fallback'),
}

async function doTest() {
  result.value = null
  errorMsg.value = null
  const payload = {
    articolo_id: form.value.articolo_obj.id,
    uom_id: form.value.uom_id,
    data_riferimento: toDateString(form.value.data_riferimento),
    billing_account_id: form.value.ba_obj?.id || null,
  }
  try {
    const apiRes = await testResolverPrezzo(payload)
    result.value = apiRes.data.data
  } catch (err) {
    errorMsg.value = extractApiError(err) || t('listini.resolver_errore')
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog :visible="visible" @update:visible="v => emit('update:visible', v)"
    :header="t('listini.test_prezzo')" modal :style="{ width: DRAWER_WIDTH.STANDARD }">

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('listini.field_articolo') }}</label>
        <ArticoloLookup v-model="form.articolo_obj" />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_ba') }}</label>
        <BillingAccountLookup v-model="form.ba_obj" :placeholder="t('listini.select_ba')" />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_uom') }}</label>
        <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura" :placeholder="t('catalogo.select_uom')" />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_data_riferimento') }}</label>
        <DatePicker v-model="form.data_riferimento" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
      </div>
    </div>

    <div style="display: flex; justify-content: center; margin: 1rem 0;">
      <Button :label="t('listini.esegui_test')" icon="pi pi-search" @click="doTest"
        :loading="loading" :disabled="!canTest" />
    </div>

    <div v-if="result" style="padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.resolver_prezzo') }}</label>
          <strong style="font-size: 1.2rem;">{{ result.prezzo }}</strong>
        </div>
        <div class="form-field">
          <label>{{ t('listini.resolver_match') }}</label>
          <Tag :value="`${t('listini.resolver_livello')} ${result.match_level}`" severity="info" />
          <small>{{ matchLevelDescriptions[result.match_level] || '' }}</small>
        </div>
        <div class="form-field">
          <label>{{ t('listini.resolver_listino') }}</label>
          <span>{{ result.listino_codice }} — {{ result.listino_descrizione }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('listini.resolver_versione') }}</label>
          <span>{{ result.codice_versione || `#${result.listino_versione_id}` }}
            <Tag :value="result.versione_stato" size="small" :severity="result.versione_stato === 'ATTIVA' ? 'success' : 'secondary'" />
          </span>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="app-field-error" style="padding: 0.75rem; text-align: center;">
      {{ errorMsg }}
    </div>

    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" @click="close" />
    </template>
  </Dialog>
</template>
