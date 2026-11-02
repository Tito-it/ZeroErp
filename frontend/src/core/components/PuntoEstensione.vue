<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: monta i COMPONENTI contribuiti a un punto di estensione
//        (`core/estensioni.js`), in ordine, passando a ciascuno tutte le
//        prop ricevute (`$attrs`). Chi dichiara il punto non sa chi ci
//        contribuisce; il contributo decide da se' se mostrarsi.
// Note: nessun contributo = nessun nodo a video.
import { computed, defineAsyncComponent, markRaw } from 'vue'
import { contributi } from '../estensioni'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  punto: { type: String, required: true },
})

// Il componente di ogni contributo, caricato su richiesta (i contributi
// stanno nei chunk dei loro domini, non nel bundle d'avvio). Chi ospita il
// punto lo precarica con `precaricaPunto`, o la sezione arriva dopo il resto.
// ⚠️ Un chunk che non si carica (deploy nuovo con la tab vecchia aperta) non
//    rende niente: almeno resta scritto QUALE contributo e' mancato.
const voci = computed(() => contributi(props.punto).map(c => ({
  chiave: c.chiave,
  componente: markRaw(defineAsyncComponent({
    loader: c.componente,
    onError(err, _retry, fail) {
      console.error(`Punto «${props.punto}»: contributo «${c.chiave}» non caricato`, err)
      fail()
    },
  })),
})))
</script>

<template>
  <component :is="v.componente" v-for="v in voci" :key="v.chiave" v-bind="$attrs" />
</template>
