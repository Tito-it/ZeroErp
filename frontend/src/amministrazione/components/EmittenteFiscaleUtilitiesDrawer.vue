<script setup>
// Scopo: Drawer dedicato per gestire la matrice utility (slot/override) di un emittente fiscale.
// Apre direttamente la gestione utility dalla riga lista, senza passare dal drawer dati.
// Wrappa EmittenteFiscaleUtilitiesTab che e' gia' autonomo (watch su emittenteId).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleUtilitiesTab from './EmittenteFiscaleUtilitiesTab.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'

const { t } = useI18n()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  emittenteId: { type: Number, default: null },
  emittenteCodice: { type: String, default: '' },
  emittenteRagioneSociale: { type: String, default: '' },
  emittenteAttivo: { type: Boolean, default: true }
})

const emit = defineEmits(['update:visible', 'close'])

const title = computed(() => {
  const base = t('amm_emittenti_fiscali.ut_drawer_title')
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
    :style="{ width: DRAWER_WIDTH.XLARGE }"
  >
    <template #header>
      <DrawerTitle icon="pi pi-bolt" :title="title" />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
      <EmittenteFiscaleUtilitiesTab
        v-if="emittenteId"
        :emittente-id="emittenteId"
        :emittente-attivo="emittenteAttivo"
      />

      <div class="flex justify-end mt-4">
        <Button :label="t('common.close')" :icon="MANAGE_ICONS.CANCEL" text @click="close" />
      </div>
    </div>
  </Drawer>
</template>
