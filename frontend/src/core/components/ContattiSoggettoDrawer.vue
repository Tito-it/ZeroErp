<script setup>
// Scopo: Drawer dedicato per gestione contatti di un soggetto.
// Riutilizzabile da: SoggettoDrawer (edit), futuro ClienteDrawer, FornitoreDrawer.
// Lista contatti esistenti (click per modifica) + aggiungi nuovo.

import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { useContattoForm } from '../composables/useContattoForm'
import {
  listSoggettoContatti, createSoggettoContatto,
  updateSoggettoContatto, deleteSoggettoContatto,
  listRuoloContatti, createRuoloContatto,
  updateRuoloContatto, deleteRuoloContatto
} from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH } from '../constants'
import { sortByFonte } from '../utils/string'
import ContattoForm from './ContattoForm.vue'
import DrawerTitle from './DrawerTitle.vue'
import DrawerFooter from './DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()
const contatto = useContattoForm()

// Context 'soggetto' (default) o 'ruolo': determina quale set di API usare.
// Per 'soggetto': soggettoId = soggetto UUID. Per 'ruolo': soggettoId = soggetto_ruolo_id (int).
// istanzaUtilityId: opzionale, usato in context 'ruolo' per cascata a 3 livelli.
const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: [String, Number], default: null },
  context: { type: String, default: 'soggetto' },
  istanzaUtilityId: { type: Number, default: null }
})

// Scopo: Risolve le funzioni API in base al context (soggetto o ruolo).
function apiFor(action) {
  if (props.context === 'ruolo') {
    return { list: listRuoloContatti, create: createRuoloContatto,
             update: updateRuoloContatto, remove: deleteRuoloContatto }[action]
  }
  return { list: listSoggettoContatti, create: createSoggettoContatto,
           update: updateSoggettoContatto, remove: deleteSoggettoContatto }[action]
}

const emit = defineEmits(['update:visible', 'saved'])

// Lista contatti: in context ruolo contiene sia ruolo (editabili) che soggetto (readonly)
const contattiList = ref([])
const listLoading = ref(false)

// Modalita' form: null = lista, 'new' = aggiungi, 'edit' = modifica
const formMode = ref(null)
const editId = ref(null)
const formErrors = ref([])

// Scopo: Carica contatti. In context 'ruolo' l'API ritorna contatti_ruolo + contatti_soggetto
//        con campo 'fonte'. In context 'soggetto' ritorna lista piatta.
async function loadContatti() {
  if (!props.soggettoId) return
  listLoading.value = true
  try {
    const listParams = props.context === 'ruolo' && props.istanzaUtilityId
      ? { istanza_utility_id: props.istanzaUtilityId } : {}
    const res = await apiFor('list')(props.soggettoId, listParams)
    const payload = res.data?.data
    if (props.context === 'ruolo' && payload?.contatti_ruolo) {
      // Il backend gia' include 'fonte' (utility/ruolo/soggetto) nei dict
      contattiList.value = sortByFonte([
        ...payload.contatti_ruolo,
        ...(payload.contatti_soggetto || []),
      ])
    } else {
      const items = payload?.results || payload || []
      contattiList.value = items.sort((a, b) =>
        (a.tipo_contatto_descrizione || '').localeCompare(b.tipo_contatto_descrizione || '')
      )
    }
  } catch {
    contattiList.value = []
  } finally {
    listLoading.value = false
  }
}

// Carica dati quando drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  formMode.value = null
  editId.value = null
  contatto.reset()
  await loadContatti()
})

// === Azioni ===

function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  formErrors.value = []
  contatto.reset()
  contatto.tipiContatto.load()
  contatto.unitaOrganizzative.load()
}

function onStartEdit(c) {
  formMode.value = 'edit'
  editId.value = c.id
  formErrors.value = []
  contatto.populate(c)
  contatto.tipiContatto.load()
  contatto.unitaOrganizzative.load()
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  formErrors.value = []
  contatto.reset()
}

async function onSaveForm() {
  formErrors.value = contatto.validate()
  if (formErrors.value.length > 0) return

  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => apiFor('update')(props.soggettoId, editId.value, { ...contatto.form }),
      { successMessage: t('contatto.contatto_salvato') }
    )
    if (result === null) return
  } else {
    const result = await execute(
      () => apiFor('create')(props.soggettoId, {
        ...contatto.form,
        ...(props.context === 'ruolo' && props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId } : {})
      }),
      { successMessage: t('contatto.contatto_creato') }
    )
    if (result === null) return
  }

  formMode.value = null
  editId.value = null
  formErrors.value = []
  contatto.reset()
  await loadContatti()
  emit('saved')
}

