<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA QUADRATURA di una distinta, a TRE esiti — dichiarato, totale
//        delle righe e scarto (quadra · non quadra · non si applica) — in
//        UNA sede per le due superfici che la mostrano: il drawer della
//        distinta e il dialog di validazione.
//
// Estratto il 2026-09-19 (regola del 2, ok Tid): i tre computed e i tre campi
// erano identici in `DistintaDrawer` e nel nuovo `ValidaDistintaDialog`. Due
// copie della stessa lettura divergono al primo ritocco — e quella che si
// sfila e' quella che l'operatore ha davanti quando preme «Valida».
//
// ⚠️ `importo_dichiarato` NULL non e' zero: significa «non e' stato dichiarato
//    niente», quindi la quadratura NON SI APPLICA. Mostrare 0,00 direbbe
//    «quadra» di una distinta che nessuno ha mai quadrato. Tre esiti, non due.
//
// ⭐ I campi PROPRI di ciascun chiamante (registrabili/totali e «di cui non
//    nostre» nel drawer, righe totali nel dialog) entrano dallo slot di
//    default, dentro la stessa griglia: qui stanno solo i tre che le due
//    superfici devono leggere IDENTICI.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

import { formatCurrency } from '../../core/utils/format'

const props = defineProps({
  // Il dettaglio della distinta (`importo_dichiarato`, `totale_righe`,
  // `scarto_dichiarato`). `null` = niente da mostrare.
  distinta: { type: [Object, null], default: null },
})

const { t } = useI18n()

const quadraturaApplicabile = computed(() => props.distinta?.importo_dichiarato != null)
const scarto = computed(() => props.distinta?.scarto_dichiarato ?? null)
const quadra = computed(
  () => quadraturaApplicabile.value && Number(scarto.value || 0) === 0,
)
</script>

<template>
  <div v-if="distinta" class="form-grid">
    <div class="app-drawer-section">
      <h4>{{ t('pagamenti.distinte.sezione_quadratura') }}</h4>
    </div>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('pagamenti.distinte.col_importo_dichiarato') }}</label>
        <span>{{ formatCurrency(distinta.importo_dichiarato) }}</span>
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.distinte.col_totale_righe') }}</label>
        <span>{{ formatCurrency(distinta.totale_righe) }}</span>
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.distinte.col_scarto_dichiarato') }}</label>
        <!-- ⭐ Tre esiti, non due: quadra · non quadra · non si applica. -->
        <span v-if="!quadraturaApplicabile" class="app-text-muted">
          {{ t('pagamenti.distinte.quadratura_non_applicabile') }}
        </span>
        <Tag v-else-if="!quadra" :value="formatCurrency(scarto)" severity="warn" />
        <Tag v-else :value="t('pagamenti.distinte.quadra')" severity="success" />
      </div>
      <!-- I campi propri del chiamante, nella stessa griglia. -->
      <slot />
    </div>
  </div>
</template>
