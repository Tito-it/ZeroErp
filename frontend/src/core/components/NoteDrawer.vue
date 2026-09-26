<script setup>
// Building block "drawer note partizionate" — riusabile cross-dominio.
// Consumato da wrapper di dominio thin (PreventivoNoteDrawer, ContrattoNoteDrawer,
// ecc.) che istanziano l'apiClient con `makeNotesApi(basePath)`.
//
// Pattern formMode: null = lista, 'new' = crea, 'edit' = aggiorna.
// Default applicativi minimi: anchor_tipo e posizione sono governati dal BE
// (BE deriva da target_riga_id: DOCUMENTO/HEADER vs RIGA/AFTER). Stile via
// `LookupSelect rel="config.note_stili"`.
//
// supportsRiga + righeOptions abilitano nota-di-riga: il select riga diventa
// visibile in modalita' "Nuovo"; in edit la riga non e' modificabile (BE blocca).

import { ref, watch, computed, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'

import { fetchParameterDefaults, lookupCodici } from '../apiCore'
import { useApiHandler } from '../composables/useApiHandler'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useDrawerClose } from '../composables/useDrawerClose'
import { useNote } from '../composables/useNote'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../constants'
import LookupSelect from './LookupSelect.vue'
import DrawerTitle from './DrawerTitle.vue'
import FormFooter from './FormFooter.vue'
import PageActionsBar from './PageActionsBar.vue'
import { useDrawerContentReady } from '../composables/useDrawerContentReady'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading: saveLoading, campiErrati } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  apiClient: { type: Object, required: true },
  title: { type: String, default: null },
  // Quando true mostra il select "Riga" nel form (per partizioni con anchor=RIGA).
  supportsRiga: { type: Boolean, default: false },
  // Opzioni per il select riga: [{ value: <id>, label: <codice o descrizione> }].
  // Il caller costruisce l'array dalle righe gia' caricate nel drawer padre.
  righeOptions: { type: Array, default: () => [] },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
// `saved` porta il TOTALE note del documento dopo l'operazione (create, update
// o delete): il drawer lo conosce già dalla lista appena ricaricata, così il
// padre può aggiornare un badge counter senza una seconda chiamata. Il
// payload è additivo — i consumer che ignorano l'argomento non cambiano.
const emit = defineEmits(['update:visible', 'saved'])

// toRef preserva la reattivita' della prop: se il padre cambia preventivoId
// l'apiClient computed restituisce un nuovo oggetto e useNote dereffa via unref.
const { notes, total, loading: listLoading, loadAll, remove } = useNote({
  apiClient: toRef(props, 'apiClient'),
})

// Pagine default lista. 200 e' il cap BE (apps.core.api.partitioned_note_views
// clamp page_size a [1, 200]); chiediamo subito il massimo perche' tipicamente
// le note per documento sono poche decine — niente paginazione UX nella v1.
const PAGE_SIZE_DEFAULT = 200

const formMode = ref(null)
const editId = ref(null)
const form = ref(defaultForm())
const canSelectRiga = computed(() =>
  props.supportsRiga && props.righeOptions.length > 0,
)
const notesTableKey = computed(() =>
  notes.value.map(n => n.id).join('|') || 'empty',
)
const pageActions = computed(() => [
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('note.aggiungi'),
    icon: MANAGE_ICONS.ADD,
    visible: !isReadonly.value && !formMode.value,
    command: onStartNew,
  },
])

function defaultForm() {
  return {
    testo_md: '',
    id_stile: null,
    id_lingua: null,
    target_riga_id: null,
    visibile: true,
    solo_stampa: false,
  }
}

// Cache del default `id_lingua` risolto da parametro sistema.
// Pre-fill UX: in CREATE l'utente vede gia' selezionata la lingua di default
// (es. "it"). Resta modificabile. In edit usa il valore della nota.
// Pattern 2 chiamate: parametro NOTE_DEFAULT_LINGUA (codice_iso) -> lookup
// config.lingue per ottenere l'id. lookupCodici sfrutta la cache globale
// del LookupSelect, quindi spesso 0 round-trip extra.
let _defaultLinguaIdCache = null

