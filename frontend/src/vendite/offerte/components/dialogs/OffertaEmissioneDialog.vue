<script setup>
// Scopo: Dialog di conferma emissione offerta (BOZZA -> EMESSA).
//        Mostra riepilogo listino+versione+validita+eccezioni count.
//        Il trigger DB enforce: listino_versione_id NOT NULL + versione
//        ATTIVA al momento dell'emissione. Avviso parlante se manca.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FormFooter from '../../../../core/components/FormFooter.vue'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'

import { displayDate } from '../../../../core/utils/date'

const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  offerta: { type: Object, default: null },
  loading: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])

const versioneListinoMancante = computed(
  () => !props.offerta?.listino_versione_id,
)
const eccezioniCount = computed(
  () => props.offerta?.eccezioni?.length || 0,
)
</script>

<template>
  <Dialog
    :visible="props.visible"
    modal
    :header="t('vendite.offerte.emissione_titolo')"
    :style="{ width: '480px' }"
    @update:visible="(val) => emit('update:visible', val)"
  >
    <p>{{ t('vendite.offerte.emissione_messaggio') }}</p>

    <div v-if="offerta" style="margin: 1rem 0; display: flex; flex-direction: column; gap: 0.4rem;">
      <div>
        <strong>{{ t('vendite.offerte.field_listino') }}:</strong>
        {{ offerta.listino_codice || '—' }}
        <span v-if="offerta.listino_versione_codice" class="text-color-secondary">
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

    <Message
      v-if="versioneListinoMancante"
      severity="warn"
      :closable="false"
      size="small"
    >
      {{ t('vendite.offerte.emissione_warn_versione_mancante') }}
    </Message>
    <Message
      v-else
      severity="info"
      :closable="false"
      size="small"
    >
      {{ t('vendite.offerte.emissione_info') }}
    </Message>

    <template #footer>
      <FormFooter
        :save-label="t('vendite.offerte.emissione_conferma')"
        :loading="props.loading"
        :disabled="props.loading"
        @cancel="emit('update:visible', false)"
        @save="emit('confirm')"
      />
    </template>
  </Dialog>
</template>
