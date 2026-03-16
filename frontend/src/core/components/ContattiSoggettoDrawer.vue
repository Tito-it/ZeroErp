<script setup>
// Scopo: Drawer dedicato per gestione contatti di un soggetto.
// Riutilizzabile da: SoggettoDrawer (edit), futuro ClienteDrawer, FornitoreDrawer.
// Lista contatti esistenti (click per modifica) + aggiungi nuovo.

import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../composables/useApiHandler'
import { useContattoForm } from '../composables/useContattoForm'
import {
  listSoggettoContatti, createSoggettoContatto,
  updateSoggettoContatto, deleteSoggettoContatto
} from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH } from '../constants'
import ContattoForm from './ContattoForm.vue'
import DrawerTitle from './DrawerTitle.vue'
import DrawerFooter from './DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const contatto = useContattoForm()

const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: String, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

// Lista contatti esistenti
const contattiList = ref([])
const listLoading = ref(false)

// Modalita' form: null = lista, 'new' = aggiungi, 'edit' = modifica
const formMode = ref(null)
const editId = ref(null)

async function loadContatti() {
  if (!props.soggettoId) return
  listLoading.value = true
  try {
    const res = await listSoggettoContatti(props.soggettoId)
    contattiList.value = res.data.data.results || res.data.data
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
  contatto.reset()
  contatto.tipiContatto.load()
}

function onStartEdit(c) {
  formMode.value = 'edit'
  editId.value = c.id
  contatto.populate(c)
  contatto.tipiContatto.load()
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  contatto.reset()
}

async function onSaveForm() {
  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateSoggettoContatto(props.soggettoId, editId.value, { ...contatto.form }),
      { successMessage: t('contatto.contatto_salvato') }
    )
    if (result === null) return
  } else {
    const result = await execute(
      () => createSoggettoContatto(props.soggettoId, { ...contatto.form }),
      { successMessage: t('contatto.contatto_creato') }
    )
    if (result === null) return
  }

  formMode.value = null
  editId.value = null
  contatto.reset()
  await loadContatti()
  emit('saved')
}

async function onDelete(c) {
  const result = await execute(
    () => deleteSoggettoContatto(props.soggettoId, c.id),
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

    <div class="app-drawer-content">
      <!-- Loading -->
      <div v-if="listLoading" style="text-align: center; padding: 1rem;">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <!-- Lista contatti esistenti -->
      <template v-if="!listLoading">
        <div v-if="contattiList.length === 0 && !formMode" class="contatti-empty">
          <i class="pi pi-users" style="font-size: 1.5rem; opacity: 0.3;" />
          <p>{{ t('contatto.nessun_contatto') }}</p>
        </div>

        <div v-else-if="contattiList.length > 0" class="contatti-list">
          <div v-for="c in contattiList" :key="c.id" class="contatto-card">
            <div class="contatto-card-content">
              <div class="contatto-card-nome">
                <Tag v-if="c.tipo_contatto_descrizione" :value="c.tipo_contatto_descrizione" severity="info" />
                <strong>{{ c.nominativo }}</strong>
              </div>
              <div class="contatto-card-detail">
                <span v-if="c.email"><i class="pi pi-envelope" /> {{ c.email }}</span>
                <span v-if="c.telefono"><i class="pi pi-phone" /> {{ c.telefono }}</span>
                <span v-if="c.cellulare"><i class="pi pi-mobile" /> {{ c.cellulare }}</span>
                <span v-if="c.pec"><i class="pi pi-at" /> {{ c.pec }}</span>
              </div>
            </div>
            <div v-if="!formMode" class="contatto-card-actions">
              <Button icon="pi pi-pencil" text rounded size="small"
                class="app-action-btn" :title="t('common.edit')" @click="onStartEdit(c)" />
              <Button icon="pi pi-trash" severity="danger" text rounded size="small"
                :title="t('common.delete')" @click="onDelete(c)" />
            </div>
          </div>
        </div>

        <!-- Pulsante aggiungi -->
        <div v-if="!formMode" style="margin-top: 0.5rem;">
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

.contatti-empty {
  text-align: center;
  padding: 1.5rem;
  color: var(--p-text-muted-color);
}

.app-drawer-section {
  margin-top: 1rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--app-border-color, #e0e0e0);
}
.app-drawer-section h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--app-text-secondary, #666);
}
</style>
