<script setup>
// Scopo: Dialog per chiudere una versione ATTIVA impostando valido_al
//        (oggi = chiusura immediata, data futura = chiusura programmata).
//        Il cambio di stato a CHIUSA e' sincronizzato dal DB (trigger/job)
//        quando valido_al scende sotto la data corrente. Mostra warning
//        sulle conseguenze della chiusura.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { updateVersione } from '../api/listini'
import { getVersioneCloseDefaults } from '../api/formDefaults'
import { displayDate, toDateString, addDaysToToday } from '../../core/utils/date'
import AppDialog from '../../core/components/AppDialog.vue'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import FormFooter from '../../core/components/FormFooter.vue'
import Message from 'primevue/message'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  versione: { type: Object, default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const dataChiusura = ref(null)

const haGiaChiusura = computed(() => props.versione?.valido_al != null)

const dataDopoLabel = computed(() => {
  if (!dataChiusura.value) return '?'
  const d = new Date(dataChiusura.value)
  d.setDate(d.getDate() + 1)
  return displayDate(d)
})

// Defaults BE (Fase 2.B5c): default_valido_al risolto dal service
// (existing valido_al se programmata, altrimenti oggi+lead_gg). Single
// source of truth: niente piu' lettura parameter cablata nel componente.
async function loadDefaults() {
  if (!props.listinoId || !props.versione?.id) return
  const res = await execute(
    () => getVersioneCloseDefaults(props.listinoId, props.versione.id),
    { silent: true },
  )
  if (res === null) {
    // Fallback resiliente: se il BE fallisce, parti da oggi.
    dataChiusura.value = props.versione?.valido_al
      ? new Date(props.versione.valido_al + 'T00:00:00')
      : addDaysToToday(0)
    return
  }
  dataChiusura.value = res.default_valido_al
    ? new Date(res.default_valido_al + 'T00:00:00')
    : addDaysToToday(0)
}

watch(() => props.visible, async (v) => {
  if (!v || !props.versione) return
  await loadDefaults()
})

function onHide() {
  emit('update:visible', false)
}

async function conferma() {
  if (loading.value) return
  const valido_al = dataChiusura.value ? toDateString(dataChiusura.value) : null
  const res = await execute(
    () => updateVersione(props.listinoId, props.versione.id, { valido_al }),
    { successMessage: valido_al
        ? t('vendite.listini.chiudi_versione_successo', { data: displayDate(dataChiusura.value) })
        : t('vendite.listini.chiudi_versione_rimossa')
    }
  )
  // Memoria feedback_drawer_result_check: useApiHandler.execute ritorna
  // null SOLO su errore. Risultato falsy legit (es. {} vuoto) deve passare.
  if (res !== null) {
    emit('saved', { listinoId: props.listinoId })
    onHide()
  }
}

async function rimuoviChiusura() {
  if (loading.value) return
  const res = await execute(
    () => updateVersione(props.listinoId, props.versione.id, { valido_al: null }),
    { successMessage: t('vendite.listini.chiudi_versione_rimossa') }
  )
  if (res !== null) {
    emit('saved', { listinoId: props.listinoId })
    onHide()
  }
}
</script>

<template>
  <AppDialog :visible="visible" @update:visible="onHide"
    :header="t('vendite.listini.chiudi_versione_titolo')" width="sm">

    <Message v-if="dataChiusura" severity="warn" :closable="false" class="mb-1">
      {{ t('vendite.listini.chiudi_versione_warning', { data_dopo: dataDopoLabel }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('vendite.listini.chiudi_versione_data') }}</label>
        <DatePicker v-model="dataChiusura" date-format="dd/mm/yy"
          show-icon show-button-bar :min-date="new Date()" />
      </div>
    </div>

    <!-- Footer custom: oltre ad Annulla/Conferma standard c'e' il bottone
         distruttivo "Rimuovi chiusura" (terzo pulsante extra-pattern). -->
    <template #footer>
      <Button
        v-if="haGiaChiusura"
        :label="t('common.delete')"
        text
        severity="danger"
        :loading="loading"
        @click="rimuoviChiusura"
      />
      <FormFooter
        :save-label="t('vendite.listini.chiudi_versione_conferma')"
        save-severity="warn"
        :loading="loading"
        :disabled="!dataChiusura"
        @cancel="onHide"
        @save="conferma"
      />
    </template>
  </AppDialog>
</template>
