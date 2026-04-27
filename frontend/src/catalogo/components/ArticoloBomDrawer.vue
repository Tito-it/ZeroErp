<script setup>
// Scopo: Sub-drawer per gestione distinta base (BoM) articolo.
// Layout: toolbar (filtro+reload) + lista paginata 10 righe + form inserimento.
// Pattern immutabilità (sviluppo-listini-v5 §14.4 / DEC-4):
//   - i campi struttura (componente, coeff_qta, esposto_in_fattura, ecc.)
//     non sono modificabili in place: trigger DB E_BOM_MODIFICA_VIETATA li
//     blocca. Per correggere si usa "chiudi riga" + "duplica come nuova
//     versione" (l'admin chiude la riga corrente e ne crea una nuova).
//   - delete BoM bloccato dal trigger: il pattern di "rimozione" è chiusura
//     con valido_al = oggi (chiusura immediata) o data futura (programmata).
//   - valido_al è l'unico campo struttura editabile inline (chiusura riga)
//     o via dialog dedicato (pattern simmetrico a ChiudiVersioneDialog dei
//     listini, vedi feedback_stato_terminale_con_data).
// Standard sub-drawer: paginazione 10 righe, ReloadButton + F5, filtro
// client-side articolo, sort default articolo_descrizione.

import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import {
  listArticoloComponenti, createArticoloComponente,
  updateArticoloComponente,
  listComponenteNote, createComponenteNota,
} from '../api/catalogo'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import { displayDate, toDateString } from '../../core/utils/date'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import CatalogoNoteDrawer from '../../core/components/CatalogoNoteDrawer.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import NewButton from '../../core/components/NewButton.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import Drawer from 'primevue/drawer'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const componentiList = ref([])
const listLoading = ref(false)

// Filtro client-side articolo (codice + descrizione, case-insensitive).
// Coerente con il pattern ContrattoRigheDrawer: la lista BoM è tipicamente
// sotto le 50-100 righe per articolo, niente bisogno di filtro server-side.
const filtroArticolo = ref('')

const componentiView = computed(() => {
  const filtro = (filtroArticolo.value || '').trim().toLowerCase()
  if (!filtro) return componentiList.value
  return componentiList.value.filter(r => {
    const codice = (r.componente_codice || '').toLowerCase()
    const desc = (r.componente_descrizione || '').toLowerCase()
    return codice.includes(filtro) || desc.includes(filtro)
  })
})

// Form inserimento nuovo componente
const form = ref({})
const componenteObj = ref(null)
const adding = ref(false)

// Edit inline: traccia quale riga ha il DatePicker valido_al aperto.
// valido_al è l'unico campo modificabile in place (DEC-4): permette
// chiusura immediata della riga senza passare dal kebab.
const editingValidoAlId = ref(null)
const editingValidoAlValue = ref(null)

// Dialog chiusura riga (pattern simmetrico a ChiudiVersioneDialog).
// Sostituisce il vecchio confirmAction semplice: ora l'admin sceglie
// data di chiusura (oggi = immediata, futura = programmata) con min-date
// vincolato a valido_dal della riga (no chiusura prima dell'inizio).
const chiudiDialogVisible = ref(false)
const chiudiDialogRow = ref(null)
const chiudiDialogData = ref(null)
const chiudiDialogMinDate = computed(() => parseDate(chiudiDialogRow.value?.valido_dal) || new Date())
const chiudiDialogIsImmediata = computed(() => {
  if (!chiudiDialogData.value) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const sel = new Date(chiudiDialogData.value)
  sel.setHours(0, 0, 0, 0)
  return sel.getTime() === today.getTime()
})

// Flag UI: distingue "nuovo componente da zero" da "duplica come nuova versione".
// Influenza il titolo del form e mostra l'hint dedicato versionamento.
const formMode = ref('new')  // 'new' | 'duplicate'

// Sub-drawer note per componente
const noteDrawerVisible = ref(false)
const noteCompId = ref(null)

