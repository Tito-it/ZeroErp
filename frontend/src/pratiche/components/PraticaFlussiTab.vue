<script setup>
// Scopo: Tab flussi dentro il drawer pratica.
// Lista compatta flussi con stato, sequenza, esito.
// Bottone "Nuovo flusso" se pratica in stato che lo consente.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listFlussi, createFlusso, cambiaStatoFlusso } from '../api/pratiche-api'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { displayDate } from '../../core/utils/date'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { STATO_PRATICA, STATO_FLUSSO, MANAGE_ICONS } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Button from 'primevue/button'

const { t } = useI18n()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  praticaId: { type: Number, required: true },
  statoCodicePratica: { type: String, default: '' }
})

const emit = defineEmits(['refresh'])

const flussi = ref([])
const loading = ref(false)

// Dialog esito inline per completamento flusso
const completandoFlussoId = ref(null)
const esitoSelezionato = ref(null)
const esitiOptions = computed(() => [
  { value: 'POSITIVO', label: t('pratiche.esito_positivo') },
  { value: 'NEGATIVO', label: t('pratiche.esito_negativo') },
  { value: 'PARZIALE', label: t('pratiche.esito_parziale') },
  { value: 'NON_APPLICABILE', label: t('pratiche.esito_non_applicabile') },
])

async function loadFlussi() {
  loading.value = true
  try {
    const res = await listFlussi(props.praticaId)
    flussi.value = res.data.data.results || []
  } finally {
    loading.value = false
  }
}

// Scopo: Crea un nuovo flusso per la pratica.
async function onNuovoFlusso() {
  const nextSeq = flussi.value.length > 0
    ? Math.max(...flussi.value.map(f => f.sequenza || 0)) + 1
    : 1
  const result = await execute(
    () => createFlusso(props.praticaId, { sequenza: nextSeq }),
    { successMessage: t('pratiche.flusso_creato') }
  )
  if (result !== null) {
    await loadFlussi()
    emit('refresh')
  }
}

// Scopo: Avvia flusso (DA_ESEGUIRE → IN_CORSO).
async function onAvviaFlusso(flusso) {
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, flusso.id, { nuovo_stato: STATO_FLUSSO.IN_CORSO }),
    { successMessage: t('pratiche.flusso_avviato') }
  )
  if (result !== null) {
    await loadFlussi()
    emit('refresh')
  }
}

// Scopo: Apre il mini-form inline per scegliere l'esito prima di completare.
function onChiediEsito(flusso) {
  completandoFlussoId.value = flusso.id
  esitoSelezionato.value = null
}

function onAnnullaEsito() {
  completandoFlussoId.value = null
  esitoSelezionato.value = null
}

// Scopo: Completa flusso (IN_CORSO → COMPLETATO) con esito scelto dall'utente.
async function onConfermaCompletamento() {
  if (!esitoSelezionato.value || !completandoFlussoId.value) return
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, completandoFlussoId.value, {
      nuovo_stato: STATO_FLUSSO.COMPLETATO,
      esito: esitoSelezionato.value
    }),
    { successMessage: t('pratiche.flusso_completato') }
  )
  if (result !== null) {
    completandoFlussoId.value = null
    esitoSelezionato.value = null
    await loadFlussi()
    emit('refresh')
  }
}

const canCreateFlusso = () => props.statoCodicePratica === STATO_PRATICA.APERTA

watch(() => props.praticaId, (id) => {
  if (id) loadFlussi()
}, { immediate: true })
</script>

<template>
  <div class="pratica-flussi-tab">
    <!-- Toolbar -->
    <div v-if="!isReadonly && canCreateFlusso()" class="pratica-flussi-toolbar">
      <Button
        :label="t('pratiche.nuovo_flusso')"
        :icon="MANAGE_ICONS.ADD"
        size="small"
        class="app-action-btn"
        @click="onNuovoFlusso"
      />
    </div>

    <!-- Lista flussi -->
    <DataTable
      :value="flussi"
      :loading="loading"
      striped-rows
      class="app-datatable"
      data-key="id"
    >
      <Column field="sequenza" :header="t('pratiche.flusso_col_seq')" style="width: 60px;" />
      <Column field="template_flusso_descrizione" :header="t('pratiche.flusso_col_template')" style="width: 180px;">
        <template #body="{ data }">
          {{ data.template_flusso_descrizione || t('pratiche.flusso_generico') }}
        </template>
      </Column>
      <Column field="stato_codice_interno" :header="t('pratiche.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione || data.stato_codice_interno" :severity="statoFlussoSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="esito" :header="t('pratiche.flusso_col_esito')" style="width: 100px;">
        <template #body="{ data }">
          <span v-if="data.esito" class="text-color-secondary">{{ data.esito }}</span>
        </template>
      </Column>
      <Column field="data_scadenza" :header="t('pratiche.col_data_scadenza')" style="width: 100px;">
        <template #body="{ data }">{{ displayDate(data.data_scadenza) }}</template>
      </Column>
      <Column :header="t('pratiche.flusso_col_azioni')" style="width: 260px;" :exportable="false">
        <template #body="{ data }">
          <div v-if="!isReadonly" style="display: flex; gap: 0.25rem; align-items: center;">
            <Button
              v-if="(data.stato_codice_interno || '') === STATO_FLUSSO.DA_ESEGUIRE"
              :icon="MANAGE_ICONS.PLAY"
              text rounded size="small"
              class="app-action-btn"
              v-tooltip.top="t('pratiche.flusso_avvia')"
              @click.stop="onAvviaFlusso(data)"
            />
            <!-- IN_CORSO: se non sto completando questo flusso, mostro il bottone -->
            <Button
              v-if="(data.stato_codice_interno || '') === STATO_FLUSSO.IN_CORSO && completandoFlussoId !== data.id"
              :icon="MANAGE_ICONS.CONFIRM"
              text rounded size="small"
              class="app-action-btn"
              v-tooltip.top="t('pratiche.flusso_completa')"
              @click.stop="onChiediEsito(data)"
            />
            <!-- IN_CORSO + completando: mini-form esito inline -->
            <div v-if="completandoFlussoId === data.id" style="display: flex; gap: 0.25rem; align-items: center;">
              <Select
                v-model="esitoSelezionato"
                :options="esitiOptions"
                option-label="label" option-value="value"
                :placeholder="t('pratiche.flusso_esito')"
                style="width: 150px;"
              />
              <Button :icon="MANAGE_ICONS.CONFIRM" text rounded size="small" severity="success"
                :disabled="!esitoSelezionato"
                @click.stop="onConfermaCompletamento" />
              <Button :icon="MANAGE_ICONS.CANCEL" text rounded size="small" severity="secondary"
                @click.stop="onAnnullaEsito" />
            </div>
          </div>
        </template>
      </Column>
      <template #empty>
        <div class="text-center text-color-secondary p-3">{{ t('pratiche.flussi_vuoti') }}</div>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.pratica-flussi-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.5rem;
}
</style>
