<script setup>
// Scopo: Dialog multi-modalita' per registrare l'esito di un'offerta.
//        Modalita' (state machine asimmetrica, piano BE+FE §C3):
//          - ACCETTATA  da EMESSA  (motivazione opzionale)
//          - RIFIUTATA  da EMESSA  (motivazione obbligatoria, "no del cliente")
//          - ANNULLATA  da BOZZA o da ACCETTATA (motivazione obbligatoria,
//                       "ritiro da noi"; da ACCETTATA solo senza documenti vivi
//                       a valle, lo dice il DB — dal 2026-10-21)
//
//        Il dialog non sceglie la modalita': la riceve via prop dal drawer
//        (che la passa in base al bottone cliccato). Single source of truth
//        della state machine = OffertaDrawer.drawerActions computed.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../../../core/components/AppDialog.vue'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useFotografiaDialog } from '../../../../core/composables/useFotografiaDialog'

const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  offerta: { type: Object, default: null },
  // 'ACCETTATA' | 'RIFIUTATA' | 'ANNULLATA'
  modalita: { type: String, default: 'ACCETTATA' },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const motivazione = ref('')

watch(() => props.visible, (val) => {
  if (val) motivazione.value = ''
})

const motivazioneObbligatoria = computed(
  () => props.modalita === 'RIFIUTATA' || props.modalita === 'ANNULLATA',
)

const titolo = computed(() => {
  switch (props.modalita) {
    case 'ACCETTATA': return t('vendite.offerte.esito_accettata_titolo')
    case 'RIFIUTATA': return t('vendite.offerte.esito_rifiutata_titolo')
    case 'ANNULLATA': return t('vendite.offerte.esito_annullata_titolo')
    default: return ''
  }
})

const messaggio = computed(() => {
  switch (props.modalita) {
    case 'ACCETTATA': return t('vendite.offerte.esito_accettata_messaggio')
    case 'RIFIUTATA': return t('vendite.offerte.esito_rifiutata_messaggio')
    case 'ANNULLATA': return t('vendite.offerte.esito_annullata_messaggio')
    default: return ''
  }
})

// Conferma: primary (verde) su ACCETTATA, danger (rosso) sulle vie negative
// (RIFIUTATA/ANNULLATA). L'icona resta il check standard (FormFooter); a
// distinguere l'azione bastano colore + label.
const saveSeverity = computed(
  () => props.modalita === 'ACCETTATA' ? null : 'danger',
)

const labelConferma = computed(() => {
  switch (props.modalita) {
    case 'ACCETTATA': return t('vendite.offerte.esito_accettata_conferma')
    case 'RIFIUTATA': return t('vendite.offerte.esito_rifiutata_conferma')
    case 'ANNULLATA': return t('vendite.offerte.esito_annullata_conferma')
    default: return ''
  }
})

const canConfirm = computed(() => {
  if (motivazioneObbligatoria.value && !motivazione.value.trim()) return false
  return true
})

function onConfirm() {
  emit('confirm', {
    esito: props.modalita,
    motivazione: motivazione.value.trim(),
  })
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ motivazione: motivazione.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="props.visible"
    :header="titolo"
    width="md"
    :loading="props.loading"
    :save-disabled="props.loading || !canConfirm"
    :save-label="labelConferma"
    :save-severity="saveSeverity"
    :readonly="false"
    @update:visible="(val) => emit('update:visible', val)"
    @save="onConfirm"
  >
    <p>{{ messaggio }}</p>

    <div v-if="offerta?.codice" style="margin: 0.5rem 0; color: var(--app-text-muted);">
      <strong>{{ offerta.codice }}</strong>
      <span v-if="offerta.billing_account_display"> · {{ offerta.billing_account_display }}</span>
    </div>

    <div class="form-field" style="margin-top: 1rem;">
      <label>
        {{ t('vendite.offerte.field_motivazione') }}
        <span v-if="motivazioneObbligatoria">*</span>
      </label>
      <Textarea
        v-model="motivazione"
        rows="4"
        autoResize
        :placeholder="motivazioneObbligatoria
          ? t('vendite.offerte.field_motivazione_required_placeholder')
          : t('vendite.offerte.field_motivazione_optional_placeholder')"
      />
    </div>

    <Message
      v-if="motivazioneObbligatoria"
      severity="warn"
      :closable="false"
      size="small"
    >
      {{ t('vendite.offerte.esito_warn_motivazione') }}
    </Message>
  </AppDialog>
</template>
