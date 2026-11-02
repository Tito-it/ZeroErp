<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: «AGGIORNA DATE DI CONSEGNA» — una data scritta su piu' righe di un
//        documento di vendita (brief-db-date-consegna-righe-in-blocco, D-2):
//        quale colonna, quale data, e se su TUTTE le righe o SOLO su quelle
//        senza data. Condiviso da ordine e preventivo (regola del 2).
//
// ⭐ Le colonne le passa il chiamante, gia' filtrate dalle capability
//    (`useDateConsegnaRighe`): il dialog non sa quali date ha il documento.
// ⭐ «Tutte» sovrascrive le date scritte: prima si chiede al backend quante
//    righe toccherebbe (`anteprima`, lo stesso UPDATE annullato dal backend)
//    e si conferma col numero. Se il DB rifiuta, il 409 arriva gia' li' e la
//    domanda di conferma non parte.
// ⚠️ Le righe d'ordine gia' spedite si SALTANO (D-7): la data con cui la merce
//    e' partita resta. Il toast dice quante.
// ⛔ Nessuna regola qui: se una riga non si puo' toccare lo dice il DB (409),
//    e il gesto non scrive niente — e' un UPDATE solo.
// ⛔ Nessuna chiamata diretta all'API: si scrive con l'azione dello store del
//    dominio (`invia`), che avvisa le liste (frontend-standards §«Producer
//    cross-tab»). Un dialog che chiamasse l'API lascerebbe ferme le liste.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import AppDialog from '../../../core/components/AppDialog.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useFotografiaDialog } from '../../../core/composables/useFotografiaDialog'
import { useNotify } from '../../../core/composables/useNotify'
import { DATE_FORMAT } from '../../../core/constants'
import { parseIsoDate, toDateString } from '../../../core/utils/date'
import { MODALITA_DATE_CONSEGNA } from './dateConsegnaApi'

const props = defineProps({
  visible: { type: Boolean, required: true },
  // L'azione dello store del dominio: `(payload) => Promise<response>`
  // (es. `(p) => store.aggiornaDateConsegna(id, p)`). Ritorna la response:
  // l'esito ha una chiave `data`, e `execute` la spacchetterebbe.
  invia: { type: Function, required: true },
  // Le colonne scrivibili ora: `[{ colonna, label }]` (`useDateConsegnaRighe`).
  colonne: { type: Array, default: () => [] },
  // ⚠️ Readonly PURO del chiamante (permessi / split), mai quello combinato
  //    con lo stato: sull'ordine confermato il drawer e' in protect, e la data
  //    confermata si scrive lo stesso (come `OrdineRigaDataConsegnaDialog`).
  readonly: { type: Boolean, default: false },
  // La data del documento (ISO, dal dettaglio): il minimo del calendario
  // della data. Solo un aiuto: il rifiuto vero e' del DB, e in blocco
  // rifiuta il gesto intero (`E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE`).
  dataDocumento: { type: String, default: null },
})
const emit = defineEmits(['update:visible', 'aggiornate'])

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const colonna = ref(null)
const dataScelta = ref(null)
const minDataConsegna = computed(() => parseIsoDate(props.dataDocumento))
const modalita = ref(MODALITA_DATE_CONSEGNA.SOLO_VUOTE)

const modalitaOpzioni = computed(() => [
  { value: MODALITA_DATE_CONSEGNA.SOLO_VUOTE, label: t('vendite.date_consegna.modalita_solo_vuote') },
  { value: MODALITA_DATE_CONSEGNA.TUTTE, label: t('vendite.date_consegna.modalita_tutte') },
])

// All'apertura si riparte puliti: la prima colonna proposta, nessuna data,
// la modalita' che non sovrascrive niente. Dichiarato PRIMA della fotografia:
// il suo watch fissa dopo questo giro, e vede i valori iniziali.
watch(() => props.visible, (visibile) => {
  if (!visibile) return
  colonna.value = props.colonne[0]?.colonna ?? null
  dataScelta.value = null
  modalita.value = MODALITA_DATE_CONSEGNA.SOLO_VUOTE
}, { immediate: true })

// D-14: uscire con qualcosa di scelto chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(
  () => ({ colonna: colonna.value, dataScelta: dataScelta.value, modalita: modalita.value }),
  { visibile: () => props.visible },
)

const pronto = computed(() => Boolean(colonna.value && dataScelta.value && modalita.value))

function payload(anteprima) {
  return {
    colonna: colonna.value,
    data: toDateString(dataScelta.value),
    modalita: modalita.value,
    anteprima,
  }
}

async function scrivi() {
  const esito = await execute(
    () => props.invia(payload(false)),
  )
  if (esito === null) return
  // Il messaggio dice i numeri: quante righe, e quante saltate perche' spedite.
  notify.success(esito.saltate_spedite > 0
    ? t('vendite.date_consegna.esito_con_saltate', {
        aggiornate: esito.aggiornate, saltate: esito.saltate_spedite,
      })
    : t('vendite.date_consegna.esito', { aggiornate: esito.aggiornate }))
  emit('update:visible', false)
  emit('aggiornate', esito)
}

async function salva() {
  if (!pronto.value) return
  if (modalita.value !== MODALITA_DATE_CONSEGNA.TUTTE) {
    await scrivi()
    return
  }
  // «Tutte» sovrascrive: prima il numero, poi la conferma.
  const conta = await execute(
    () => props.invia(payload(true)),
  )
  if (conta === null) return
  confirmAction({
    header: t('vendite.date_consegna.conferma_titolo'),
    message: conta.saltate_spedite > 0
      ? t('vendite.date_consegna.conferma_tutte_con_saltate', {
          aggiornate: conta.aggiornate, saltate: conta.saltate_spedite,
        })
      : t('vendite.date_consegna.conferma_tutte', { aggiornate: conta.aggiornate }),
    onAccept: scrivi,
  })
}
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    width="sm"
    :header="t('vendite.date_consegna.titolo')"
    :loading="loading"
    :readonly="readonly"
    :save-disabled="!pronto"
    @update:visible="emit('update:visible', $event)"
    @save="salva"
  >
    <p class="app-text-muted">{{ t('vendite.date_consegna.intro') }}</p>
    <div class="form-grid">
      <div v-if="colonne.length > 1" class="form-field">
        <label for="date-consegna-colonna">{{ t('vendite.date_consegna.colonna') }}</label>
        <Select
          v-model="colonna"
          input-id="date-consegna-colonna"
          :options="colonne"
          option-label="label"
          option-value="colonna"
        />
      </div>
      <div v-else-if="colonne.length === 1" class="form-field">
        <label>{{ t('vendite.date_consegna.colonna') }}</label>
        <span>{{ colonne[0].label }}</span>
      </div>
      <div class="form-field">
        <label for="date-consegna-data">{{ t('vendite.date_consegna.data') }}</label>
        <DatePicker
          v-model="dataScelta"
          input-id="date-consegna-data"
          :date-format="DATE_FORMAT"
          :min-date="minDataConsegna"
          show-icon
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.date_consegna.modalita') }}</label>
        <div v-for="opt in modalitaOpzioni" :key="opt.value">
          <RadioButton
            v-model="modalita"
            :value="opt.value"
            :input-id="`date-consegna-modalita-${opt.value}`"
          />
          <label :for="`date-consegna-modalita-${opt.value}`" class="ml-05">{{ opt.label }}</label>
        </div>
      </div>
    </div>
  </AppDialog>
</template>
