<script setup>
// Scopo: Dialog di conferma push offerta -> contratto DRAFT.
//        Pattern idempotenza Pattern A: una seconda push fallisce con
//        `E_OFFERTA_CONTRATTO_GIA_GENERATO`. Il piano FE-5 prevede di
//        intercettare quell'errore con un dialog parlante che linki al
//        contratto esistente; oggi pero' il dettaglio offerta non
//        espone `contratto_id` collegato — quel link sara' aggiunto
//        quando il BE estendera' get_offerta() (Step futuro post-v1).
//
//        Pratica opzionale: l'operatore puo' collegare il contratto
//        generato a una pratica esistente (es. asse OFFERTA_QUADRO).
//        In v1 niente lookup pratiche FE: solo input opzionale, lasciato
//        a future estensioni.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../../../core/components/AppDialog.vue'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'

const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  offerta: { type: Object, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const praticaId = ref(null)

watch(() => props.visible, (val) => {
  if (val) praticaId.value = null
})

function onConfirm() {
  emit('confirm', {
    praticaId: praticaId.value || null,
  })
}
</script>

<template>
  <AppDialog
    :visible="props.visible"
    :header="t('vendite.offerte.push_titolo')"
    width="md"
    :loading="props.loading"
    :save-disabled="props.loading"
    :save-label="t('common.confirm')"
    :readonly="false"
    @update:visible="(val) => emit('update:visible', val)"
    @save="onConfirm"
  >
    <p>{{ t('vendite.offerte.push_messaggio') }}</p>

    <div v-if="offerta?.codice" style="margin: 0.5rem 0; color: var(--app-text-muted);">
      <strong>{{ offerta.codice }}</strong>
      <span v-if="offerta.billing_account_display"> · {{ offerta.billing_account_display }}</span>
    </div>

    <Message severity="info" :closable="false" size="small">
      {{ t('vendite.offerte.push_info') }}
    </Message>

    <div class="form-field" style="margin-top: 1rem;">
      <label>{{ t('vendite.offerte.push_pratica_opzionale') }}</label>
      <InputNumber
        v-model="praticaId"
        :placeholder="t('vendite.offerte.push_pratica_placeholder')"
        :min="1"
        show-buttons
      />
      <small class="text-color-secondary">
        {{ t('vendite.offerte.push_pratica_hint') }}
      </small>
    </div>
  </AppDialog>
</template>
