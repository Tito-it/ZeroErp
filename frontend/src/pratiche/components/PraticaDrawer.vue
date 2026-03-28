<script setup>
// Scopo: Drawer dettaglio/creazione pratica con TabView (Dati, Flussi, Giornale).
// In edit: 3 tab + bottoni azioni stato nel tab Dati.
// In create: solo form creazione (no tab).
// Pattern: DrawerTitle + DrawerFooter + TabView + useApiHandler + useInjectReadonly.
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { lookupCodici } from '../../core/apiCore'
import { displayDate } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import { DRAWER_WIDTH, STATO_PRATICA } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import PraticaFlussiTab from './PraticaFlussiTab.vue'
import PraticaGiornaleTab from './PraticaGiornaleTab.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const store = usePraticheStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

// Lookup
const statiPratica = useLookup(() => lookupCodici('config.stati_pratiche'), { immediate: true })
const prioritaPratica = useLookup(() => lookupCodici('config.priorita_pratiche'), { immediate: true })
const tipiPrestazione = useLookup(() => lookupCodici('pratiche.tipi_prestazione'), { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  praticaId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
const tabViewKey = ref(0)

function defaultForm() {
  return {
    tipo_prestazione_id: null,
    priorita_id: null,
    descrizione: '',
    data_scadenza: null
  }
}

function resetForm() {
  detail.value = null
  form.value = defaultForm()
}

// Scopo: Popola form dai dati dettaglio (edit mode).
function populateFormFromDetail(d) {
  form.value = {
    tipo_prestazione_id: d.tipo_prestazione_id,
    priorita_id: d.priorita_id,
    descrizione: d.descrizione || '',
    data_scadenza: d.data_scadenza ? new Date(d.data_scadenza) : null
  }
}

// Scopo: Risolve un campo di un lookup ID dalla lista caricata.
function lookupField(items, id, field = 'descrizione') {
  if (id == null) return ''
  const item = items.find(i => i.id === id)
  return item?.[field] || ''
}

// Scopo: Codice interno stato pratica corrente (per condizioni azioni e severity).
const statoCorrente = computed(() =>
  lookupField(statiPratica.items.value, detail.value?.stato_id, 'codice_interno').trim()
)

// Carica dati quando il drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  nextTick(() => { tabViewKey.value++ })
  if (isEdit.value && props.praticaId) {
    const d = await store.fetchDetail(props.praticaId)
    detail.value = d
    populateFormFromDetail(d)
  } else {
    resetForm()
  }
})

// Scopo: Ricarica dettaglio (usato dopo azioni stato o refresh da tab flussi).
async function reloadDetail() {
  if (!props.praticaId) return
  const d = await store.fetchDetail(props.praticaId)
  detail.value = d
  populateFormFromDetail(d)
}

// --- Azioni stato pratica (FE-6) ---

async function onApriPratica() {
  const result = await execute(
    () => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.APERTA }),
    { successMessage: t('pratiche.stato_cambiato') }
  )
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

async function onSospendiPratica() {
  const result = await execute(
    () => store.sospendi(props.praticaId, { motivo: t('pratiche.sospensione_manuale') }),
    { successMessage: t('pratiche.stato_cambiato') }
  )
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

async function onRiattivaPratica() {
  const result = await execute(
    () => store.riattiva(props.praticaId),
    { successMessage: t('pratiche.stato_cambiato') }
  )
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

async function onChiudiPratica() {
  const result = await execute(
    () => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.CHIUSA }),
    { successMessage: t('pratiche.stato_cambiato') }
  )
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

async function onAnnullaPratica() {
  const result = await execute(
    () => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.ANNULLATA }),
    { successMessage: t('pratiche.stato_cambiato') }
  )
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

// --- Salvataggio (FE-4 create / FE-3 update) ---