const noteListFn = computed(() => () => listComponenteNote(props.articoloId, noteCompId.value))
const noteCreateFn = computed(() => (payload) => createComponenteNota(props.articoloId, noteCompId.value, payload))

function openNoteDrawer(row) {
  noteCompId.value = row.id
  noteDrawerVisible.value = true
}

function defaultForm() {
  return {
    componente_id: null,
    coeff_qta: 1,
    partecipa_qta: true,
    obbligatorio: true,
    determina_qta_padre: false,
    esposto_in_fattura: false,
    valido_dal: new Date(),
    valido_al: null,
  }
}

// Scopo: reset stato del form add/duplica. Comune a cancel, save-success
// e apertura drawer: evita duplicazione delle 4 reassegnazioni.
function resetFormState() {
  adding.value = false
  formMode.value = 'new'
  form.value = defaultForm()
  componenteObj.value = null
}

// Scopo: Converte stringa ISO date in Date object per DatePicker.
function parseDate(val) {
  if (!val) return null
  if (val instanceof Date) return val
  const d = new Date(val)
  return isNaN(d.getTime()) ? null : d
}

// Scopo: Carica lista componenti dell'articolo.
async function loadComponenti() {
  if (!props.articoloId) return
  listLoading.value = true
  try {
    const res = await listArticoloComponenti(props.articoloId)
    const payload = res.data?.data
    componentiList.value = payload?.results || payload || []
  } catch {
    componentiList.value = []
  } finally {
    listLoading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (!val) return
  resetFormState()
  editingValidoAlId.value = null
  filtroArticolo.value = ''
  loadComponenti()
})

// Shortcut F5: ricarica la lista senza reload del browser. Coerente con il
// pattern useSearchTable e con gli altri sub-drawer (ContrattoRigheDrawer).
// Attivo solo quando il drawer è visibile (il drawer è persistente: register
// in onMounted, deregister in onUnmounted, no leak su mount/unmount parent).
function onKeydown(e) {
  if (e.key === 'F5' && props.visible) {
    e.preventDefault()
    loadComponenti()
  }
}
onMounted(() => { window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('keydown', onKeydown) })

// Scopo: Callback quando l'utente seleziona un articolo dal lookup.
function onComponenteSelect(item) {
  componenteObj.value = item
  form.value.componente_id = item?.id || null
}

function startAdd() {
  resetFormState()
  adding.value = true
}

function cancelAdd() {
  resetFormState()
}

// Scopo: pre-compila il form di inserimento con i valori di una riga
// esistente, per creare una nuova versione senza ridigitare tutto.
// La riga sorgente NON viene chiusa automaticamente: l'admin può scegliere
// di farlo prima/dopo via "Chiudi riga". L'exclusion constraint daterange
// del DB previene comunque sovrapposizioni.
function startDuplicaComeNuovaVersione(row) {
  formMode.value = 'duplicate'
  // Pre-compila componente_obj per restore AutoComplete: ArticoloLookup
  // usa optionLabel="_display" (formato "codice — descrizione"), senza
  // questo campo l'AutoComplete cade in toString() e mostra "[object Object]".
  componenteObj.value = {
    id: row.componente_id,
    codice: row.componente_codice,
    descrizione: row.componente_descrizione,
    _display: `${row.componente_codice} — ${row.componente_descrizione}`,
  }
  form.value = {
    componente_id: row.componente_id,
    coeff_qta: row.coeff_qta,
    partecipa_qta: row.partecipa_qta,
    obbligatorio: row.obbligatorio,
    determina_qta_padre: row.determina_qta_padre,
    esposto_in_fattura: row.esposto_in_fattura,
    valido_dal: new Date(),  // nuova versione parte da oggi
    valido_al: null,
  }
  adding.value = true
}

const canSaveForm = computed(() => {
  return form.value.componente_id != null && form.value.coeff_qta > 0
})

