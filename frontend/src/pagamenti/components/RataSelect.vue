<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA TENDINA DELLE RATE DI UNA FATTURA, col saldo accanto — il pezzo
//        che risponde a «dove ci sta questo incasso?».
//
// ⭐ Estratto il 2026-09-14 alla SECONDA occorrenza (regola del 2, ok Tid):
//    l'abbinamento di una riga e la nascita della riga con la destinazione
//    (D16) fanno la stessa identica domanda. Era dichiarato in attesa della
//    seconda in §5.3 del piano BE/FE.
//
// ⭐ TRE stati e non due (`useLetturaTreStati`): «rate presenti» · «la fattura
//    non ha rate» · «non le ho lette». L'ultimo NON si spaccia per il secondo:
//    «questa fattura non ha rate» e' un'affermazione, e detta al posto di
//    «non lo so» e' falsa.
// ⚠️ La rata e' FACOLTATIVA (la riga del fondo fattura ha fattura si' e rata
//    no) e la nota lo dice: senza, l'operatore crede di doverne scegliere una
//    e su un fondo fattura si blocca.
// ⚠️ Il residuo NEGATIVO si dice a parole, mai come «-120,00», che si legge
//    come un guasto — e la frase segue la NATURA del documento (`etichette.js`):
//    «di troppo» su una fattura, «da rimborsare» su una nota di credito, che
//    dal 2026-09-17 (P-5) ha la sua rata negativa.
// ⛔ Emette la rata INTERA con `select`: chi propone un importo ha bisogno del
//    residuo, non del solo id — e non deve ricercarla nell'elenco.
//
// ⭐ LA SCELTA ARRIVATA DA FUORI SOPRAVVIVE (Q-2 del piano, 2026-09-17). Il
//    picker delle rate consegna al form fattura E rata insieme; il `watch`
//    sulla fattura ricarica le rate e — fino a quel giorno — azzerava la scelta
//    a prescindere, quindi la rata scelta nel picker spariva un istante dopo.
//    Ora, se il `modelValue` in arrivo e' fra le rate del documento appena
//    caricato, si TIENE e si emette `select` con la rata intera (coi numeri
//    della tendina); si azzera solo se non c'e' — cioe' quando era di un altro
//    documento, che e' il caso per cui l'azzeramento esiste.
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'

import { RISULTATI, useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { listRateFattura } from '../api/pagamenti'
import { useEtichettePagamenti } from '../etichette'

const props = defineProps({
  // La fattura di cui mostrare le rate; `null` = tendina spenta.
  fatturaId: { type: [Number, null], default: null },
  // La NATURA del documento (`natura_doc_codice_interno`): decide come si
  // legge un residuo negativo. `null` vale «fattura», il default a DB.
  naturaDocCodice: { type: [String, null], default: null },
  // `scadenza_id` della rata scelta.
  modelValue: { type: [Number, null], default: null },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'select'])

const { t } = useI18n()

const {
  dati: rate,
  caricati: rateCaricate,
  errore: erroreRate,
  loading,
  carica: caricaRate,
  azzera: azzeraRate,
} = useLetturaTreStati((id) => listRateFattura(id), { estrai: RISULTATI, vuoto: [] })

// Scopo: cambia la fattura, cambiano le rate — e la scelta di prima vale
//        solo se e' una rata di QUESTO documento (Q-2).
// ⚠️ La scelta si legge PRIMA di caricare e si decide DOPO: `caricaRate`
//    risponde `null` quando una fattura piu' recente l'ha scavalcata, e in quel
//    caso non si tocca niente — decidera' l'ultima.
watch(
  () => props.fatturaId,
  async (id) => {
    const preselezionata = props.modelValue
    azzeraRate()
    if (id == null) {
      emit('update:modelValue', null)
      emit('select', null)
      return
    }
    const elenco = await caricaRate(id)
    if (elenco == null) return
    const tenuta = preselezionata != null
      ? elenco.find((r) => r.scadenza_id === preselezionata) || null
      : null
    if (tenuta) {
      emit('select', tenuta)
      return
    }
    emit('update:modelValue', null)
    emit('select', null)
  },
  { immediate: true },
)

// Scopo: «Rata n · scadenza · importo · residuo». ⭐ L'importo della rata
//        accanto al residuo (D19-b): «restano 400» senza «di 1.000» non dice
//        se e' la prima rata o l'ultima, e chi digita un incasso lo vuole
//        sapere prima di confermare. La forma vive in `etichette.js`: qui,
//        nel blocco «Destinazione» e nella tabella delle righe e' la stessa.
// ⚠️ `residuo ?? 0`: la tendina mostra SEMPRE il residuo, anche a zero — e'
//    la colonna che dice «qui non ci sta piu' niente».
const { rata: etichettaBase } = useEtichettePagamenti()
function etichettaRata(r) {
  return etichettaBase({
    ...r,
    residuo: r.residuo ?? 0,
    natura_doc_codice_interno: props.naturaDocCodice,
  })
}

function onChange(scadenzaId) {
  emit('update:modelValue', scadenzaId)
  emit('select', rate.value.find((r) => r.scadenza_id === scadenzaId) || null)
}

defineExpose({ loading })
</script>

<template>
  <div class="form-field">
    <label>{{ t('pagamenti.rata.campo') }}</label>
    <Select
      :model-value="modelValue"
      :options="rate"
      :option-label="etichettaRata"
      option-value="scadenza_id"
      :placeholder="t('pagamenti.rata.placeholder')"
      :disabled="disabled || fatturaId == null || !rate.length"
      :loading="loading"
      show-clear
      @update:model-value="onChange"
    />
    <!-- ⛔ Tre casi, non due: rate presenti · nessuna rata · non lette.
         L'ultimo NON si spaccia per il secondo. -->
    <small v-if="erroreRate" class="app-text-muted">
      {{ t('pagamenti.rata.non_lette') }}
    </small>
    <small v-else-if="rateCaricate && !rate.length" class="app-text-muted">
      {{ t('pagamenti.rata.nessuna') }}
    </small>
    <small v-else class="app-text-muted">{{ t('pagamenti.rata.facoltativa') }}</small>
  </div>
</template>
