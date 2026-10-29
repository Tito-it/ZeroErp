<script setup>
// Scopo: Dialog per chiudere una versione ATTIVA impostando valido_al
//        (oggi = chiusura immediata, data futura = chiusura programmata).
//        Il cambio di stato a CHIUSA e' sincronizzato dal DB (trigger/job)
//        quando valido_al scende sotto la data corrente. Mostra warning
//        sulle conseguenze della chiusura.
// Note: ⭐ Il verbo «Chiudi» del DB (`fn_programma_chiusura_versione_listino`,
//        brief-modello-documento-vendita §16.16, FE-C1): la fine nel passato la
//        rifiuta il DB sul campo `valido_al`. ⛔ Ritirato il `:min-date` del
//        DatePicker: era la sola sede della regola, ora copia di quella del DB.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { programmaChiusuraVersione } from '../api/listini'
import { getVersioneCloseDefaults } from '../api/formDefaults'
import { displayDate, toDateString, giornoDi, parseIsoDate, oggiAziendale } from '../../core/utils/date'
import AppDialog from '../../core/components/AppDialog.vue'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import FormFooter from '../../core/components/FormFooter.vue'
import Message from 'primevue/message'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'
import { DATE_FORMAT } from '../../core/constants'

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

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
  const d = giornoDi(dataChiusura.value)
  if (!d) return '?'
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
    // Fallback resiliente: se il BE fallisce, la fine attuale se non e' gia'
    // passata (come il service dei defaults: il verbo la rifiuterebbe),
    // altrimenti oggi.
    const attuale = parseIsoDate(props.versione?.valido_al)
    const oggi = oggiAziendale()
    dataChiusura.value = attuale && attuale >= oggi ? attuale : oggi
    return
  }
  dataChiusura.value = parseIsoDate(res.default_valido_al) ?? oggiAziendale()
}

watch(() => props.visible, async (v) => {
  if (!v || !props.versione) return
  await loadDefaults()
  fotografia.fissa()
})

function onHide() {
  emit('update:visible', false)
}

async function conferma() {
  if (loading.value) return
  const valido_al = dataChiusura.value ? toDateString(dataChiusura.value) : null
  const res = await execute(
    () => programmaChiusuraVersione(props.listinoId, props.versione.id, valido_al),
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
    () => programmaChiusuraVersione(props.listinoId, props.versione.id, null),
    { successMessage: t('vendite.listini.chiudi_versione_rimossa') }
  )
  if (res !== null) {
    emit('saved', { listinoId: props.listinoId })
    onHide()
  }
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ dataChiusura: dataChiusura.value }), { visibile: () => props.visible, fissaAllApertura: false })
</script>

<template>
  <AppDialog
    :visible="visible"
    :conferma-uscita="fotografia.chiudiConConferma"
    @update:visible="onHide"
    :header="t('vendite.listini.chiudi_versione_titolo')" width="sm">

    <Message v-if="dataChiusura" severity="warn" :closable="false">
      {{ t('vendite.listini.chiudi_versione_warning', { data_dopo: dataDopoLabel }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('vendite.listini.chiudi_versione_data') }}</label>
        <DatePicker v-model="dataChiusura" :date-format="DATE_FORMAT"
          show-icon show-button-bar
          :invalid="campiErrati.includes('valido_al')" />
      </div>
    </div>

    <!-- Footer custom: oltre ad Annulla/Conferma standard c'e' il bottone
         distruttivo "Rimuovi chiusura" (terzo pulsante extra-pattern). -->
    <template #footer="{ chiudi }">
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
        @cancel="chiudi"
        @save="conferma"
      />
    </template>
  </AppDialog>
</template>
