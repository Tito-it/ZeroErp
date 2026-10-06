<script setup>
// Scopo: Il log email dell'amministratore: TUTTE le mail, dalla porta
//        `/amm-software/email-log/` (super admin).
// ⭐ Lista, filtri e celle stanno nel BB `core/components/EmailLogLista`
//    (regola del 2, 2026-09-26): lo usa anche il dominio Personale per le
//    email dell'operatore. Qui resta cio' che e' della SCHERMATA — la porta
//    (lo store).
// ⚠️ Niente `useReadonlyMode` (tolto il 2026-10-06, Tid): dietro `adminOnly`
//    di Strumenti → Diagnostica non c'e' un livello d'area da risolvere — o
//    sei super admin, o non arrivi alla pagina. Come ProcessiAutomaticiListView.
// Email logs e' read-only: nessuno store emette EMAIL_LOGS, quindi non serve
// ascoltare eventi cross-tab.
import EmailLogLista from '../../core/components/EmailLogLista.vue'
import { useEmailLogsStore } from '../stores/emailLogs'

const store = useEmailLogsStore()
</script>

<template>
  <EmailLogLista :store="store" />
</template>
