<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Scopo: La scheda dell'utente collegato, aperta dal suo badge nella topbar:
         chi e' (nome, utente, ruolo) e le azioni sul PROPRIO accesso — il
         cambio password e «Sicurezza dell'accesso».
  Note: ⭐ Decisione di Tid, 2026-10-03. Fino a quel giorno «Sicurezza» stava
        nel kebab delle preferenze (preferiti, lingua, tema), che non parlano
        dell'accesso, e il cambio password non aveva nessuna voce: chi voleva
        cambiarla di sua iniziativa non trovava la pagina. Il badge sta nel
        blocco «CHI» della topbar, ed e' la sede naturale.
        Il chiamante apre la scheda con `toggle(event)` (esposto).
-->
<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Popover from 'primevue/popover'
import Menu from 'primevue/menu'
import { useAuthStore } from '../../stores/auth'
import { useTabsStore } from '../../stores/tabs'
import { useConfirmAction } from '../composables/useConfirmAction'
import { MANAGE_ICONS } from '../constants'
import { menuItemClass } from '../utils/rowActions'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const tabs = useTabsStore()
const { confirmAction } = useConfirmAction()
const popover = ref(null)

// Stessa palette delle voci del kebab della topbar.
const VOCE = menuItemClass(undefined, 'app-menu-item-action')

const username = computed(() => auth.user?.utente?.username || '')
const ruolo = computed(() =>
  auth.ruoloApplicativo ? t(`auth.ruolo_applicativo.${auth.ruoloApplicativo}`) : ''
)

// Scopo: apre una pagina dell'accesso. Le due stanno FUORI da AppLayout
//        (famiglia login): entrarci smonta le schede, e le modifiche non
//        salvate andrebbero perse senza che nessuno lo dica. Con schede
//        modificate si chiede conferma, contandole (come il cambio emittente,
//        `EmittenteAttivoSelect`).
// ⭐ Una sede per le due pagine: fino al 2026-10-03 la conferma stava in
//    `AppTopbar` per la sola «Sicurezza».
function apriPaginaAccesso(nomeRotta, titolo) {
  popover.value?.hide()
  const vai = () => router.push({ name: nomeRotta })
  if (!tabs.hasDirtyTabs()) {
    vai()
    return
  }
  confirmAction({
    header: titolo,
    message: t('auth.account.uscita_conferma', {
      pagina: titolo,
      n: tabs.tabs.filter((x) => x.dirty).length,
    }),
    onAccept: vai,
  })
}

const azioni = computed(() => [
  {
    label: t('auth.change_password'),
    icon: MANAGE_ICONS.CAMBIO_PASSWORD,
    class: VOCE,
    command: () => apriPaginaAccesso('change-password', t('auth.change_password')),
  },
  {
    label: t('auth.secondo_fattore.titolo'),
    icon: MANAGE_ICONS.SICUREZZA_ACCESSO,
    class: VOCE,
    command: () => apriPaginaAccesso('sicurezza', t('auth.secondo_fattore.titolo')),
  },
])

function toggle(event) {
  popover.value?.toggle(event)
}

defineExpose({ toggle })
</script>

<template>
  <Popover ref="popover">
    <div class="app-scheda-utente">
      <div class="app-scheda-utente-nome">{{ auth.displayName }}</div>
      <div v-if="username" class="app-scheda-utente-riga">
        {{ t('auth.account.utente') }}: <span class="app-mono">{{ username }}</span>
      </div>
      <div v-if="ruolo" class="app-scheda-utente-riga">{{ ruolo }}</div>
      <div v-if="auth.isSuperAdmin" class="app-scheda-utente-riga">
        <i :class="MANAGE_ICONS.SUPER_ADMIN" aria-hidden="true" /> {{ t('auth.super_admin_badge') }}
      </div>
    </div>
    <Menu :model="azioni" class="app-scheda-utente-azioni" />
  </Popover>
</template>

<style scoped>
.app-scheda-utente {
  padding: 0.25rem 0.5rem 0.5rem;
  border-bottom: 1px solid var(--app-border-color);
  margin-bottom: 0.25rem;
  min-width: 14rem;
}

.app-scheda-utente-nome {
  font-weight: 600;
}

.app-scheda-utente-riga {
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}

.app-scheda-utente-azioni {
  border: none;
  padding: 0;
}
</style>
