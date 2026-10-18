<script setup>
// Scopo: Dialog di emissione offerta (BOZZA -> EMESSA). Wrapper sottile sul
//        building block generico `DocumentoEmissioneDialog` (modalita'
//        advances-state): mostra l'anteprima del documento che verra'
//        generato + consente di allegare file; alla Conferma il parent
//        chiama l'endpoint emetti multipart (emetti + genera + allegati,
//        atomico). Il riepilogo specifico offerta (listino/versione/
//        eccezioni) vive nello slot `#riepilogo`.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import DocumentoEmissioneDialog from '../../../../documenti/components/DocumentoEmissioneDialog.vue'
import { SORGENTE_CODES } from '../../../../documenti/constants'
import { displayDate } from '../../../../core/utils/date'

const props = defineProps({
  visible: Boolean,
  offerta: { type: Object, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()

// Nota: NON controlliamo qui se `listino_versione_id` e' valorizzato.
// In BOZZA e' legittimamente NULL: il trigger DB lo fissa al momento
// dell'emissione (versione ATTIVA del listino). Se manca la versione
// attiva, il trigger rifiuta con errore parlante propagato dal BE.
const eccezioniCount = computed(
  () => props.offerta?.eccezioni?.length || 0,
)
</script>

<template>
  <DocumentoEmissioneDialog
    :visible="props.visible"
    :sorgente-code="SORGENTE_CODES.OFFERTA_COMMERCIALE"
    :sorgente-id="props.offerta?.id ?? null"
    advances-state
    :header="t('vendite.offerte.emissione_titolo')"
    :confirm-label="t('vendite.offerte.emissione_conferma')"
    :loading="props.loading"
    @update:visible="(val) => emit('update:visible', val)"
    @confirm="(payload) => emit('confirm', payload)"
  >
    <template #riepilogo>
      <p>{{ t('vendite.offerte.emissione_messaggio') }}</p>

      <div v-if="offerta" style="margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.4rem;">
        <div>
          <strong>{{ t('vendite.offerte.field_listino') }}:</strong>
          {{ offerta.listino_codice || '—' }}
          <span v-if="offerta.listino_versione_codice" class="app-text-muted">
            · v{{ offerta.listino_versione_codice }}
          </span>
        </div>
        <div>
          <strong>{{ t('vendite.offerte.field_validita_dal') }}:</strong>
          {{ displayDate(offerta.validita_dal) }}
          <span v-if="offerta.validita_al">
            → {{ displayDate(offerta.validita_al) }}
          </span>
        </div>
        <div>
          <strong>{{ t('vendite.offerte.col_eccezioni') }}:</strong>
          {{ eccezioniCount }}
        </div>
      </div>

      <!-- Info sempre visibile: la versione del listino viene fissata in
           automatico al momento dell'emissione (la BOZZA non la ha). -->
      <Message
        severity="info"
        :closable="false"
        size="small"
      >
        {{ t('vendite.offerte.emissione_info') }}
      </Message>
    </template>
  </DocumentoEmissioneDialog>
</template>
