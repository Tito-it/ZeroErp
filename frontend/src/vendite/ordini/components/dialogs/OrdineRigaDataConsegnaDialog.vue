<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: cambia la data di consegna confermata di UNA riga d'ordine, anche
//        dopo la conferma (brief-db-testata-dopo-emissione, fase 1, R-FE-2).
//        La promessa si decide alla conferma e puo' cambiare dopo, mentre la
//        riga non si modifica piu': per questo e' un verbo suo e non il form
//        di riga.
//
// ⛔ Il dialog non decide QUANDO si puo': l'azione che lo apre e' spenta col
//    motivo dalla capability `can_edit_data_consegna_confermata` del dettaglio,
//    e il rifiuto vero resta del DB (lock delle righe, `E_RIGA_DOC_NON_BOZZA`).
// ⚠️ Il campo vuoto e' una risposta legittima: toglie la promessa (`null`).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import AppDialog from '../../../../core/components/AppDialog.vue'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useFotografiaDialog } from '../../../../core/composables/useFotografiaDialog'
import { DATE_FORMAT } from '../../../../core/constants'
import { parseIsoDate, toDateString } from '../../../../core/utils/date'
import { useOrdiniStore } from '../../stores/ordini'

const props = defineProps({
  visible: { type: Boolean, required: true },
  ordineId: { type: Number, required: true },
  // La riga della lista: `id`, `riga_nr`, `descrizione`, `data_consegna_confermata`.
  riga: { type: Object, default: null },
  // ⚠️ Readonly PURO del chiamante (permessi / split), mai quello combinato
  //    con lo stato: il dialog vive su un ordine confermato, cioe' dove il
  //    drawer e' in protect, e senza l'override `FormFooter` nasconderebbe il
  //    pulsante di conferma (stessa ragione di `AccreditoAnnullaDialog`).
  readonly: { type: Boolean, default: false },
  // La data del documento (ISO, dal dettaglio): il minimo del calendario
  // delle date di consegna. Solo un aiuto: il rifiuto vero e' del DB
  // (`E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE`).
  dataDocumento: { type: String, default: null },
})
const emit = defineEmits(['update:visible', 'salvata'])

const { t } = useI18n()
const { execute, loading } = useApiHandler()
// Lo store scrive e avvisa le liste (frontend-standards §«Producer cross-tab»).
const store = useOrdiniStore()

const dataScelta = ref(null)
const minDataConsegna = computed(() => parseIsoDate(props.dataDocumento))

// All'apertura, la data che la riga porta oggi. Dichiarato PRIMA della
// fotografia: il suo watch fissa dopo questo giro, e vede il valore iniziale.
watch(() => [props.visible, props.riga], ([visibile]) => {
  if (!visibile) return
  const attuale = props.riga?.data_consegna_confermata
  dataScelta.value = attuale ? parseIsoDate(attuale) : null
}, { immediate: true })

// D-14: uscire con una data cambiata chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(
  () => ({ dataScelta: dataScelta.value }),
  { visibile: () => props.visible },
)

async function salva() {
  if (!props.riga) return
  const data = dataScelta.value ? toDateString(dataScelta.value) : null
  const res = await execute(
    () => store.cambiaDataConsegnaConfermata(props.ordineId, props.riga.id, data),
    { successMessage: t('vendite.ordini.data_consegna_confermata_salvata') },
  )
  if (res === null) return
  emit('update:visible', false)
  emit('salvata')
}
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    width="sm"
    :header="t('vendite.ordini.data_consegna_confermata_titolo')"
    :loading="loading"
    :readonly="readonly"
    @update:visible="emit('update:visible', $event)"
    @save="salva"
  >
    <p v-if="riga" class="app-text-muted">
      {{ t('vendite.ordini.data_consegna_confermata_riga', {
        riga_nr: riga.riga_nr,
        descrizione: riga.descrizione || '',
      }) }}
    </p>
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_data_consegna_confermata') }}</label>
        <DatePicker
          v-model="dataScelta"
          :date-format="DATE_FORMAT"
          :min-date="minDataConsegna"
          show-icon
          show-button-bar
        />
        <small class="app-text-muted">{{ t('vendite.ordini.data_consegna_confermata_hint') }}</small>
      </div>
    </div>
  </AppDialog>
</template>
