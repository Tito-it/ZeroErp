<script setup>
// Scopo: Drawer dettaglio/creazione pratica con TabView (Dati, Flussi, Giornale).
// In edit: 3 tab + bottoni azioni stato nel tab Dati.
//          I campi display (stato_descrizione, soggetto_display, ecc.) arrivano dal backend.
// In create: solo form creazione (no tab).
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { displayDate, toDateString } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import { DRAWER_WIDTH, STATO_PRATICA, MANAGE_ICONS } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import PraticaFlussiTab from './PraticaFlussiTab.vue'
import PraticaNoteTab from './PraticaNoteTab.vue'
import PraticaAllegatiTab from './PraticaAllegatiTab.vue'
import PraticaGiornaleTab from './PraticaGiornaleTab.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
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
const { confirmAction } = useConfirmAction()

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

// Selezione soggetto e ruolo (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)
const ruoloSelezionato = ref(null)

// Ruoli disponibili dal soggetto selezionato
const ruoliDisponibili = computed(() => {
  if (!soggettoSelezionato.value?.ruoli) return []
  return soggettoSelezionato.value.ruoli.map(r => ({
    value: r.soggetto_ruolo_id,
    label: r.descrizione || r.codice
  }))
})

function onSoggettoRicevuto(data) {
  soggettoSelezionato.value = data
  ruoloSelezionato.value = null
}

function clearSoggetto() {
  soggettoSelezionato.value = null
  ruoloSelezionato.value = null
}

function resetForm() {
  detail.value = null
  form.value = defaultForm()
  soggettoSelezionato.value = null
  ruoloSelezionato.value = null
}

function populateFormFromDetail(d) {
  form.value = {
    tipo_prestazione_id: d.tipo_prestazione_id,
    priorita_id: d.priorita_id,
    descrizione: d.descrizione || '',
    data_scadenza: d.data_scadenza ? new Date(d.data_scadenza) : null
  }
}

// Stato corrente dalla risposta backend (campo display, no lookup)
const statoCorrente = computed(() => detail.value?.stato_codice_interno || '')

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

async function reloadDetail() {
  if (!props.praticaId) return
  const d = await store.fetchDetail(props.praticaId)
  detail.value = d
  populateFormFromDetail(d)
}

// --- Azioni stato pratica ---

// Scopo: esegue un'azione sullo store e ricarica il dettaglio se OK.
async function executeAction(fn) {
  const result = await execute(fn, { successMessage: t('pratiche.stato_cambiato') })
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

function onApriPratica() {
  executeAction(() => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.APERTA }))
}
function onSospendiPratica() {
  executeAction(() => store.sospendi(props.praticaId, { motivo: t('pratiche.sospensione_manuale') }))
}
function onRiattivaPratica() {
  executeAction(() => store.riattiva(props.praticaId))
}
function onChiudiPratica() {
  executeAction(() => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.CHIUSA }))
}
function onAnnullaPratica() {
  confirmAction({
    title: t('pratiche.azione_annulla'),
    message: t('pratiche.conferma_annulla'),
    danger: true,
    onAccept: () => executeAction(() => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.ANNULLATA }))
  })
}

// --- Salvataggio ---

