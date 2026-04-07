<script setup>
// Scopo: Tab autonomo riusabile per la gestione del mapping BA -> emittente fiscale.
// Mostra elenco mapping (default + specifici), consente add tramite BillingAccountLookup
// e creazione del default globale (one-shot). Reagisce automaticamente al cambio
// di emittenteId e puo' essere montato sia in TabView del drawer principale sia
// in un drawer dedicato richiamato dalla riga della lista.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
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

const selectedBA = ref(null)
const adding = ref(false)

// Carica i mapping BA dell'emittente quando l'id cambia.
// Le store action void vanno chiamate direttamente: useApiHandler.execute serve
// solo dove serve l'unwrap envelope (POST/PATCH che restituiscono il dato salvato).
watch(() => props.emittenteId, async (id) => {
  if (!id) {
    store.clearBillingAccountMappings()
    return
  }
  try {
    await store.fetchBillingAccountMappings(id)
  } catch (e) {
    store.clearBillingAccountMappings()
  }
}, { immediate: true })

// Computed reattivo: il pulsante "default" si disabilita appena il default esiste.
const hasDefault = computed(() =>
  store.billingAccountMappings.some(m => m.is_default)
)

async function addSpecificMapping() {
  if (!selectedBA.value?.id) {
    notify.warn(t('amm_emittenti_fiscali.ba_select_required'))
    return
  }
  adding.value = true
  try {
    const result = await execute(
      () => store.addBillingAccountMapping(props.emittenteId, { billing_account_id: selectedBA.value.id }),
      { successMessage: t('amm_emittenti_fiscali.ba_added') }
    )
    if (result !== null) selectedBA.value = null
  } finally {
    adding.value = false
  }
}

// Crea il default globale (record one-shot, billing_account_id = null).
async function addDefaultMapping() {
  if (hasDefault.value) {
    notify.warn(t('amm_emittenti_fiscali.ba_default_exists'))
    return
  }
  await execute(
    () => store.addBillingAccountMapping(props.emittenteId, {}),
    { successMessage: t('amm_emittenti_fiscali.ba_default_added') }
  )
}

// Elimina un mapping previa conferma. Il default e' protetto da un trigger DB.
function removeMapping(row) {
  confirmAction({
    title: t('common.confirm'),
    message: row.is_default
      ? t('amm_emittenti_fiscali.ba_remove_default_confirm')
      : t('amm_emittenti_fiscali.ba_remove_confirm', { codice: row.billing_account_codice || '-' }),
    danger: true,
    onAccept: () => {
      execute(
        () => store.removeBillingAccountMapping(props.emittenteId, row.id),
        { successMessage: t('amm_emittenti_fiscali.ba_removed') }
      )
    }
  })
}
</script>

<template>
  <div class="app-tab-content">
    <Message severity="info" :closable="false" class="mb-3">
      {{ t('amm_emittenti_fiscali.ba_help') }}
    </Message>

    <div v-if="!isReadonly" class="form-grid-2col mb-3">
      <BillingAccountLookup
        v-model="selectedBA"
        :placeholder="t('amm_emittenti_fiscali.ba_search_placeholder')"
      />
      <div class="flex gap-2">
        <Button
          :label="t('amm_emittenti_fiscali.ba_add_specific')"
          icon="pi pi-plus"
          :loading="adding"
          :disabled="!selectedBA?.id"
          @click="addSpecificMapping"
        />
        <Button
          :label="t('amm_emittenti_fiscali.ba_add_default')"
          icon="pi pi-star"
          severity="secondary"
          :disabled="hasDefault"
          @click="addDefaultMapping"
        />
      </div>
    </div>

    <DataTable :value="store.billingAccountMappings" striped-rows class="app-datatable">
      <Column :header="t('amm_emittenti_fiscali.ba_col_default')" style="width: 110px;">
        <template #body="{ data }">
          <Badge v-if="data.is_default" :value="t('common.default')" severity="info" />
        </template>
      </Column>
      <Column field="billing_account_codice" :header="t('amm_emittenti_fiscali.ba_col_codice')">
        <template #body="{ data }">
          {{ data.billing_account_codice || '—' }}
        </template>
      </Column>
      <Column field="billing_account_ragione_sociale" :header="t('amm_emittenti_fiscali.ba_col_ragione_sociale')">
        <template #body="{ data }">
          {{ data.billing_account_ragione_sociale || t('amm_emittenti_fiscali.ba_default_label') }}
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('amm.col_actions')" style="width: 70px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <Button
            icon="pi pi-trash"
            text rounded size="small"
            severity="danger"
            v-tooltip.bottom="t('common.delete')"
            @click="removeMapping(data)"
          />
        </template>
      </Column>
      <template #empty>
        <div class="app-empty">{{ t('amm_emittenti_fiscali.ba_empty') }}</div>
      </template>
    </DataTable>
  </div>
</template>