// Scopo: Inserisce nuovo componente. Ricarica lista e notifica il parent.
async function onSaveNew() {
  const payload = {
    componente_id: form.value.componente_id,
    coeff_qta: form.value.coeff_qta,
    partecipa_qta: form.value.partecipa_qta,
    obbligatorio: form.value.obbligatorio,
    determina_qta_padre: form.value.determina_qta_padre,
    esposto_in_fattura: form.value.esposto_in_fattura,
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
  }
  const result = await execute(
    () => createArticoloComponente(props.articoloId, payload),
    { successMessage: t('catalogo.componente_aggiunto') }
  )
  if (result === null) return
  resetFormState()
  await loadComponenti()
  emit('saved')
}

// Scopo: Apre edit inline valido_al per una riga.
function startEditValidoAl(row) {
  editingValidoAlId.value = row.id
  editingValidoAlValue.value = parseDate(row.valido_al)
}

// Scopo: Salva valido_al modificato inline.
async function confirmEditValidoAl(row) {
  const result = await execute(
    () => updateArticoloComponente(props.articoloId, row.id, {
      valido_al: toDateString(editingValidoAlValue.value),
    }),
    { successMessage: t('catalogo.componente_salvato') }
  )
  if (result === null) return
  editingValidoAlId.value = null
  editingValidoAlValue.value = null
  await loadComponenti()
  emit('saved')
}

function cancelEditValidoAl() {
  editingValidoAlId.value = null
  editingValidoAlValue.value = null
}

// Scopo: apre il dialog di chiusura riga BoM con DatePicker. Sostituisce il
// vecchio confirmAction semplice. Pattern simmetrico a ChiudiVersioneDialog
// (listini-versioni): l'admin sceglie la data, default oggi (chiusura
// immediata), futura ammessa (chiusura programmata). Min-date = valido_dal
// della riga: la BoM non può "chiudersi prima di iniziare". Il delete BoM
// resta bloccato dal trigger DB E_BOM_MODIFICA_VIETATA.
function onChiudiRiga(row) {
  chiudiDialogRow.value = row
  // Default oggi se >= valido_dal, altrimenti valido_dal stesso (caso
  // "riga futura" ipotetico — oggi non è ancora dentro la finestra).
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const dal = parseDate(row.valido_dal)
  chiudiDialogData.value = dal && dal > today ? dal : today
  chiudiDialogVisible.value = true
}

function annullaChiusura() {
  chiudiDialogVisible.value = false
  chiudiDialogRow.value = null
  chiudiDialogData.value = null
}

async function confermaChiusura() {
  if (!chiudiDialogRow.value || !chiudiDialogData.value) return
  const result = await execute(
    () => updateArticoloComponente(props.articoloId, chiudiDialogRow.value.id, {
      valido_al: toDateString(chiudiDialogData.value),
    }),
    { successMessage: t('catalogo.componente_chiuso') }
  )
  if (result !== null) {
    annullaChiusura()
    await loadComponenti()
    emit('saved')
  }
}