async function onSave() {
  if (isEdit.value) {
    const payload = {
      descrizione: form.value.descrizione || null,
      data_scadenza: form.value.data_scadenza
        ? toDateString(form.value.data_scadenza)
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
        ? toDateString(form.value.data_scadenza)
        : null,
      soggetto_id: soggettoSelezionato.value?.id || null,
      soggetto_ruolo_id: ruoloSelezionato.value || null,
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

      <!-- === CREAZIONE: form con soggetto/ruolo opzionali === -->
      <template v-if="!isEdit">
        <div class="form-grid">

          <!-- Soggetto (opzionale — pratica interna se non selezionato) -->
          <h4>{{ t('pratiche.section_soggetto') }}</h4>
          <div v-if="soggettoSelezionato" class="mb-3">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale"
              :codice-fiscale="soggettoSelezionato.cf"
            />
            <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else class="mb-3">
            <Button :label="t('resolver.open')" icon="pi pi-search"
              outlined class="w-full" @click="resolverVisible = true" />
            <small class="text-color-secondary">{{ t('pratiche.soggetto_opzionale') }}</small>
          </div>

          <!-- Ruolo (opzionale — visibile solo se soggetto selezionato e ha ruoli) -->
          <div v-if="soggettoSelezionato && ruoliDisponibili.length > 0" class="form-field">
            <label>{{ t('pratiche.field_ruolo') }}</label>
            <Select
              v-model="ruoloSelezionato"
              :options="ruoliDisponibili"
              option-label="label" option-value="value"
              class="w-full" :placeholder="t('pratiche.select_ruolo')" show-clear
            />
          </div>

          <!-- Dati pratica -->
          <h4 class="mt-3">{{ t('pratiche.section_dati') }}</h4>
          <div class="form-field">
            <label>{{ t('pratiche.col_tipo_prestazione') }} *</label>
            <LookupSelect
              v-model="form.tipo_prestazione_id"
              rel="pratiche.tipi_prestazione"
              class="w-full" :placeholder="t('pratiche.select_tipo_prestazione')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.col_priorita') }} *</label>
            <LookupSelect
              v-model="form.priorita_id"
              rel="config.priorita_pratiche"
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

        <!-- Sotto-drawer: SoggettoResolver -->
        <SoggettoResolver
          :visible="resolverVisible"
          tipo-ruolo-codice=""
          @update:visible="v => resolverVisible = v"
          @soggetto-selezionato="onSoggettoRicevuto"
          @soggetto-creato="onSoggettoRicevuto"
          @annullato="resolverVisible = false"
        />
      </template>

      <!-- === EDIT: TabView con Dati + Flussi + Giornale === -->
      <template v-if="isEdit && detail">
        <TabView :key="tabViewKey">

          <!-- Tab Dati -->
          <TabPanel :header="t('pratiche.tab_dati')">
            <!-- Intestazione: codice + stato + priorita' (display dal backend) -->
            <div class="pratica-header-row">
              <div class="form-field" style="flex: 1;">
                <label>{{ t('pratiche.col_codice') }}</label>
                <InputText :model-value="detail.codice" disabled class="w-full" />
              </div>
              <div style="display: flex; gap: 0.5rem; align-self: flex-end;">
                <Tag
                  :value="detail.stato_descrizione"
                  :severity="statoPraticaSeverity(detail.stato_codice_interno)"
                />
                <Tag
                  v-if="detail.priorita_descrizione"
                  :value="detail.priorita_descrizione"
                  :severity="prioritaPraticaSeverity(detail.priorita_codice_interno)"
                />
              </div>
            </div>

            <!-- Soggetto (se presente) -->
            <div v-if="detail.soggetto_display" class="form-field">
              <label>{{ t('pratiche.col_soggetto') }}</label>
              <InputText :model-value="detail.soggetto_display" disabled class="w-full" />
            </div>

            <!-- Azioni stato (nascosto quando nessun bottone visibile) -->
            <div v-if="!isReadonly && statoCorrente !== STATO_PRATICA.CHIUSA && statoCorrente !== STATO_PRATICA.ANNULLATA" class="pratica-actions">
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
                <InputText :model-value="detail.tipo_prestazione_descrizione" disabled class="w-full" />
              </div>
              <div class="form-field">
                <label>{{ t('pratiche.col_priorita') }}</label>
                <LookupSelect
                  v-model="form.priorita_id"
                  rel="config.priorita_pratiche"
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
                  <InputText :model-value="displayDate(detail.data_apertura)" disabled class="w-full" />
                </div>
              </div>
              <div v-if="detail.risorsa_umana_display" class="form-field">
                <label>{{ t('pratiche.col_assegnata_a') }}</label>
                <InputText :model-value="detail.risorsa_umana_display" disabled class="w-full" />
              </div>
            </div>

            <div class="flex justify-end mt-4">
              <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
            </div>
          </TabPanel>

          <!-- Tab Flussi -->
          <TabPanel :header="t('pratiche.tab_flussi')">
            <PraticaFlussiTab
              :pratica-id="props.praticaId"
              :stato-codice-pratica="statoCorrente"
              @refresh="reloadDetail"
            />
          </TabPanel>

          <!-- Tab Note -->
          <TabPanel :header="t('pratiche.tab_note')">
            <PraticaNoteTab :pratica-id="props.praticaId" />
          </TabPanel>

          <!-- Tab Allegati -->
          <TabPanel :header="t('pratiche.tab_allegati')">
            <PraticaAllegatiTab :pratica-id="props.praticaId" />
          </TabPanel>

          <!-- Tab Giornale -->
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
