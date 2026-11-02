<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer dei registri di numerazione di un emittente fiscale. Apre la
//        gestione dalla riga della lista emittenti, come i due gemelli
//        (billing account e utilities). Wrappa `EmittenteFiscaleRegistriTab`,
//        che è già autonomo (watch sul padre dentro `useDrawerTabLista`).
//
// ⚠️ NOTA DI SCOSTAMENTO DAL BRIEF (§FE-1). Il brief diceva «un terzo TAB
//    dentro il drawer dell'emittente», descrivendo i due esistenti come tab. In
//    realtà non sono tab: sono due DRAWER a sé, aperti dal kebab della riga
//    nella lista emittenti — `EmittenteFiscaleBillingAccountDrawer` e
//    `…UtilitiesDrawer`. Il terzo segue quello che c'è, non quello che il brief
//    ricordava: una forma diversa dai fratelli sarebbe una terza convenzione
//    nella stessa schermata.
//
// ⭐ QUELLO CHE PASSA E' IL SOGGETTO-RUOLO, non la PK. `registri_fatturazione`
//    si aggancia a `emittente_soggetto_ruolo_id`, e la lista emittenti quella
//    colonna la porta già in riga. Passare la PK non solleverebbe niente:
//    filtrerebbe su numeri che non corrispondono e la lista uscirebbe vuota,
//    cioè «questo emittente non ha registri» (`feedback_emittente_pk_vs_soggetto_ruolo`).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleRegistriTab from './EmittenteFiscaleRegistriTab.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'



const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  emittenteSoggettoRuoloId: { type: Number, default: null },
  emittenteRagioneSociale: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'close'])

const titolo = computed(() => {
  const base = t('amministrazione.registri_numerazione.drawer_lista_title')
  return props.emittenteRagioneSociale
    ? `${base} — ${props.emittenteRagioneSociale}`
    : base
})

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="titolo"
    :icon="MANAGE_ICONS.NUMERAZIONE"
    :width="DRAWER_WIDTH.XLARGE"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('close')"
  >
    <EmittenteFiscaleRegistriTab
      v-if="emittenteSoggettoRuoloId"
      :emittente-soggetto-ruolo-id="emittenteSoggettoRuoloId"
      :emittente-ragione-sociale="emittenteRagioneSociale"
    />
  </AppDrawer>
</template>
