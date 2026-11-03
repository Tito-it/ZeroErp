<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il link «Informazioni» in fondo alle pagine di accesso (quelle con
//        `.login-page`): apre `InformazioniDialog` (licenza e codice
//        sorgente), e chiunque arrivi all'applicazione lo vede prima di
//        entrare (AGPL-3.0 §13). Dentro l'app lo stesso dialog e' una voce del
//        kebab utente (`AppTopbar`).
// ⚠️ Va messo come figlio DIRETTO di `.login-page`, fuori dal cerchio
//    `.login-card`: e' posizionato in fondo alla pagina (auth-pages.css).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InformazioniDialog from './InformazioniDialog.vue'
import { MANAGE_ICONS } from '../constants'

const { t } = useI18n()
const visibile = ref(false)
</script>

<template>
  <button type="button" class="login-informazioni" @click="visibile = true">
    <i :class="MANAGE_ICONS.INFORMAZIONI" aria-hidden="true" />
    {{ t('informazioni.titolo') }}
  </button>
  <InformazioniDialog v-model:visible="visibile" />
</template>
