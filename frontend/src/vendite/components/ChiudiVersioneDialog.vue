<script setup>
// Scopo: Dialog per programmare la chiusura di una versione ATTIVA
//        impostando valido_al. Mostra warning sulle conseguenze.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { updateVersione } from '../api/listini'
import { displayDate, toDateString } from '../../core/utils/date'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()

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

watch(() => props.visible, (v) => {
  if (v && props.versione) {
    dataChiusura.value = props.versione.valido_al
      ? new Date(props.versione.valido_al)
      : null
  }
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
        ? t('listini.programma_chiusura_successo', { data: displayDate(dataChiusura.value) })
        : t('listini.programma_chiusura_rimossa')
    }
  )
  if (res) {
    emit('saved', { listinoId: props.listinoId })
    onHide()
  }
}

async function rimuoviChiusura() {
  if (loading.value) return
  const res = await execute(
    () => updateVersione(props.listinoId, props.versione.id, { valido_al: null }),
    { successMessage: t('listini.programma_chiusura_rimossa') }
  )
  if (res) {
    emit('saved', { listinoId: props.listinoId })
    onHide()
  }
}
</script>

<template>
  <Dialog :visible="visible" @update:visible="onHide" modal
    :header="t('listini.programma_chiusura_titolo')" :style="{ width: '480px' }">

    <Message v-if="dataChiusura" severity="warn" :closable="false" class="mb-1">
      {{ t('listini.programma_chiusura_warning', { data_dopo: dataDopoLabel }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('listini.programma_chiusura_data') }}</label>
        <DatePicker v-model="dataChiusura" date-format="dd/mm/yy"
          show-icon show-button-bar :min-date="new Date()" />
      </div>
    </div>

    <div class="flex justify-end gap-2 mt-1">
      <Button v-if="haGiaChiusura" :label="t('common.delete')"
        text severity="danger" :loading="loading" @click="rimuoviChiusura" />
      <Button :label="t('common.cancel')" text @click="onHide" />
      <Button :label="t('listini.programma_chiusura_conferma')"
        icon="pi pi-calendar" severity="warn"
        :disabled="!dataChiusura" :loading="loading" @click="conferma" />
    </div>
  </Dialog>
</template>
