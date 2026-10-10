<script setup>
// Scopo: Drawer dedicato per gestire la matrice utility (slot/override) di un emittente fiscale.
// Apre direttamente la gestione utility dalla riga lista, senza passare dal drawer dati.
// Wrappa EmittenteFiscaleUtilitiesTab che e' gia' autonomo (watch su emittenteId).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleUtilitiesTab from './EmittenteFiscaleUtilitiesTab.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'



const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  emittenteId: { type: Number, default: null },
  emittenteCodice: { type: String, default: '' },
  emittenteRagioneSociale: { type: String, default: '' },
  emittenteAttivo: { type: Boolean, default: true }
})


const emit = defineEmits(['update:visible', 'close'])

const title = computed(() => {
  const base = t('amministrazione.emittenti_fiscali.ut_drawer_title')
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
    :icon="MANAGE_ICONS.UTILITY"
    :width="DRAWER_WIDTH.XLARGE"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('close')"
  >
    <EmittenteFiscaleUtilitiesTab
      v-if="emittenteId"
      :emittente-id="emittenteId"
      :emittente-attivo="emittenteAttivo"
    />
  </AppDrawer>
</template>
