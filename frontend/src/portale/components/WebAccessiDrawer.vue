<script setup>
// Scopo: Drawer autonomo "Accessi Web" per cliente/fornitore. Aperto
// via pulsante `pi-globe` in `SoggettoPreviewBadges`, sostituisce il
// pannello `PortaleAccessoPanel` che prima era montato inline nei
// drawer padre. Incapsula portale + shop (shop solo per cliente) con
// azioni invita/reinvia/disattiva + visualizzazione username/email
// dell'auth_user collegato.
//
// Usa il pattern drawer autonomi (feedback_drawer_autonomi):
// ereditarieta' readonly dal padre via inject, DrawerFooter closeOnly,
// DrawerTitle standard.
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import PortaleAccessoPanel from './PortaleAccessoPanel.vue'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { DRAWER_WIDTH } from '../../core/constants'

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

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="t('portale.accessi_web.drawer_action')"
        :title="t('portale.accessi_web.title')"
        icon="pi pi-globe"
      />
    </template>

    <div class="app-drawer-content">
      <PortaleAccessoPanel
        :entita-tipo="props.entitaTipo"
        :entita-id="props.entitaId"
        :email-iniziale="props.emailIniziale"
        :readonly="isReadonly()"
        @stato-cambiato="$emit('stato-cambiato')"
      />

      <DrawerFooter close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>
