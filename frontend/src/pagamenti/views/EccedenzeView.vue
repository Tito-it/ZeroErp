<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina delle ECCEDENZE DA SISTEMARE — i documenti su cui e' entrato
//        piu' del dovuto, raggruppati per cliente perche' e' li' che si decide.
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import EccedenzeSearchTable from '../components/EccedenzeSearchTable.vue'

useReadonlyMode('pagamenti')
</script>

<template>
  <div class="app-page">
    <EccedenzeSearchTable />
  </div>
</template>
