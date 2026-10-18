<script setup>
// Scopo: Dialog di emissione preventivo (BOZZA -> EMESSO). Wrapper sottile
//        sul building block generico `DocumentoEmissioneDialog` (modalita'
//        advances-state): mostra l'anteprima del documento che verra'
//        generato + consente di allegare file; alla Conferma il parent
//        chiama l'endpoint emetti multipart (cambia stato + genera +
//        allegati, atomico). Mirror di `OffertaEmissioneDialog`.
import { useI18n } from 'vue-i18n'
import DocumentoEmissioneDialog from '../../../../documenti/components/DocumentoEmissioneDialog.vue'
import { SORGENTE_CODES } from '../../../../documenti/constants'
import { displayDate } from '../../../../core/utils/date'

const props = defineProps({
  visible: Boolean,
  preventivo: { type: Object, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()
</script>

<template>
  <DocumentoEmissioneDialog
    :visible="props.visible"
    :sorgente-code="SORGENTE_CODES.PREVENTIVO"
    :sorgente-id="props.preventivo?.id ?? null"
    advances-state
    :header="t('vendite.preventivi.emissione_titolo')"
    :confirm-label="t('vendite.preventivi.emissione_conferma')"
    :loading="props.loading"
    @update:visible="(val) => emit('update:visible', val)"
    @confirm="(payload) => emit('confirm', payload)"
  >
    <template #riepilogo>
      <p>{{ t('vendite.preventivi.emissione_messaggio') }}</p>

      <div v-if="preventivo" style="margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.4rem;">
        <div v-if="preventivo.billing_account_codice || preventivo.billing_account_ragione_sociale">
          <strong>{{ t('vendite.preventivi.field_billing_account') }}:</strong>
          {{ preventivo.billing_account_ragione_sociale || preventivo.billing_account_codice }}
          <span
            v-if="preventivo.billing_account_codice && preventivo.billing_account_ragione_sociale"
            class="app-text-muted"
          >
            · {{ preventivo.billing_account_codice }}
          </span>
        </div>
        <div>
          <strong>{{ t('vendite.preventivi.field_validita_dal') }}:</strong>
          {{ displayDate(preventivo.validita_dal) }}
          <span v-if="preventivo.validita_al">
            → {{ displayDate(preventivo.validita_al) }}
          </span>
        </div>
      </div>
    </template>
  </DocumentoEmissioneDialog>
</template>
