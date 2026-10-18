<script setup>
// Scopo: Dialog di emissione DDT (DRAFT -> EMESSO). Wrapper sottile sul
//        building block generico `DocumentoEmissioneDialog` (modalita'
//        advances-state): mostra l'anteprima del documento accompagnatorio che
//        verra' generato + consente di allegare file; alla Conferma il parent
//        chiama l'endpoint /emetti/ multipart (emissione + genera documento +
//        allegati, atomico lato BE — ApiDdtEmetti). Alla transizione il DB
//        assegna il `numero` (trgfn_ddt_gen_numero_emesso) e scatta il gate
//        approvazione componenti BoM. Mirror di OrdineEmissioneDialog.
import { useI18n } from 'vue-i18n'
import DocumentoEmissioneDialog from '../../../../documenti/components/DocumentoEmissioneDialog.vue'
import { SORGENTE_CODES } from '../../../../documenti/constants'
import { displayDate } from '../../../../core/utils/date'
import Message from 'primevue/message'

const props = defineProps({
  visible: Boolean,
  ddt: { type: Object, default: null },
  loading: Boolean,
  // True quando manca l'indirizzo obbligatorio (CON): avviso nel riepilogo +
  // Conferma DISABILITATA (l'emissione genera la stampa: senza indirizzo il
  // PDF sarebbe scorretto). Il guard DB (E_INDIRIZZO_DOC_OBBLIGATORIO) resta
  // la fonte di verita' server-side.
  indirizzoMancante: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()
</script>

<template>
  <DocumentoEmissioneDialog
    :visible="props.visible"
    :sorgente-code="SORGENTE_CODES.DDT_VENDITA"
    :sorgente-id="props.ddt?.id ?? null"
    advances-state
    :header="t('vendite.ddt.emissione_titolo')"
    :confirm-label="t('vendite.ddt.emissione_conferma')"
    :loading="props.loading"
    :confirm-disabled="props.indirizzoMancante"
    @update:visible="(val) => emit('update:visible', val)"
    @confirm="(payload) => emit('confirm', payload)"
  >
    <template #riepilogo>
      <Message v-if="props.indirizzoMancante" severity="warn" :closable="false">
        {{ t('vendite.indirizzi.mancante_obbligatorio') }}
      </Message>
      <p>{{ t('vendite.ddt.emissione_messaggio') }}</p>

      <div
        v-if="ddt"
        style="margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.4rem;"
      >
        <div v-if="ddt.destinatario_denominazione">
          <strong>{{ t('vendite.ddt.field_destinatario') }}:</strong>
          {{ ddt.destinatario_denominazione }}
        </div>
        <div v-if="ddt.data">
          <strong>{{ t('vendite.ddt.field_data') }}:</strong>
          {{ displayDate(ddt.data) }}
        </div>
        <div>{{ t('vendite.ddt.emissione_numero_hint') }}</div>
      </div>
    </template>
  </DocumentoEmissioneDialog>
</template>
