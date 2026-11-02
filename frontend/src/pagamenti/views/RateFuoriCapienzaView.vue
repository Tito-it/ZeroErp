<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina delle RATE FUORI CAPIENZA — l'elenco che rende onesta la
//        forzatura.
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import RateFuoriCapienzaSearchTable from '../components/RateFuoriCapienzaSearchTable.vue'

useReadonlyMode(READONLY_DOMAINS.PAGAMENTI)
</script>

<template>
  <div class="app-page">
    <RateFuoriCapienzaSearchTable />
  </div>
</template>
