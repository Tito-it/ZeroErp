<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la sezione «Saldo» del DRAWER DELLA FATTURA — «questa fattura e'
//        stata pagata?». La contribuisce pagamenti al punto
//        `FATTURA_DRAWER_SEZIONI` (`pagamenti/iscrizioni.js`): i movimenti
//        puntano alla fattura, e vendite non conosce pagamenti.
//
// ⭐ DUE numeri e non tre (Q-6): il RESIDUO in grande e IN LAVORAZIONE in
//    piccolo. L'«incassato» risponde a una domanda di tesoreria, non a
//    «questa fattura e' a posto?»: il pannello lo sa mostrare — e' la stessa
//    base — ma questa schermata non lo accende.
// ⚠️ Il pannello legge da se' e si rilegge al cambio di fattura: il drawer e'
//    un'istanza sola riusata cambiando `fatturaId`.
// Note: fino al 2026-09-26 stava scritto dentro FatturaDrawer, che importava
//       pannello e composable di pagamenti.
import { useI18n } from 'vue-i18n'
import SaldoPanel from './SaldoPanel.vue'
import { LIVELLO } from '../composables/useSaldi'

defineOptions({ inheritAttrs: false })

defineProps({
  fatturaId: { type: [Number, null], default: null },
})

const { t } = useI18n()
</script>

<template>
  <div class="app-drawer-section"><h4>{{ t('pagamenti.saldi.sezione') }}</h4></div>
  <SaldoPanel
    :livello="LIVELLO.DOCUMENTO"
    :riferimento-id="fatturaId"
    :mostra="['residuo', 'in_lavorazione']"
  />
</template>
