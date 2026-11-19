<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Gli indirizzi che il cambio di natura chiede a UN titolare (il
// soggetto, o uno dei suoi ruoli): R-7 di brief-db-fornitore-privato-indirizzi
// §13.4. Un form multi-tipo (`IndirizzoSoggettoForm`) con i soli tipi che la
// lettura dei mancanti elenca: il tipo richiesto, obbligatorio, e il suo
// ripiego come alternativa. Il drawer del soggetto ne monta uno per titolare e
// raccoglie i payload con `toPayloadArray()`.
// ⭐ Che cosa manca lo dice il DB (`motivi_cambio_natura`, la stessa sede dei
//    guard degli obbligatori): qui non si ricalcola, si propone.

import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIndirizzoSoggettoForm } from '../composables/useIndirizzoSoggettoForm'
import { collegaIndirizzoSoggettoForm } from '../composables/collegaIndirizzoSoggettoForm'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'

const props = defineProps({
  // Il titolo del gruppo («Soggetto», «Ruolo Fornitore»), gia' composto.
  titolo: { type: String, required: true },
  // Le righe di `indirizzi_mancanti` di questo titolare.
  mancanti: { type: Array, required: true },
  campiErrati: { type: Array, default: () => [] },
})

const { t } = useI18n()
const indirizzo = useIndirizzoSoggettoForm()
const legameIndirizzo = collegaIndirizzoSoggettoForm(indirizzo)

// Scopo: I tipi del form dalle righe dei mancanti: ogni tipo richiesto
//        (obbligatorio) e il suo ripiego (alternativa), una volta sola.
function tipiDaMancanti(righe) {
  const tipi = new Map()
  for (const m of righe) {
    tipi.set(m.tipo_indirizzo_codice_interno, {
      codice_interno: m.tipo_indirizzo_codice_interno,
      descrizione: m.tipo_indirizzo_descrizione,
      obbligatorio: true,
    })
  }
  for (const m of righe) {
    const codice = m.ripiego_tipo_indirizzo_codice_interno
    if (codice && !tipi.has(codice)) {
      tipi.set(codice, { codice_interno: codice, descrizione: m.ripiego_tipo_indirizzo_descrizione, obbligatorio: false })
    }
  }
  return [...tipi.values()]
}

// ⚠️ Si segue la FIRMA dei tipi (richiesto e ripiego), non l'array: i motivi
//    si rileggono a ogni P.IVA o flag digitato e dopo un salvataggio rifiutato,
//    e ogni lettura porta un array nuovo con gli stessi tipi. `setMatrice`
//    svuota gli indirizzi compilati e torna al primo obbligatorio: seguendo
//    l'array, l'operatore perdeva cio' che aveva scritto.
const firmaTipi = computed(() => props.mancanti
  .map(m => `${m.tipo_indirizzo_codice_interno}|${m.ripiego_tipo_indirizzo_codice_interno ?? ''}`)
  .join(','))
watch(firmaTipi, () => indirizzo.setMatrice(tipiDaMancanti(props.mancanti)), { immediate: true })

defineExpose({ toPayloadArray: indirizzo.toPayloadArray })
</script>

<template>
  <div class="app-drawer-section">
    <h4>{{ titolo }}</h4>
  </div>
  <ul class="mt-025">
    <li v-for="m in mancanti" :key="m.tipo_indirizzo_id">
      <template v-if="m.ripiego_tipo_indirizzo_codice_interno">
        {{ t('anagrafiche.soggetti.cambio_natura_indirizzo_o_ripiego', {
          tipo: m.tipo_indirizzo_descrizione, ripiego: m.ripiego_tipo_indirizzo_descrizione,
        }) }}
      </template>
      <template v-else>{{ m.tipo_indirizzo_descrizione }}</template>
    </li>
  </ul>
  <IndirizzoSoggettoForm
    v-bind="legameIndirizzo"
    :campi-errati="campiErrati"
    :mostra-auto-clone="false"
  />
</template>
