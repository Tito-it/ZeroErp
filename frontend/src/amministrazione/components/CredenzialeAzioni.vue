<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: La sezione «Credenziale» di un drawer dell'area Accessi: le azioni che
//        valgono per TUTTE le vesti della persona — il blocco dell'amministratore
//        e il secondo fattore (brief-db-be-fe-area-accessi, A-4/A-5).
// Note: ⭐ Regola del 2: la montano il drawer dell'operatore e quello degli
//       altri accessi (simmetria A-5). Le due parti restano componenti propri
//       perche' ognuna ha il suo stato e i suoi gesti; qui c'e' solo la sezione
//       che le mette insieme, una volta. Le azioni sono immediate, non passano
//       dal Salva del drawer.
import { useI18n } from 'vue-i18n'
import CredenzialeBlocco from './CredenzialeBlocco.vue'
import CredenzialeSecondoFattore from './CredenzialeSecondoFattore.vue'

defineProps({
  authUserId: { type: Number, required: true },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])

const { t } = useI18n()
</script>

<template>
  <div>
    <div class="app-drawer-section"><h4>{{ t('amministrazione.accessi.sezione_credenziale') }}</h4></div>
    <div class="form-grid">
      <CredenzialeBlocco :auth-user-id="authUserId" :readonly="readonly" @changed="emit('changed')" />
      <CredenzialeSecondoFattore :auth-user-id="authUserId" :readonly="readonly" />
    </div>
  </div>
</template>
