<script setup>
// Scopo: Il log email dell'amministratore: TUTTE le mail, dalla porta
//        `/amm-software/email-log/` (super admin).
// ⭐ Lista, filtri e celle stanno nel BB `core/components/EmailLogLista`
//    (regola del 2, 2026-09-26): lo usa anche il dominio Personale per le
//    email dell'operatore. Qui resta cio' che e' della SCHERMATA — la porta
//    (lo store) e la modalita' di Amm. Software.
// Email logs e' read-only: nessuno store emette EMAIL_LOGS, quindi non serve
// ascoltare eventi cross-tab.
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import EmailLogLista from '../../core/components/EmailLogLista.vue'
import { useEmailLogsStore } from '../stores/emailLogs'

useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const store = useEmailLogsStore()
</script>

<template>
  <EmailLogLista :store="store" />
</template>
