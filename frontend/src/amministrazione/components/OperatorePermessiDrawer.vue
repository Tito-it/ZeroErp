<script setup>
// Scopo: Drawer dedicato alla gestione permessi di un operatore.
// Riusa il componente OperatorePermessiTab (building block condiviso con
// OperatoreDrawer). Serve per l'azione rapida "gestisci permessi" dalla
// riga della lista operatori, senza dover aprire il drawer di modifica
// completo e navigare fino al tab.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import OperatorePermessiTab from './OperatorePermessiTab.vue'
import Drawer from 'primevue/drawer'



const { t } = useI18n()
const store = useOperatoriStore()
const injectedReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  authUserId: { type: Number, default: null },
  // Sola lettura CUMULATIVA con quella iniettata (standard drawer admin).
  readonly: { type: Boolean, default: false }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const isReadonly = computed(() => props.readonly || injectedReadonly.value)
const emit = defineEmits(['update:visible'])

// Titolo drawer che include il nome operatore quando il dettaglio e' gia'
// stato caricato da OperatorePermessiTab. Fallback al titolo generico.
const drawerTitle = computed(() => {
  const base = t('amministrazione.permessi_operatore_title')
  const u = store.currentOperatore
  if (!u || u.auth_user_id !== props.authUserId) return base
  const fullName = [u.soggetto_cognome || u.last_name, u.soggetto_nome || u.first_name]
    .filter(Boolean)
    .join(' ')
    .trim()
  const label = fullName || u.username
  return label ? `${base} — ${label}` : base
})
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.XLARGE }"
    @update:visible="v => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="t('common.edit')"
        :title="drawerTitle"
        icon="pi pi-shield"
      />
    </template>

    <!-- ⭐ `XLARGE` e non `COMPLEX`: la costante lo dice da sé — «matrici
         parametri-per-entità (utility, slot/override)». Da quando il pannello
         mostra TUTTE le voci del catalogo con ereditato, override e stato,
         questo drawer è una di quelle matrici, come il gemello
         `EmittenteFiscaleUtilitiesDrawer` che l'ha inaugurata.
         ℹ️ Su viewport più stretti non esce dallo schermo: `.p-drawer` ha
         `max-width: 100vw` globale, quindi la larghezza è una preferenza.
         `app-drawer-content` aggiunge gap, tipografia e l'`overflow-x: auto`
         che serve alle tabelle larghe. -->
    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <OperatorePermessiTab
        v-if="props.authUserId"
        :auth-user-id="props.authUserId"
        :readonly="isReadonly"
      />
    </div>
  </Drawer>
</template>
