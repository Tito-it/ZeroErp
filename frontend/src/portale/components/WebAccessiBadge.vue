<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il badge «accessi web» nell'ANTEPRIMA DEL SOGGETTO (§1.6): quante
//        vesti web sono ATTIVE (portale + shop per un cliente, solo portale
//        per un fornitore) e, al click, il drawer degli accessi. Lo
//        contribuisce portale al punto `SOGGETTO_ANTEPRIMA_BADGE`
//        (`portale/iscrizioni.js`): gli accessi puntano al soggetto, e
//        anagrafiche non conosce portale.
// Note: fino al 2026-09-26 stava scritto dentro SoggettoPreviewBadges, che
//       importava drawer e API di portale.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getStatoAccessiCliente, getStatoAccessiFornitore } from '../api/portaleAdminApi'
import WebAccessiDrawer from './WebAccessiDrawer.vue'
import Button from 'primevue/button'
import { MANAGE_ICONS, STATO_VESTE } from '../../core/constants'

// Il punto passa tutte le prop dell'anteprima: qui se ne leggono tre.
defineOptions({ inheritAttrs: false })

const props = defineProps({
  // 'cliente' | 'fornitore': senza tipo e id il badge non compare (l'anteprima
  // si usa anche dove gli accessi web non si applicano).
  entitaTipoWeb: { type: String, default: null },
  entitaIdWeb: { type: [Number, String], default: null },
  emailInizialeWeb: { type: String, default: '' },
  // Anteprima di creazione: il drawer si apre in sola lettura.
  preview: { type: Boolean, default: false },
})

const { t } = useI18n()
const attivo = computed(() => ['cliente', 'fornitore'].includes(props.entitaTipoWeb) && !!props.entitaIdWeb)
const conteggio = ref(0)
const loading = ref(false)
const drawerVisible = ref(false)

// Scopo: quante vesti sono ATTIVE. Un invito in volo (PENDING) non conta:
//        l'utente non ha ancora completato l'attivazione.
async function caricaConteggio() {
  if (!attivo.value) return
  loading.value = true
  try {
    const fn = props.entitaTipoWeb === 'cliente' ? getStatoAccessiCliente : getStatoAccessiFornitore
    const data = (await fn(props.entitaIdWeb))?.data?.data || {}
    conteggio.value = (data.portale?.stato === STATO_VESTE.ATTIVO ? 1 : 0) + (data.shop?.stato === STATO_VESTE.ATTIVO ? 1 : 0)
  } catch {
    conteggio.value = 0
  } finally {
    loading.value = false
  }
}

watch(() => [props.entitaTipoWeb, props.entitaIdWeb], caricaConteggio, { immediate: true })
</script>

<template>
  <template v-if="attivo">
    <Button
      outlined :icon="MANAGE_ICONS.ACCESSI_WEB"
      :label="`${conteggio} ${t('portale.accessi_web.badge_label')}`"
      :loading="loading"
      class="app-badge-anteprima"
      @click="drawerVisible = true"
    />
    <WebAccessiDrawer
      :visible="drawerVisible"
      @update:visible="v => { drawerVisible = v; if (!v) caricaConteggio() }"
      :entita-tipo="entitaTipoWeb"
      :entita-id="entitaIdWeb"
      :email-iniziale="emailInizialeWeb"
      :readonly="preview"
    />
  </template>
</template>
