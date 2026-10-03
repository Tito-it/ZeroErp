<script setup>
// Scopo: Drawer dedicato per gestire i mapping Billing Account di un emittente fiscale.
// Apre direttamente la gestione BA dalla riga lista, senza passare dal drawer dati.
// Wrappa EmittenteFiscaleBillingAccountTab che e' gia' autonomo (watch su emittenteId).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleBillingAccountTab from './EmittenteFiscaleBillingAccountTab.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'



const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  emittenteId: { type: Number, default: null },
  emittenteCodice: { type: String, default: '' },
  emittenteRagioneSociale: { type: String, default: '' }
})


const emit = defineEmits(['update:visible', 'close'])

const title = computed(() => {
  const base = t('amministrazione.emittenti_fiscali.ba_drawer_title')
  const rs = props.emittenteRagioneSociale
  return rs ? `${base} — ${rs}` : base
})

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="title"
    :icon="MANAGE_ICONS.BILLING_ACCOUNT"
    :width="DRAWER_WIDTH.COMPLEX"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('close')"
  >
    <EmittenteFiscaleBillingAccountTab
      v-if="emittenteId"
      :emittente-id="emittenteId"
    />
  </AppDrawer>
</template>
