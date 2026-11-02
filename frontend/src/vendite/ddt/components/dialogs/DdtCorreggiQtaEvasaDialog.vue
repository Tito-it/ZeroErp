<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: «Correggi quantita' evasa» — la quantita' di una riga di DDT legata a
//        un ordine o a un reso da ri-consegnare (D-2 di
//        brief-db-ddt-righe-evase-dall-ordine). Sulla riga evasa articolo, UoM
//        e quantita' sono fermi: la quantita' cambia solo da qui, e con lei il
//        legame e lo stato dell'ordine, nella stessa operazione.
// ⛔ Nessuna regola ricopiata: bozza, residuo dell'ordine, copertura del reso e
//    quantita' positiva li giudica il DB, e il suo rifiuto arriva col toast
//    (`E_QTA_SUPERA_RESIDUO`, `E_QTA_NON_POSITIVA` col campo). Qui si chiede
//    solo un numero.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'

import AppDialog from '../../../../core/components/AppDialog.vue'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useFotografiaDialog } from '../../../../core/composables/useFotografiaDialog'
import { useDdtStore } from '../../stores/ddt'

const props = defineProps({
  visible: { type: Boolean, default: false },
  ddtId: { type: Number, required: true },
  // La riga della lista (`vw_ddt_righe_dettaglio`): id, riga_nr, qta_operativa,
  // uom_codice.
  riga: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'corretta'])

const { t } = useI18n()
const store = useDdtStore()
const { execute, loading, campiErrati } = useApiHandler()

const qta = ref(null)

watch(() => props.visible, (aperto) => {
  if (!aperto) return
  qta.value = props.riga?.qta_operativa != null ? Number(props.riga.qta_operativa) : null
}, { immediate: true })

async function onSalva() {
  const esito = await execute(
    () => store.correggiQtaEvasa(props.ddtId, props.riga.id, qta.value),
    { successMessage: t('vendite.ddt.correggi_qta_evasa_ok') },
  )
  if (esito === null) return
  emit('corretta', esito)
  emit('update:visible', false)
}

// D-14: uscire con una quantita' scritta chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ qta: qta.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t('vendite.ddt.correggi_qta_evasa')"
    width="sm"
    :loading="loading"
    :save-disabled="!riga || qta == null"
    :save-label="t('vendite.ddt.correggi_qta_evasa')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSalva"
    @cancel="emit('update:visible', false)"
  >
    <div v-if="riga" class="form-grid">
      <!-- Che cosa cambia insieme alla riga: l'operatore deve saperlo prima. -->
      <Message severity="info" :closable="false">
        {{ t('vendite.ddt.correggi_qta_evasa_spiegazione', { riga: riga.riga_nr }) }}
      </Message>
      <div class="form-field">
        <label>{{ t('vendite.ddt.correggi_qta_evasa_nuova') }} *</label>
        <InputNumber v-model="qta" :min-fraction-digits="2" :max-fraction-digits="6"
          :suffix="riga.uom_codice ? ` ${riga.uom_codice}` : undefined"
          :invalid="campiErrati.includes('qta_operativa')" autofocus />
      </div>
    </div>
  </AppDialog>
</template>