async function onSave() {
  if (isEdit.value) {
    const payload = {
      descrizione: form.value.descrizione || null,
      data_scadenza: form.value.data_scadenza
        ? form.value.data_scadenza.toISOString().split('T')[0]
        : null
    }
    const result = await execute(
      () => store.update(props.praticaId, payload),
      { successMessage: t('pratiche.pratica_salvata') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const payload = {
      tipo_prestazione_id: form.value.tipo_prestazione_id,
      priorita_id: form.value.priorita_id,
      descrizione: form.value.descrizione || null,
      data_scadenza: form.value.data_scadenza
        ? form.value.data_scadenza.toISOString().split('T')[0]
        : null
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('pratiche.pratica_creata') }
    )
    if (result !== null) emit('saved', result)
  }
}

const canSave = computed(() => {
  if (isEdit.value) return true
  return !!form.value.tipo_prestazione_id && !!form.value.priorita_id
})

function onClose() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('pratiche.pratica')"
        icon="pi pi-folder"
      />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">

      <!-- === CREAZIONE: form semplice senza tab === -->
      <template v-if="!isEdit">
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('pratiche.col_tipo_prestazione') }} *</label>
            <Select
              v-model="form.tipo_prestazione_id"
              :options="tipiPrestazione.items.value"
              :loading="tipiPrestazione.loading.value"
              option-label="descrizione" option-value="id"
              class="w-full" :placeholder="t('pratiche.select_tipo_prestazione')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.col_priorita') }} *</label>
            <Select
              v-model="form.priorita_id"
              :options="prioritaPratica.items.value"
              :loading="prioritaPratica.loading.value"
              option-label="descrizione" option-value="id"
              class="w-full" :placeholder="t('pratiche.select_priorita')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.field_descrizione') }}</label>
            <Textarea v-model="form.descrizione" class="w-full" rows="3" auto-resize />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.col_data_scadenza') }}</label>
            <DatePicker v-model="form.data_scadenza" class="w-full" date-format="dd/mm/yy" show-icon />
          </div>
        </div>
        <div class="flex justify-end mt-4">
          <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
        </div>
      </template>

      <!-- === EDIT: TabView con Dati + Flussi + Giornale === -->
      <template v-if="isEdit && detail">
        <TabView :key="tabViewKey">

          <!-- Tab Dati -->
          <TabPanel :header="t('pratiche.tab_dati')">
            <!-- Intestazione: codice + stato + priorita' -->
            <div class="pratica-header-row">
              <div class="form-field" style="flex: 1;">
                <label>{{ t('pratiche.col_codice') }}</label>
                <InputText :model-value="detail.codice" disabled class="w-full" />
              </div>
              <div style="display: flex; gap: 0.5rem; align-self: flex-end;">
                <Tag
                  :value="lookupField(statiPratica.items.value, detail.stato_id)"
                  :severity="statoPraticaSeverity(statoCorrente)"
                />
                <Tag
                  v-if="detail.priorita_id"
                  :value="lookupField(prioritaPratica.items.value, detail.priorita_id)"
                  :severity="prioritaPraticaSeverity(lookupField(prioritaPratica.items.value, detail.priorita_id, 'codice_interno'))"
                />
              </div>
            </div>

            <!-- Azioni stato (FE-6) -->
            <div v-if="!isReadonly" class="pratica-actions">
              <Button
                v-if="statoCorrente === STATO_PRATICA.BOZZA"
                :label="t('pratiche.azione_apri')"
                icon="pi pi-lock-open" size="small"
                severity="info"
                @click="onApriPratica"
              />
              <Button
                v-if="statoCorrente === STATO_PRATICA.APERTA"
                :label="t('pratiche.azione_sospendi')"
                icon="pi pi-pause" size="small"
                severity="warn"
                @click="onSospendiPratica"
              />
              <Button
                v-if="statoCorrente === STATO_PRATICA.SOSPESA"
                :label="t('pratiche.azione_riattiva')"
                icon="pi pi-play" size="small"
                severity="success"
                @click="onRiattivaPratica"
              />
              <Button
                v-if="statoCorrente === STATO_PRATICA.APERTA || statoCorrente === STATO_PRATICA.SOSPESA"
                :label="t('pratiche.azione_chiudi')"
                icon="pi pi-check-circle" size="small"
                severity="success"
                @click="onChiudiPratica"
              />
              <Button
                v-if="statoCorrente !== STATO_PRATICA.CHIUSA && statoCorrente !== STATO_PRATICA.ANNULLATA"
                :label="t('pratiche.azione_annulla')"
                icon="pi pi-times-circle" size="small"
                severity="danger"
                @click="onAnnullaPratica"
              />
            </div>

            <!-- Form dati editabili -->
            <div class="form-grid">
              <div class="form-field">
                <label>{{ t('pratiche.col_tipo_prestazione') }}</label>
                <Select
                  v-model="form.tipo_prestazione_id"
                  :options="tipiPrestazione.items.value"
                  :loading="tipiPrestazione.loading.value"
                  option-label="descrizione" option-value="id"
                  class="w-full" disabled
                />
              </div>
              <div class="form-field">
                <label>{{ t('pratiche.col_priorita') }}</label>
                <Select
                  v-model="form.priorita_id"
                  :options="prioritaPratica.items.value"
                  :loading="prioritaPratica.loading.value"
                  option-label="descrizione" option-value="id"
                  class="w-full" :placeholder="t('pratiche.select_priorita')" show-clear
                />
              </div>
              <div class="form-field">
                <label>{{ t('pratiche.field_descrizione') }}</label>
                <Textarea v-model="form.descrizione" class="w-full" rows="3" auto-resize />
              </div>
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('pratiche.col_data_scadenza') }}</label>
                  <DatePicker v-model="form.data_scadenza" class="w-full" date-format="dd/mm/yy" show-icon />
                </div>
                <div class="form-field">
                  <label>{{ t('pratiche.col_data_apertura') }}</label>
                  <InputText :model-value="displayDate(detail.data_insert)" disabled class="w-full" />
                </div>
              </div>
            </div>

            <div class="flex justify-end mt-4">
              <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
            </div>
          </TabPanel>

          <!-- Tab Flussi (FE-5) -->
          <TabPanel :header="t('pratiche.tab_flussi')">
            <PraticaFlussiTab
              :pratica-id="props.praticaId"
              :stato-codice-pratica="statoCorrente"
              @refresh="reloadDetail"
            />
          </TabPanel>

          <!-- Tab Giornale (FE-7) -->
          <TabPanel :header="t('pratiche.tab_giornale')">
            <PraticaGiornaleTab :pratica-id="props.praticaId" />
          </TabPanel>

        </TabView>
      </template>

    </div>
  </Drawer>
</template>

<style scoped>
.pratica-header-row {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.pratica-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--app-toolbar-border);
}
</style>
