<script setup>
// Scopo: Drawer dedicato per gestire i mapping Billing Account di un emittente fiscale.
// Apre direttamente la gestione BA dalla riga lista, senza passare dal drawer dati.
// Wrappa EmittenteFiscaleBillingAccountTab che e' gia' autonomo (watch su emittenteId).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleBillingAccountTab from './EmittenteFiscaleBillingAccountTab.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'



const { t } = useI18n()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  emittenteId: { type: Number, default: null },
  emittenteCodice: { type: String, default: '' },
  emittenteRagioneSociale: { type: String, default: '' }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'close'])

const title = computed(() => {
  const base = t('amministrazione.emittenti_fiscali.ba_drawer_title')
  const rs = props.emittenteRagioneSociale
  return rs ? `${base} — ${rs}` : base
})

function close() {
  emit('update:visible', false)
  emit('close')
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :icon="MANAGE_ICONS.BILLING_ACCOUNT" :title="title" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <EmittenteFiscaleBillingAccountTab
        v-if="emittenteId"
        :emittente-id="emittenteId"
      />

      <div class="flex justify-end mt-4">
        <Button :label="t('common.close')" :icon="MANAGE_ICONS.CANCEL" text @click="close" />
      </div>
    </div>
  </Drawer>
</template>
