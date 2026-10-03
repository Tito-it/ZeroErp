<script setup>
// Scopo: Drawer autonomo "Accessi Web" per cliente/fornitore. Aperto
// via pulsante `pi-globe` in `SoggettoPreviewBadges`, sostituisce il
// pannello `PortaleAccessoPanel` che prima era montato inline nei
// drawer padre. Incapsula portale + shop (shop solo per cliente) con
// azioni invita/reinvia/disattiva + visualizzazione username/email
// dell'auth_user collegato.
//
// Usa il pattern drawer autonomi (feedback_drawer_autonomi):
// ereditarieta' readonly dal padre via inject, chrome di AppDrawer con
// footer «Chiudi».
import { useI18n } from 'vue-i18n'
import AppDrawer from '../../core/components/AppDrawer.vue'
import PortaleAccessoPanel from './PortaleAccessoPanel.vue'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'

const { t } = useI18n()
const injectedReadonly = useInjectReadonly()

const props = defineProps({
  visible: { type: Boolean, required: true },
  entitaTipo: {
    type: String,
    required: true,
    validator: v => ['cliente', 'fornitore'].includes(v),
  },
  entitaId: { type: [Number, String], required: true },
  emailIniziale: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'stato-cambiato'])

// Scopo: readonly effettivo = prop || inject (pattern readonly cumulativo).
function isReadonly() {
  return props.readonly || injectedReadonly.value
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('portale.accessi_web.title')"
    :icon="MANAGE_ICONS.ACCESSI_WEB"
    :action="t('portale.accessi_web.drawer_action')"
    :width="DRAWER_WIDTH.STANDARD"
    :proteggi-corpo="false"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <PortaleAccessoPanel
      :entita-tipo="props.entitaTipo"
      :entita-id="props.entitaId"
      :email-iniziale="props.emailIniziale"
      :readonly="isReadonly()"
      @stato-cambiato="$emit('stato-cambiato')"
    />
  </AppDrawer>
</template>
