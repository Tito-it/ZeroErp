<script setup>
// Scopo: Dialog di successione contratti — si apre quando il push offerta a
//        contratto fallisce con E_CONTRATTO_OVERLAP_ESISTENTE (esiste gia' un
//        contratto attivo sovrapposto per cliente/utility/periodo).
//        Mostra il contratto in conflitto e chiede conferma esplicita per
//        chiuderlo (valido_al = nuova decorrenza - 1 giorno) e generare il
//        nuovo. Su conferma il drawer ri-chiama il push con
//        chiudi_esistente=true (brief successione 2026-05-31).
//
//        La successione e' SEMPRE esplicita: nessun contratto preesistente
//        viene chiuso senza questa conferma.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../../../core/components/AppDialog.vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { displayDate, parseIsoDate, toDateString } from '../../../../core/utils/date'
import { MANAGE_ICONS } from '../../../../core/constants'

const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  // Contratto in conflitto: { id, numero, valido_dal, valido_al }.
  contratto: { type: Object, default: null },
  // Data di decorrenza del nuovo contratto (= offerta.validita_dal, ISO).
  nuovaValiditaDal: { type: String, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm', 'ispeziona-contratto'])

// Data di chiusura del contratto esistente = decorrenza nuovo - 1 giorno
// (mirror della logica DB fn_chiudi_contratto_per_successione). Mostrata
// all'operatore per rendere esplicito l'effetto della successione.
const dataChiusura = computed(() => {
  const d = parseIsoDate(props.nuovaValiditaDal)
  if (!d) return null
  d.setDate(d.getDate() - 1)
  return toDateString(d)
})

function onConfirm() {
  emit('confirm')
}

// Apre il contratto in conflitto in sola lettura per ispezione (righe incluse).
// Il parent chiude questo dialog, mostra il ContrattoDrawer read-only e lo
// ri-apre alla chiusura: l'operatore rivede e poi conferma/annulla.
function onIspezionaContratto() {
  if (props.contratto?.id) {
    emit('ispeziona-contratto', { contrattoId: props.contratto.id })
  }
}
</script>

<template>
  <AppDialog
    :visible="props.visible"
    :header="t('vendite.offerte.successione_titolo')"
    width="md"
    :loading="props.loading"
    :save-disabled="props.loading || !props.contratto"
    :save-label="t('common.confirm')"
    :readonly="false"
    @update:visible="(val) => emit('update:visible', val)"
    @save="onConfirm"
  >
    <Message severity="warn" :closable="false" size="small">
      {{ t('vendite.offerte.successione_messaggio') }}
    </Message>

    <div v-if="props.contratto" class="app-preview-box">
      <div>
        <strong>{{ t('vendite.offerte.successione_contratto_label') }}:</strong>
        {{ props.contratto.numero }}
        <Button
          :label="t('vendite.offerte.successione_apri_contratto')"
          :icon="MANAGE_ICONS.INSPECT"
          text
          size="small"
          @click="onIspezionaContratto"
        />
      </div>
      <div class="app-text-muted">
        {{ t('vendite.offerte.successione_validita_attuale') }}:
        {{ displayDate(props.contratto.valido_dal) }} —
        {{ props.contratto.valido_al ? displayDate(props.contratto.valido_al) : t('vendite.offerte.successione_senza_fine') }}
      </div>
    </div>

    <p v-if="dataChiusura">
      {{ t('vendite.offerte.successione_effetto', { data: displayDate(dataChiusura) }) }}
    </p>
  </AppDialog>
</template>
