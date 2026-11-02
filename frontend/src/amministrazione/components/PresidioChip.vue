<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: un presidio A ZERO — letto, nessuna riga — ridotto a un chip: il
//        nome della vista e il suo conteggio. La descrizione (il commento
//        della vista: COSA controlla) si apre su richiesta, in un popover.
//
// ⭐ PERCHÉ IL CHIP E NON LA SCHEDA (rilievo di Tid, 2026-09-15). Il pannello
//    dei presidi rendeva per OGNI vista la descrizione intera. Quante viste e
//    quanto lunghe lo decide il catalogo DB, non questa schermata: al 15-09
//    erano 17 presidi e ~15.000 caratteri, cioè otto schermate di prosa sotto
//    una lista che non scrolla — e la lista dei processi finiva ad altezza
//    ZERO, senza nessun errore. Un presidio verde non ha righe da interpretare:
//    la sua descrizione serve a chi vuole sapere cosa controlla, e la trova
//    qui con un click. Quando invece si accende, la scheda intera la rende il
//    pannello (`PresidiProcessiPanel`), perché lì la spiegazione va letta
//    accanto alle righe.
// ⚠️ Un `Popover` PER CHIP, non uno solo commutato fra i bersagli: il cambio
//    di bersaglio mentre uno è aperto lo gestisce PrimeVue (click fuori →
//    chiude, click sul nuovo → apre) e non c'è nessuna logica di switch da
//    scrivere e da sbagliare. Da chiuso il popover non sta nel DOM.
// ⚠️ È un `Button`, non un `<span>` con `@click`: hit-area, focus da tastiera
//    e ruolo semantico corretti (stessa regola di `ErroreRigaInfo`).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Tag from 'primevue/tag'

defineProps({
  // La riga di `stato_presidi`: `vista`, `conteggio`, `descrizione`, ...
  presidio: { type: Object, required: true },
})

const { t } = useI18n()
const popover = ref(null)

function toggle(event) {
  popover.value?.toggle(event)
}
</script>

<template>
  <Button
    type="button"
    text
    size="small"
    severity="secondary"
    class="app-presidio-chip"
    :aria-label="t('amministrazione.processi.presidi_vedi_descrizione')"
    v-tooltip.top="t('amministrazione.processi.presidi_vedi_descrizione')"
    @click="toggle"
  >
    <span class="app-mono app-presidio-chip-nome">{{ presidio.vista }}</span>
    <Tag :value="String(presidio.conteggio)" severity="success" />
  </Button>

  <Popover ref="popover" :style="{ width: '460px' }">
    <h4 class="app-mono app-presidio-chip-titolo">{{ presidio.vista }}</h4>
    <!-- ⭐ La descrizione è quella che il team DB ha scritto sulla vista. Se
         manca lo si dice, e si dice DOVE va scritta: un popover vuoto
         sembrerebbe un caricamento mancato. -->
    <p class="app-presidio-chip-desc">
      {{ presidio.descrizione || t('amministrazione.processi.presidi_senza_descrizione') }}
    </p>
  </Popover>
</template>

<style scoped>
/* Layout locale del chip: non è un pattern di pagina, non va in main.css. */
.app-presidio-chip {
  gap: 0.4rem;
  padding: 0.2rem 0.5rem;
  border: 1px solid var(--app-border-color);
  border-radius: var(--p-content-border-radius);
}
.app-presidio-chip-nome { font-size: 0.8rem; }
.app-presidio-chip-titolo { margin: 0 0 0.5rem; }
.app-presidio-chip-desc { margin: 0; font-size: 0.85rem; line-height: 1.45; }
</style>
