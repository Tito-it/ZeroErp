<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il campo del CODICE del secondo fattore (TOTP): il codice dell'app di
//        autenticazione oppure, se il chiamante lo consente, un codice di
//        recupero, col link che commuta fra i due e azzera quanto scritto.
//        Nasce il 2026-10-02 (regola del 2, decisione di Tid): lo stesso
//        campo stava nel secondo passo del login (LoginView) e tre volte in
//        SicurezzaView (conferma della configurazione, rigenerazione codici,
//        disattivazione).
//
// Uso:
//   <CodiceSecondoFattoreInput v-model:codice="codice" v-model:usa-recupero="usaRecupero"
//                              consenti-recupero :disabled="loading" autofocus>
//     <Button type="submit" ... />
//   </CodiceSecondoFattoreInput>
//   ... chiamata(provaSecondoFattore(codice, usaRecupero))   // utils/provaSecondoFattore
//
// ⭐ Lo slot di default sta FRA il campo e il link «usa codice di recupero»:
//    nei form del secondo fattore il pulsante d'invio sta li', e il link
//    sotto. Senza slot il link finirebbe attaccato al campo, sopra il pulsante.
// ⭐ `autofocus` e' gestito qui (ref + nextTick al mount), non con l'attributo
//    HTML: il campo nasce dentro un `v-if` (il form del secondo passo), e
//    l'`autofocus` HTML vale solo al caricamento della pagina — su un nodo
//    inserito dopo non e' affidabile.
// ⚠️ Gli attributi non dichiarati (es. `id`) vanno sull'`InputText`, non sul
//    contenitore: il componente ha piu' radici.

import { nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  // Mostra il link che passa al codice di recupero (secondo passo del login,
  // disattivazione). Senza, il campo chiede solo il codice dell'app.
  consentiRecupero: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  autofocus: { type: Boolean, default: false },
})

const codice = defineModel('codice', { type: String, default: '' })
const usaRecupero = defineModel('usaRecupero', { type: Boolean, default: false })

const { t } = useI18n()
const campo = ref(null)

onMounted(async () => {
  if (!props.autofocus) return
  await nextTick()
  campo.value?.$el?.focus?.()
})

// Scopo: passa fra codice dell'app e codice di recupero; quanto scritto vale
//        per l'altro tipo di codice, quindi si azzera.
function commuta() {
  usaRecupero.value = !usaRecupero.value
  codice.value = ''
}
</script>

<template>
  <div class="field">
    <InputText
      ref="campo"
      v-bind="$attrs"
      v-model="codice"
      :disabled="disabled"
      :placeholder="usaRecupero ? t('auth.secondo_fattore.codice_recupero') : t('auth.secondo_fattore.codice')"
      :aria-label="usaRecupero ? t('auth.secondo_fattore.codice_recupero') : t('auth.secondo_fattore.codice')"
      :inputmode="usaRecupero ? 'text' : 'numeric'"
      autocomplete="one-time-code"
      fluid
    />
  </div>
  <slot />
  <a v-if="consentiRecupero" href="#" class="forgot-link" @click.prevent="commuta">
    {{ usaRecupero ? t('auth.secondo_fattore.usa_codice') : t('auth.secondo_fattore.usa_recupero') }}
  </a>
</template>
