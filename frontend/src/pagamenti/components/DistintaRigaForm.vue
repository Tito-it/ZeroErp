<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form di UNA riga contabile — l'atto con cui si digita il denaro
//        arrivato: quanto, quando, e con quale riferimento il canale lo nomina.
//
// ⚠️ Qui si digitano i FATTI della riga, non il suo percorso: l'abbinamento alla
//    fattura e alla rata, la sospensione e lo scarto sono verbi propri e stanno
//    nelle azioni di riga. Mescolarli nel form significherebbe far cambiare
//    stato a una riga mentre si corregge un importo.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'

import { useApiHandler } from '../../core/composables/useApiHandler'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString, parseIsoDate } from '../../core/utils/date'
import { aggiornaRiga, creaRiga } from '../api/pagamenti'

const props = defineProps({
  contabileId: { type: [Number, null], default: null },
  // La riga in modifica; `null` = nuova.
  riga: { type: [Object, null], default: null },
})
const emit = defineEmits(['salvata', 'annulla'])

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

const isEdit = computed(() => props.riga?.id != null)
const form = ref(defaultForm())

function defaultForm() {
  return {
    importo: null,
    riferimento_ente: '',
    // ⭐ La data del pagamento nasce OGGI: si sta digitando il denaro di
    //    giornata. ⚠️ Ma NON e' la data contabile della distinta — un incasso
    //    puo' essere di ieri e finire sul foglio di oggi.
    data_pagamento: new Date(),
    data_valuta: null,
  }
}

watch(
  () => props.riga,
  (r) => {
    form.value = r
      ? {
          importo: r.importo != null ? Number(r.importo) : null,
          riferimento_ente: r.riferimento_ente || '',
          data_pagamento: parseIsoDate(r.data_pagamento),
          data_valuta: parseIsoDate(r.data_valuta),
        }
      : defaultForm()
  },
  { immediate: true },
)

// ⚠️ `!= null` e non un test di verita': lo ZERO non e' un importo valido qui
//    (una riga da zero non e' denaro arrivato), ma va rifiutato dal DATABASE con
//    la sua frase — non nascosto disabilitando il pulsante, che lascerebbe
//    l'operatore senza sapere perche'.
const canSave = computed(() => form.value.importo != null)

async function onSalva() {
  const payload = {
    importo: form.value.importo,
    data_pagamento: toDateString(form.value.data_pagamento),
  }
  // ⚠️ Stringa vuota -> NULL, mai `''`: il backend normalizza a NULL e una
  //    stringa vuota a database sarebbe un valore diverso da «non c'e'».
  payload.riferimento_ente = form.value.riferimento_ente?.trim() || null
  payload.data_valuta = form.value.data_valuta ? toDateString(form.value.data_valuta) : null

  const esito = await execute(
    () => (isEdit.value
      ? aggiornaRiga(props.riga.id, payload)
      : creaRiga(props.contabileId, payload)),
    { successMessage: t(isEdit.value ? 'pagamenti.righe.aggiornata' : 'pagamenti.righe.creata') },
  )
  if (esito !== null) emit('salvata')
}
</script>

<template>
  <div class="app-drawer-section">
    <h4>{{ t(isEdit ? 'pagamenti.righe.titolo_modifica' : 'pagamenti.righe.titolo_nuova') }}</h4>
  </div>

  <div class="form-grid">
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_importo') }}</label>
        <InputNumber
          v-model="form.importo"
          mode="currency"
          currency="EUR"
          locale="it-IT"
          :invalid="campiErrati.includes('importo')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_riferimento_ente') }}</label>
        <!-- ⭐ E' il riferimento con cui IL CANALE nomina il pagamento: e' cio'
             che permette di ritrovarlo quando il cliente telefona. -->
        <InputText
          v-model="form.riferimento_ente"
          :invalid="campiErrati.includes('riferimento_ente')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_data_pagamento') }}</label>
        <DatePicker
          v-model="form.data_pagamento"
          :date-format="DATE_FORMAT"
          show-icon
          :invalid="campiErrati.includes('data_pagamento')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_data_valuta') }}</label>
        <DatePicker
          v-model="form.data_valuta"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          :invalid="campiErrati.includes('data_valuta')"
        />
      </div>
    </div>

    <div class="app-form-footer">
      <Button
        text
        size="small"
        :label="t('common.cancel')"
        icon="pi pi-arrow-left"
        @click="emit('annulla')"
      />
      <Button
        size="small"
        :label="t('common.save')"
        icon="pi pi-check"
        :loading="loading"
        :disabled="!canSave"
        @click="onSalva"
      />
    </div>
  </div>
</template>