async function resolveDefaultLinguaId() {
  if (_defaultLinguaIdCache !== null) return _defaultLinguaIdCache
  try {
    const r = await fetchParameterDefaults(['NOTE_DEFAULT_LINGUA'])
    const codiceIso = r.data?.data?.NOTE_DEFAULT_LINGUA
    if (!codiceIso) return null
    const res = await lookupCodici('config.lingue', { search: codiceIso })
    const match = (res.data?.data?.results || []).find(
      l => l.codice === codiceIso || l.codice_interno === codiceIso,
    )
    _defaultLinguaIdCache = match?.id ?? null
    return _defaultLinguaIdCache
  } catch {
    return null
  }
}

// Ricarica quando il drawer apre OPPURE quando il padre cambia l'apiClient
// (es. cambio preventivoId con drawer aperto): la lista mostrata deve
// riflettere l'entita corrente, niente sgranatura cross-document.
watch(
  [() => props.visible, () => props.apiClient],
  async ([visible]) => {
    if (!visible) return
    formMode.value = null
    editId.value = null
    form.value = defaultForm()
    await loadAll({ page_size: PAGE_SIZE_DEFAULT })
  },
  { immediate: true },
)

async function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  form.value = defaultForm()
  // Pre-fill lingua dal parametro sistema (best-effort, errori silenti).
  // L'utente puo' cambiare la selezione; il BE applica comunque il
  // fallback in save se id_lingua e' null.
  const linguaId = await resolveDefaultLinguaId()
  if (linguaId != null && formMode.value === 'new') {
    form.value.id_lingua = linguaId
  }
}

function onStartEdit(n) {
  formMode.value = 'edit'
  editId.value = n.id
  form.value = {
    testo_md: n.testo_md || n.testo || '',
    id_stile: n.id_stile ?? null,
    id_lingua: n.id_lingua ?? null,
    target_riga_id: n.target_riga_id ?? null,
    visibile: n.visibile !== false,
    solo_stampa: n.solo_stampa === true,
  }
}

function onRowClick(event) {
  if (formMode.value || isReadonly.value) return
  onStartEdit(event.data)
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
}

const canSaveForm = computed(() => {
  const txt = (form.value.testo_md || '').trim()
  return txt.length > 0 && form.value.id_stile != null
})

const onClose = useDrawerClose(emit)

// Scopo: persistenza form. Patch in edit, create in new. Re-fetch lista al successo.
async function onSaveForm() {
  if (!canSaveForm.value) return
  const payload = {
    testo_md: form.value.testo_md,
    id_stile: form.value.id_stile,
    visibile: form.value.visibile,
    solo_stampa: form.value.solo_stampa,
  }
  // id_lingua e' opzionale: invio solo se valorizzato. Se NULL in create,
  // il BE applica il fallback `NOTE_DEFAULT_LINGUA` (codice_iso='it' default).
  if (form.value.id_lingua != null) {
    payload.id_lingua = form.value.id_lingua
  }
  // target_riga_id solo in create (BE lo rifiuta in PATCH).
  if (formMode.value === 'new' && form.value.target_riga_id != null) {
    payload.target_riga_id = form.value.target_riga_id
  }
  const toCall = formMode.value === 'edit' && editId.value
    ? () => props.apiClient.updateNota(editId.value, payload)
    : () => props.apiClient.createNota(payload)
  const result = await execute(toCall, {
    successMessage: t('note.saved'),
  })
  if (result === null) return
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  await loadAll({ page_size: PAGE_SIZE_DEFAULT })
  // `total` è già aggiornato dal loadAll qui sopra.
  emit('saved', total.value)
}

// Scopo: elimina nota per id, ricarica lista, notifica padre.
async function onDelete(n) {
  const ok = await remove(n.id)
  if (ok) {
    await loadAll({ page_size: PAGE_SIZE_DEFAULT })
    emit('saved', total.value)
  }
}