// Scopo: azioni di riga del componente BoM (note + duplica + chiudi).
// Nascoste in readonly. La voce "elimina" non esiste più: la BoM è
// immutabile (DEC-4), il pattern è "chiudi+inserisci nuova versione".
function buildRigaActions(row) {
  return [
    {
      key: 'gestisci-note',
      label: t('catalogo.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => openNoteDrawer(row),
    },
    {
      key: 'duplica-nuova-versione',
      label: t('catalogo.duplica_come_nuova_versione'),
      icon: 'pi pi-clone',
      command: () => startDuplicaComeNuovaVersione(row),
    },
    {
      key: 'chiudi-riga',
      label: t('catalogo.chiudi_riga'),
      icon: 'pi pi-calendar-times',
      severity: 'danger',
      command: () => onChiudiRiga(row),
    },
  ]
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('catalogo.tab_bom')" icon="pi pi-sitemap" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading">
        <!-- Hint immutabilità (defense-in-depth UX): spiega il pattern
             chiudi+inserisci che sostituisce l'edit in place. -->
        <Message
          v-if="!isReadonly && componentiList.length > 0"
          severity="info"
          :closable="false"
          class="mt-025"
        >
          {{ t('catalogo.bom_immutabile_hint') }}
        </Message>

        <!-- Toolbar standard sub-drawer: filtro + reload + nuovo. Visibile
             sempre (anche con lista vuota) per esporre il pulsante "Aggiungi
             componente" come azione primaria — pattern allineato a
             ContrattoRigheDrawer. Filtro nascosto se non c'e' nulla da filtrare. -->
        <div v-if="!isReadonly" class="app-page-toolbar">
          <div class="app-page-filters">
            <InputText v-if="componentiList.length > 0"
              v-model="filtroArticolo"
              :placeholder="t('catalogo.filtro_componente_placeholder')"
              style="min-width: 240px;" />
          </div>
          <div class="app-page-actions">
            <ReloadButton @click="loadComponenti" />
            <NewButton :tooltip="t('catalogo.aggiungi_componente')"
              :disabled="adding" @click="startAdd" />
          </div>
        </div>

        <!-- Lista componenti (sempre visibile) -->
        <div v-if="componentiList.length === 0 && !adding" class="app-empty-state">
          <i class="pi pi-sitemap" />
          <p>{{ t('catalogo.nessun_componente') }}</p>
        </div>

        <DataTable
          v-if="componentiList.length > 0"
          :value="componentiView"
          class="app-datatable"
          striped-rows
          paginator
          :rows="10"
          :rows-per-page-options="[10, 25, 50]"
          paginator-position="top"
          sort-field="componente_descrizione"
          :sort-order="1"
          removable-sort
          data-key="id"
        >
          <Column field="componente_codice" :header="t('catalogo.col_codice')" sortable />
          <Column field="componente_descrizione" :header="t('catalogo.col_descrizione')" sortable />
          <Column field="coeff_qta" :header="t('catalogo.col_coeff_qta')" style="width: 70px;" sortable />
          <Column field="esposto_in_fattura" :header="t('catalogo.col_esposto_fattura')" style="width: 80px;">
            <template #body="{ data }">
              <i :class="data.esposto_in_fattura ? 'pi pi-check text-green-500' : 'pi pi-minus text-color-secondary'" />
            </template>
          </Column>
          <Column field="valido_al" :header="t('catalogo.field_valido_al')" style="width: 130px;" sortable>
            <template #body="{ data }">
              <template v-if="editingValidoAlId === data.id">
                <div class="flex gap-1 align-items-center">
                  <DatePicker v-model="editingValidoAlValue" :date-format="DATE_FORMAT"
                    show-icon show-button-bar style="width: 110px;" />
                  <Button icon="pi pi-check" text rounded size="small" class="app-action-btn"
                    @click="confirmEditValidoAl(data)" />
                  <Button icon="pi pi-times" text rounded size="small"
                    @click="cancelEditValidoAl" />
                </div>
              </template>
              <template v-else>
                <span v-if="!isReadonly" class="valido-al-cell" @click="startEditValidoAl(data)">
                  {{ displayDate(data.valido_al) || '—' }}
                  <i class="pi pi-pencil" style="font-size: 0.7rem; margin-left: 0.25rem; opacity: 0.5;" />
                </span>
                <span v-else>{{ displayDate(data.valido_al) || '—' }}</span>
              </template>
            </template>
          </Column>
          <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
            <template #body="{ data }">
              <RowActionsMenu :actions="buildRigaActions(data)" />
            </template>
          </Column>
        </DataTable>

        <!-- Form inserimento nuovo componente. Pulsante di apertura ora
             nella toolbar in alto (NewButton); qui solo il form quando
             adding=true. -->
        <template v-if="!isReadonly">
          <template v-if="adding">
            <div class="app-drawer-section">
              <h4>{{ formMode === 'duplicate' ? t('catalogo.nuova_versione_componente') : t('catalogo.nuovo_componente') }}</h4>
            </div>
            <Message
              v-if="formMode === 'duplicate'"
              severity="warn"
              :closable="false"
              class="mt-025"
            >
              {{ t('catalogo.nuova_versione_hint') }}
            </Message>
            <div class="form-grid">
              <div class="form-field">
                <label>{{ t('catalogo.field_componente') }} *</label>
                <ArticoloLookup
                  :model-value="componenteObj"
                  :placeholder="t('catalogo.search_componente')"
                  @select="onComponenteSelect"
                />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_coeff_qta') }} *</label>
                <InputNumber v-model="form.coeff_qta" :min="0" :min-fraction-digits="2"
                  :max-fraction-digits="6" class="w-full" />
              </div>
            </div>
            <div class="form-grid-2col mt-05">
              <div class="form-field">
                <label>{{ t('catalogo.field_valido_dal') }}</label>
                <DatePicker v-model="form.valido_dal" :date-format="DATE_FORMAT"
                  show-icon show-button-bar class="w-full" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_valido_al') }}</label>
                <DatePicker v-model="form.valido_al" :date-format="DATE_FORMAT"
                  show-icon show-button-bar class="w-full" />
              </div>
            </div>
            <div class="form-grid-2col mt-05">
              <div class="form-field">
                <label>{{ t('catalogo.field_obbligatorio') }}</label>
                <ToggleSwitch v-model="form.obbligatorio" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_partecipa_qta') }}</label>
                <ToggleSwitch v-model="form.partecipa_qta" />
              </div>
            </div>
            <div class="form-grid-2col mt-05">
              <div class="form-field">
                <label>{{ t('catalogo.field_esposto_fattura') }}</label>
                <ToggleSwitch v-model="form.esposto_in_fattura" />
              </div>
            </div>
            <div class="flex justify-end gap-2 mt-05">
              <Button :label="t('common.cancel')" text @click="cancelAdd" />
              <Button :label="t('common.save')" :loading="loading" :disabled="!canSaveForm" @click="onSaveNew" />
            </div>
          </template>
        </template>
      </template>
    </div>
  </Drawer>

  <CatalogoNoteDrawer
    :visible="noteDrawerVisible"
    @update:visible="v => noteDrawerVisible = v"
    :list-fn="noteListFn"
    :create-fn="noteCreateFn"
    :title="t('catalogo.tab_note')"
    @saved="loadComponenti"
  />

  <!-- Dialog chiusura riga BoM. Pattern simmetrico a ChiudiVersioneDialog
       dei listini-versioni: DatePicker default oggi, min-date = valido_dal
       della riga, conferma esplicita per evitare PATCH involontario. -->
  <Dialog
    :visible="chiudiDialogVisible"
    @update:visible="v => { if (!v) annullaChiusura() }"
    modal
    :header="t('catalogo.chiudi_riga_dialog_titolo')"
    :style="{ width: '480px' }"
  >
    <Message
      v-if="chiudiDialogIsImmediata"
      severity="warn"
      :closable="false"
      class="mb-1"
    >
      {{ t('catalogo.chiudi_riga_warn_immediata') }}
    </Message>
    <Message
      v-else-if="chiudiDialogData"
      severity="info"
      :closable="false"
      class="mb-1"
    >
      {{ t('catalogo.chiudi_riga_info_programmata', {
        data: displayDate(chiudiDialogData)
      }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('catalogo.chiudi_riga_data') }}</label>
        <DatePicker v-model="chiudiDialogData" :date-format="DATE_FORMAT"
          show-icon show-button-bar :min-date="chiudiDialogMinDate" />
      </div>
    </div>

    <div class="flex justify-end gap-2 mt-1">
      <Button :label="t('common.cancel')" text @click="annullaChiusura" />
      <Button :label="t('catalogo.chiudi_riga_conferma')"
        icon="pi pi-calendar-times" severity="warn"
        :disabled="!chiudiDialogData || loading" :loading="loading"
        @click="confermaChiusura" />
    </div>
  </Dialog>
</template>

<style scoped>
.valido-al-cell {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.valido-al-cell:hover {
  color: var(--p-primary-color);
}
</style>
