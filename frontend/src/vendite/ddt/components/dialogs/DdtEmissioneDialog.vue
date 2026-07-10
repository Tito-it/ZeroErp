<script setup>
// Scopo: Dialog di emissione DDT (DRAFT -> EMESSO). Alla conferma il DB assegna
//        il `numero` (trgfn_ddt_gen_numero_emesso) e scatta il guard
//        approvazione componenti BoM. A differenza di ordini/preventivi la
//        transizione NON genera documento/allegati (PDF fuori scope in questa
//        slice, D-3): dialog di sola CONFERMA con riepilogo, senza anteprima
//        PDF ne' upload. L'endpoint /emetti/ non accetta payload.
//
// Predisposizione PDF (D-3): quando la fase PDF sara' attiva questo dialog potra'
// evolvere verso il building block generico `DocumentoEmissioneDialog` (mirror
// OrdineEmissioneDialog) una volta registrato il context builder DDT_VENDITA.
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { displayDate } from '../../../../core/utils/date'

const props = defineProps({
  visible: { type: Boolean, default: false },
  ddt: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()

function onConfirm() {
  emit('confirm')
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="(v) => emit('update:visible', v)"
    modal
    :header="t('vendite.ddt.emissione_titolo')"
    :style="{ width: '30rem' }"
    :dismissable-mask="true"
  >
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
    </div>

    <Message severity="info" :closable="false" class="mt-1">
      {{ t('vendite.ddt.emissione_numero_hint') }}
    </Message>

    <template #footer>
      <Button
        :label="t('common.cancel')"
        severity="secondary"
        text
        :disabled="props.loading"
        @click="emit('update:visible', false)"
      />
      <Button
        :label="t('vendite.ddt.emissione_conferma')"
        icon="pi pi-check"
        :loading="props.loading"
        @click="onConfirm"
      />
    </template>
  </Dialog>
</template>