// Decorazione lista: etichetta riga dal mapping righeOptions, fallback id.
function rigaLabel(n) {
  if (n.target_riga_id == null) return null
  const found = props.righeOptions.find(opt => opt.value === n.target_riga_id)
  return found ? found.label : `#${n.target_riga_id}`
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="t('common.edit')"
        :title="title || t('note.titolo_default')"
        icon="pi pi-file-edit"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="!formMode" class="app-page-toolbar">
        <PageActionsBar :actions="pageActions" />
      </div>

      <DataTable
        :key="notesTableKey"
        :value="notes"
        :loading="listLoading"
        data-key="id"
        striped-rows
        size="small"
        removable-sort
        class="app-datatable app-datatable--inner"
        @row-click="onRowClick"
      >
        <template #empty>
          <div class="app-empty-state">
            <i class="pi pi-file-edit" />
            <p>{{ t('note.empty') }}</p>
          </div>
        </template>

        <Column field="anchor_tipo" :header="t('note.col_ambito')" :style="{ width: '110px' }">
          <template #body="{ data }">
            <Tag
              :value="data.anchor_tipo === 'RIGA' ? t('note.tag_riga') : t('note.tag_documento')"
              :severity="data.anchor_tipo === 'RIGA' ? 'info' : 'secondary'"
            />
          </template>
        </Column>
        <Column :header="t('note.col_riga')" :style="{ width: '140px' }">
          <template #body="{ data }">
            <span v-if="rigaLabel(data)">{{ rigaLabel(data) }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column field="posizione" :header="t('note.col_posizione')" :style="{ width: '110px' }" />
        <Column :header="t('note.col_testo')">
          <template #body="{ data }">
            <span class="nota-card-testo">{{ data.testo_md || data.testo }}</span>
          </template>
        </Column>
        <Column field="stile_descrizione" :header="t('note.col_stile')" :style="{ width: '160px' }" />
        <Column :header="t('note.col_lingua')" :style="{ width: '90px' }">
          <template #body="{ data }">
            <span :title="data.lingua_descrizione || ''">{{ data.lingua_codice_iso || '—' }}</span>
          </template>
        </Column>
        <Column :header="t('common.col_azioni')" :style="{ width: '60px' }" :exportable="false">
          <template #body="{ data }">
            <div class="app-row-actions-inline" v-if="!isReadonly && !formMode">
              <Button
                :icon="MANAGE_ICONS.DELETE" text rounded size="small"
                class="app-delete-btn" :title="t('common.delete')"
                @click.stop="onDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <FormFooter v-if="!formMode" close-only @cancel="onClose" />

      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('note.modifica') : t('note.nuova') }}</h4>
        </div>
        <div class="form-grid">
          <div class="form-grid-2col">
            <div class="form-field" v-if="canSelectRiga">
              <label>{{ t('note.field_riga') }}</label>
              <Select
                v-model="form.target_riga_id"
                :options="righeOptions"
                option-label="label" option-value="value"
                :placeholder="t('note.placeholder_riga_doc')"
                :disabled="formMode === 'edit'"
                show-clear 
                :invalid="campiErrati.includes('target_riga_id')"
              />
            </div>
            <div class="form-field">
              <label>{{ t('note.field_stile') }} *</label>
              <LookupSelect
                v-model="form.id_stile"
                rel="config.note_stili"
                :placeholder="t('note.placeholder_stile')"
              />
            </div>
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('note.field_lingua') }}</label>
              <LookupSelect
                v-model="form.id_lingua"
                rel="config.lingue"
                :placeholder="t('note.placeholder_lingua')"
                show-code
                show-clear
              />
            </div>
          </div>
          <div class="form-field">
            <label>{{ t('note.field_testo') }} *</label>
            <Textarea
              v-model="form.testo_md" rows="6" auto-resize
              :placeholder="t('note.placeholder_testo')"
              :invalid="campiErrati.includes('testo_md')"
            />
          </div>
          <div class="form-grid-2col">
            <div class="form-field form-field-inline">
              <label>{{ t('note.field_visibile') }}</label>
              <ToggleSwitch v-model="form.visibile"
                :invalid="campiErrati.includes('visibile')"
              />
            </div>
            <div class="form-field form-field-inline">
              <label>{{ t('note.field_solo_stampa') }}</label>
              <ToggleSwitch v-model="form.solo_stampa"
                :invalid="campiErrati.includes('solo_stampa')"
              />
            </div>
          </div>
        </div>

        <FormFooter
          :loading="saveLoading"
          :disabled="!canSaveForm"
          @save="onSaveForm"
          @cancel="onCancelForm"
        />
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.nota-card-testo {
  font-size: 0.85rem;
  color: var(--app-text-color);
  white-space: pre-wrap;
  word-break: break-word;
}
.text-muted {
  color: var(--app-text-muted);
}
.form-field-inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
</style>