async function onDelete(c) {
  const result = await execute(
    () => apiFor('remove')(props.soggettoId, c.id),
    { successMessage: t('contatto.contatto_eliminato') }
  )
  if (result !== null) {
    await loadContatti()
    emit('saved')
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('soggetti.section_contatto')" icon="pi pi-id-card" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <!-- Loading -->
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <!-- Lista contatti esistenti -->
      <template v-if="!listLoading">
        <div v-if="contattiList.length === 0 && !formMode" class="app-empty-state">
          <i class="pi pi-users" />
          <p>{{ t('contatto.nessun_contatto') }}</p>
        </div>

        <div v-else-if="contattiList.length > 0" class="contatti-list">
          <div v-for="c in contattiList" :key="c.id"
            class="contatto-card" :class="{ 'contatto-card-soggetto': c.fonte === 'soggetto', 'contatto-card-ruolo': c.fonte === 'ruolo' || c.fonte === 'istanza' }">
            <div class="contatto-card-content">
              <div class="contatto-card-nome">
                <Tag v-if="c.fonte" :value="c.fonte === 'soggetto' ? t('common.soggetto') : (c.fonte === 'istanza' && c.utility_codice ? c.utility_codice : t('common.ruolo'))"
                  :severity="c.fonte === 'soggetto' ? 'secondary' : 'info'" />
                <Tag v-if="c.tipo_contatto_descrizione"
                  :value="c.tipo_contatto_descrizione"
                  severity="info" />
                <strong>{{ c.nominativo }}</strong>
              </div>
              <div class="contatto-card-detail">
                <span v-if="c.email"><i class="pi pi-envelope" /> {{ c.email }}</span>
                <span v-if="c.telefono"><i class="pi pi-phone" /> {{ c.telefono }}</span>
                <span v-if="c.cellulare"><i class="pi pi-mobile" /> {{ c.cellulare }}</span>
                <span v-if="c.pec"><i class="pi pi-at" /> {{ c.pec }}</span>
              </div>
            </div>
            <div v-if="!formMode && !isReadonly && c.fonte !== 'soggetto'" class="contatto-card-actions">
              <Button icon="pi pi-pencil" text rounded size="small"
                class="app-action-btn" :title="t('common.edit')" @click="onStartEdit(c)" />
              <Button icon="pi pi-trash" severity="danger" text rounded size="small"
                :title="t('common.delete')" @click="onDelete(c)" />
            </div>
          </div>
        </div>

        <!-- Pulsante aggiungi (nascosto in readonly) -->
        <div v-if="!formMode && !isReadonly" class="mt-05">
          <Button
            :label="t('contatto.aggiungi_contatto')"
            icon="pi pi-plus"
            text
            size="small"
            class="app-action-btn"
            @click="onStartNew"
          />
        </div>
      </template>

      <!-- Form (aggiungi o modifica) -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('contatto.modifica_contatto') : t('contatto.nuovo_contatto') }}</h4>
        </div>
        <ContattoForm
          :form="contatto.form"
          :tipi-contatto="contatto.tipiContatto"
          :unita-organizzative="contatto.unitaOrganizzative"
          :errors="formErrors"
          :show-u-o="true"
          :tipo-disabled="formMode === 'edit'"
          :disabled="false"
        />

        <DrawerFooter
          :loading="loading"
          :disabled="!contatto.form.nominativo?.trim()"
          @save="onSaveForm"
          @cancel="onCancelForm"
        />
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.contatti-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.contatto-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-sm, 4px);
  padding: 0.5rem 0.75rem;
}

.contatto-card-soggetto {
  border-color: var(--p-orange-300);
  opacity: 0.5;
}
.contatto-card-ruolo {
  border-color: var(--p-blue-300);
}

.contatto-card-content {
  flex: 1;
  min-width: 0;
}

.contatto-card-nome {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.contatto-card-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.contatto-card-detail i {
  font-size: 0.75rem;
  margin-right: 0.15rem;
}

.contatto-card-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}
</style>
