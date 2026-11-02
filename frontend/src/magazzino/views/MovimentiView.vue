<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina del REGISTRO dei movimenti di magazzino — host della lista
//        configurabile. Sola lettura: nessun drawer, nessun dialog.
//
// ⚠️ Il permesso e' di AREA (`magazzino`): il dominio non ha un livello
//    oggetto a catalogo, quindi non si dichiara un `modelName` che il backend
//    non presidia.
//
// --- Deep-link dal documento POSTED --------------------------------------
// `?inventario_id=…` (oppure `?rettifica_id=…`): apre il registro GIA'
// filtrato sui movimenti nati dalle righe di quel documento.
//
// ⚠️ In `onActivated`, non solo al mount: la vista vive sotto KeepAlive
//    (AppLayout, `:key="$route.path"`), quindi un deep-link su una vista gia'
//    in cache non rimonta niente e un'applicazione fatta al mount non
//    scatterebbe mai (memoria feedback_keepalive_onactivated).
// ⚠️ Idempotente, e la query si PULISCE dopo averla applicata: lasciarla
//    significherebbe ri-filtrare il registro ogni volta che si torna su questa
//    vista, anche dopo che l'operatore ha tolto il filtro a mano.
// ⚠️ Azzera il floor `data_da`: un documento registrato tre mesi fa ha
//    movimenti piu' vecchi del floor, e col floor il deep-link mostrerebbe una
//    lista VUOTA per un documento che ha scritto — cioe' un'affermazione falsa.
import { onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import MovimentiSearchTable from '../components/MovimentiSearchTable.vue'
import { useMovimentiStore } from '../stores/movimenti'
import { FAMIGLIE } from '../vocabolari'

useReadonlyMode(READONLY_DOMAINS.MAGAZZINO)

const route = useRoute()
const router = useRouter()
const store = useMovimentiStore()

// I due parametri di deep-link, che sono anche i nomi dei filtri nello store.
const CHIAVI_DEEP_LINK = Object.values(FAMIGLIE).map((f) => f.filtroMovimenti)

function numeroQuery(chiave) {
  const raw = route.query[chiave]
  const n = Number(raw)
  return raw != null && raw !== '' && Number.isInteger(n) && n > 0 ? n : null
}

function applicaDeepLink() {
  if (route.name !== 'magazzino-movimenti') return
  const valori = Object.fromEntries(CHIAVI_DEEP_LINK.map((k) => [k, numeroQuery(k)]))
  if (Object.values(valori).every((v) => v == null)) return

  // I due filtri sono ALTERNATIVI (un movimento nasce da una riga sola): il
  // primo valorizzato vince, l'altro si azzera.
  const scelta = CHIAVI_DEEP_LINK.find((k) => valori[k] != null)
  for (const k of CHIAVI_DEEP_LINK) store.filters[k] = k === scelta ? valori[k] : null
  store.filters.data_da = null
  store.filters.offset = 0

  // ⛔ Nessuna fetch qui: la decide la lista, che osserva i filtri di
  //    documento e ricarica — se e' montata. Se non lo e' ancora, li trova
  //    gia' impostati al proprio mount.
  const resto = { ...route.query }
  for (const k of CHIAVI_DEEP_LINK) delete resto[k]
  router.replace({ query: resto })
}

onActivated(applicaDeepLink)
</script>

<template>
  <div class="app-page">
    <MovimentiSearchTable />
  </div>
</template>
