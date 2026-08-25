<script setup>
// Scopo: pagina della LISTA fatture — host dell'elenco configurabile e del
//        drawer di consultazione.
//
// ⚠️ SOLA LETTURA per costruzione: la fattura si produce dalla pipeline di
//    fatturazione e oltre EMESSA le righe sono congelate a DB. Qui non esiste
//    nessun verbo di creazione o modifica, e il drawer è quello di
//    consultazione già in servizio — la lista gli dà finalmente una casa.
import { ref } from 'vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import FattureSearchTable from '../components/FattureSearchTable.vue'
import FatturaDrawer from '../components/FatturaDrawer.vue'

// Permessi: livello area `vendite` + livello oggetto `fattura` — lo stesso
// `model_permission` che il BE dichiara su lista, dettaglio e giornale.
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.FATTURA)

const drawerVisible = ref(false)
const fatturaId = ref(null)

// Scopo: click su una riga → apre il documento in consultazione.
// ⚠️ La riga della lista viene dalla vista canonica: la chiave è `id`.
function apriFattura(riga) {
  if (!riga?.id) return
  fatturaId.value = riga.id
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <FattureSearchTable @row-click="apriFattura" />

    <FatturaDrawer
      v-model:visible="drawerVisible"
      :fattura-id="fatturaId"
    />
  </div>
</template>
