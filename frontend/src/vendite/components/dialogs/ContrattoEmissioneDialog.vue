<script setup>
// Scopo: Dialog di attivazione contratto (DRAFT -> ATTIVO). Wrapper sottile
//        sul building block generico `DocumentoEmissioneDialog` (modalita'
//        advances-state): mostra l'anteprima del documento che verra'
//        generato + consente di allegare file; alla Conferma il parent
//        chiama l'endpoint emetti multipart (cambia stato + genera +
//        allegati, atomico). Mirror di Offerta/Preventivo EmissioneDialog.
import { useI18n } from 'vue-i18n'
import DocumentoEmissioneDialog from '../../../documenti/components/DocumentoEmissioneDialog.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { displayDate } from '../../../core/utils/date'

const props = defineProps({
  visible: Boolean,
  contratto: { type: Object, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()
</script>

<template>
  <DocumentoEmissioneDialog
    :visible="props.visible"
    :sorgente-code="SORGENTE_CODES.CONTRATTO"
    :sorgente-id="props.contratto?.id ?? null"
    advances-state
    :header="t('vendite.contratti.emissione_titolo')"
    :confirm-label="t('vendite.contratti.emissione_conferma')"
    :loading="props.loading"
    @update:visible="(val) => emit('update:visible', val)"
    @confirm="(payload) => emit('confirm', payload)"
  >
    <template #riepilogo>
      <p>{{ t('vendite.contratti.emissione_messaggio') }}</p>

      <div v-if="contratto" style="margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.4rem;">
        <div v-if="contratto.billing_account_codice || contratto.billing_account_ragione_sociale">
          <strong>{{ t('vendite.contratti.col_ba') }}:</strong>
          {{ contratto.billing_account_ragione_sociale || contratto.billing_account_codice }}
          <span
            v-if="contratto.billing_account_codice && contratto.billing_account_ragione_sociale"
            class="app-text-muted"
          >
            · {{ contratto.billing_account_codice }}
          </span>
        </div>
        <div>
          <strong>{{ t('vendite.contratti.col_valido_dal') }}:</strong>
          {{ displayDate(contratto.valido_dal) }}
          <span v-if="contratto.valido_al">
            → {{ displayDate(contratto.valido_al) }}
          </span>
        </div>
      </div>
    </template>
  </DocumentoEmissioneDialog>
</template>
