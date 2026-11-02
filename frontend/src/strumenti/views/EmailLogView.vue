<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Le email dell'operatore: quelle che ha scritto lui e quelle del suo
//        reparto, dentro le aziende del suo perimetro. Dominio Strumenti, voce
//        senza area; rotta BE `/core/email/log/` (skip d'area: la apre ogni
//        operatore).
// ⭐ Chi vede quale mail lo decide la RLS per ambito
//    (brief-db-email-visibilita-per-ambito), non questa schermata. Lista,
//    filtri e celle sono il BB `core/components/EmailLogLista`, lo stesso del
//    log dell'amministratore: qui c'e' solo la porta (lo store).
// ⛔ Nessun `useReadonlyMode`: la voce non ha un'area da leggere, e la lista
//    e' di sola consultazione per natura.
import EmailLogLista from '../../core/components/EmailLogLista.vue'
import { useEmailLogOperatoreStore } from '../stores/emailLog'

const store = useEmailLogOperatoreStore()
</script>

<template>
  <EmailLogLista :store="store" />
</template>
