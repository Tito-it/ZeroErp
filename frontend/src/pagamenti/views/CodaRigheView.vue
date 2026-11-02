<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina della CODA DEL RICONCILIATORE.
//
// ⭐ DUE VOCI DI MENU, UNA PAGINA (Q-4 -> c): «da abbinare» e «sospese» sono la
//    stessa lista, e quale delle due si apra lo dice la ROTTA
//    (`meta.coda`) — non uno stato interno. Cosi' le due porte sono
//    deep-linkabili e il tab del browser ricorda quale stavi lavorando.
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import CodaRigheSearchTable from '../components/CodaRigheSearchTable.vue'
import { CODE } from '../vocabolari'

useReadonlyMode(READONLY_DOMAINS.PAGAMENTI)

const route = useRoute()
// ⚠️ Il ripiego e' `DA_ABBINARE` e non «tutte»: se la rotta non dicesse niente,
//    aprire TUTTE mostrerebbe anche le righe gia' lavorate — una coda piu'
//    lunga del vero, che e' il modo in cui una coda smette di essere una coda.
const coda = computed(() => route.meta?.coda || CODE.DA_ABBINARE)
</script>

<template>
  <div class="app-page">
    <CodaRigheSearchTable :coda="coda" />
  </div>
</template>
