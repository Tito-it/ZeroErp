<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la sezione «Lotti di magazzino» della SCHEDA ARTICOLO: il conteggio
//        dei lotti attivi, i due vuoti che vanno detti, e il sub-drawer di
//        gestione. La contribuisce magazzino al punto
//        `ARTICOLO_DRAWER_SEZIONI` (`magazzino/iscrizioni.js`): la scheda
//        articolo sta in catalogo, e catalogo non conosce magazzino — e'
//        `magazzino.lotti` a puntare a `catalogo.articoli`, non il contrario.
// Note: fino al 2026-09-26 questo pezzo stava scritto dentro ArticoloDrawer,
//       che importava drawer e API di magazzino.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import { listLotti } from '../api/magazzino'
import ArticoloLottiDrawer from './ArticoloLottiDrawer.vue'
import Button from 'primevue/button'

const props = defineProps({
  articoloId: { type: String, default: null },
  // Il form della scheda: ne servono `codice`, `gestito_a_magazzino`,
  // `requires_lotto`.
  articolo: { type: Object, default: null },
})

const { t } = useI18n()
const isReadonly = useInjectReadonly()

const drawerVisible = ref(false)
// Il conteggio dei lotti ATTIVI dell'articolo (`null` = non letto).
const conteggio = ref(null)

// Scopo: una pagina da una riga, il totale lo dice l'envelope. Solo se
//        l'articolo e' gestito a magazzino: un lotto ha senso su cio' che
//        movimenta.
async function caricaConteggio() {
  conteggio.value = null
  if (!props.articoloId || !props.articolo?.gestito_a_magazzino) return
  try {
    const res = await listLotti({ articolo_id: props.articoloId, attivo: true, limit: 1 })
    conteggio.value = res.data?.data?.count ?? 0
  } catch { conteggio.value = null }
}

watch(
  () => [props.articoloId, props.articolo?.gestito_a_magazzino],
  caricaConteggio,
  { immediate: true },
)
</script>

<template>
  <template v-if="articolo?.gestito_a_magazzino">
    <div class="app-drawer-section"><h4>{{ t('magazzino.lotti.titolo', { n: conteggio ?? '…' }) }}</h4></div>
    <div class="app-riepilogo-section">
      <div v-if="!articolo.requires_lotto" class="app-riepilogo-empty">{{ t('magazzino.lotti.articolo_non_per_lotti') }}</div>
      <div v-else-if="conteggio === 0" class="app-riepilogo-empty">{{ t('magazzino.lotti.nessun_lotto') }}</div>
      <Button v-if="!isReadonly"
        :label="t('magazzino.lotti.gestisci')" :icon="MANAGE_ICONS.LOTTO_MAGAZZINO"
        text size="small" class="app-action-btn app-escape mt-025"
        @click="drawerVisible = true" />
    </div>
  </template>

  <ArticoloLottiDrawer
    :visible="drawerVisible"
    @update:visible="v => { drawerVisible = v; if (!v) caricaConteggio() }"
    :articolo-id="articoloId"
    :articolo-codice="articolo?.codice ?? ''"
    :requires-lotto="articolo?.requires_lotto ?? true"
  />
</template>
