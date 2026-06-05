<script setup>
// Scopo: Dialog di emissione ordine (DRAFT -> CONFERMATO). Wrapper sottile sul
//        building block generico `DocumentoEmissioneDialog` (modalita'
//        advances-state): mostra l'anteprima del documento che verra' generato
//        + consente di allegare file; alla Conferma il parent chiama l'endpoint
//        /emetti/ multipart (conferma + genera documento + allegati, atomico
//        lato BE — ApiOrdineEmetti). Mirror di PreventivoEmissioneDialog.
import { useI18n } from 'vue-i18n'
import DocumentoEmissioneDialog from '../../../../documenti/components/DocumentoEmissioneDialog.vue'
import { SORGENTE_CODES } from '../../../../documenti/constants'
import { displayDate } from '../../../../core/utils/date'

const props = defineProps({
  visible: Boolean,
  ordine: { type: Object, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()
</script>

<template>
  <DocumentoEmissioneDialog
    :visible="props.visible"
    :sorgente-code="SORGENTE_CODES.ORDINE_VENDITA"
    :sorgente-id="props.ordine?.id ?? null"
    advances-state
    :header="t('vendite.ordini.emissione_titolo')"
    :confirm-label="t('vendite.ordini.emissione_conferma')"
    :loading="props.loading"
    @update:visible="(val) => emit('update:visible', val)"
    @confirm="(payload) => emit('confirm', payload)"
  >
    <template #riepilogo>
      <p>{{ t('vendite.ordini.emissione_messaggio') }}</p>

      <div
        v-if="ordine"
        style="margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.4rem;"
      >
        <div v-if="ordine.ragione_sociale_completa">
          <strong>{{ t('vendite.ordini.field_billing_account') }}:</strong>
          {{ ordine.ragione_sociale_completa }}
        </div>
        <div v-if="ordine.data">
          <strong>{{ t('vendite.ordini.field_data') }}:</strong>
          {{ displayDate(ordine.data) }}
        </div>
      </div>
    </template>
  </DocumentoEmissioneDialog>
</template>
