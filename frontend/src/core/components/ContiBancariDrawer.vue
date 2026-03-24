<script setup>
// Scopo: Drawer dedicato per gestione conti bancari di un soggetto (o ruolo).
// Riutilizzabile da: SoggettoDrawer (edit), futuro RuoloDrawer.
// Lista conti esistenti (click per modifica) + aggiungi nuovo.
// Context 'soggetto' o 'ruolo' determina API chiamate.

import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { useContoBancarioForm } from '../composables/useContoBancarioForm'
import { useConfirmAction } from '../composables/useConfirmAction'
import {
  listSoggettoContiBancari, createSoggettoContoBancario,
  updateSoggettoContoBancario, deleteSoggettoContoBancario,
  listRuoloContiBancari, createRuoloContoBancario,
  updateRuoloContoBancario, deleteRuoloContoBancario
} from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH } from '../constants'
import ContoBancarioForm from './ContoBancarioForm.vue'
import DrawerTitle from './DrawerTitle.vue'
import DrawerFooter from './DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()
const conto = useContoBancarioForm()
const { confirmDelete } = useConfirmAction()

// Context 'soggetto' (default) o 'ruolo': determina quale set di API usare.
// Per 'soggetto': ownerId = soggetto UUID. Per 'ruolo': ownerId = soggetto_ruolo_id (int).
const props = defineProps({
  visible: { type: Boolean, default: false },
  ownerId: { type: [String, Number], default: null },
  ownerName: { type: String, default: '' },
  context: { type: String, default: 'soggetto' }
})

// Scopo: Risolve le funzioni API in base al context (soggetto o ruolo).
function apiFor(action) {
  if (props.context === 'ruolo') {
    return { list: listRuoloContiBancari, create: createRuoloContoBancario,
             update: updateRuoloContoBancario, remove: deleteRuoloContoBancario }[action]
  }
  return { list: listSoggettoContiBancari, create: createSoggettoContoBancario,
           update: updateSoggettoContoBancario, remove: deleteSoggettoContoBancario }[action]
}

const emit = defineEmits(['update:visible', 'saved'])

// Lista conti esistenti
const contiList = ref([])
const listLoading = ref(false)

// Modalita' form: null = lista, 'new' = aggiungi, 'edit' = modifica
const formMode = ref(null)
const editId = ref(null)
const formErrors = ref([])

// Scopo: Carica lista conti bancari dal backend.
//        In context 'ruolo' l'API ritorna conti_ruolo + conti_ereditati.
async function loadConti() {
  if (!props.ownerId) return
  listLoading.value = true
  try {
    const res = await apiFor('list')(props.ownerId)
    const payload = res.data?.data
    if (props.context === 'ruolo' && payload?.conti_ruolo) {
      contiList.value = [
        ...payload.conti_ruolo.map(c => ({ ...c, fonte: 'ruolo' })),
        ...(payload.conti_ereditati || []).map(c => ({ ...c, fonte: 'soggetto' })),
      ]
    } else {
      contiList.value = payload?.results || payload || []
    }
  } catch {
    contiList.value = []
  } finally {
    listLoading.value = false
  }
}

// Carica dati quando drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  formMode.value = null
  editId.value = null
  formErrors.value = []
  conto.reset(props.ownerName)
  await loadConti()
})

// === Azioni ===

function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  formErrors.value = []
  conto.reset(props.ownerName)
}

function onStartEdit(c) {
  formMode.value = 'edit'
  editId.value = c.id
  formErrors.value = []
  conto.populate(c)
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  formErrors.value = []
  conto.reset()
}

async function onSaveForm() {
  formErrors.value = conto.validate()
  if (formErrors.value.length > 0) return

  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => apiFor('update')(props.ownerId, editId.value, conto.toUpdatePayload()),
      { successMessage: t('conti_bancari.conto_salvato') }
    )
    if (result === null) return
  } else {
    const result = await execute(
      () => apiFor('create')(props.ownerId, conto.toCreatePayload()),
      { successMessage: t('conti_bancari.conto_creato') }
    )
    if (result === null) return
  }

  formMode.value = null
  editId.value = null
  formErrors.value = []
  conto.reset()
  await loadConti()
  emit('saved')
}

async function onDelete(c) {
  const ibanShort = maskIban(c.iban)
  confirmDelete({
    message: t('conti_bancari.conferma_elimina', { iban: ibanShort, uso: c.uso }),
    accept: async () => {
      const result = await execute(
        () => apiFor('remove')(props.ownerId, c.id),
        { successMessage: t('conti_bancari.conto_eliminato') }
      )
      if (result !== null) {
        await loadConti()
        emit('saved')
      }
    }
  })
}

// Scopo: Maschera IBAN per visualizzazione card (primi 4 + ultimi 4).
function maskIban(iban) {
  if (!iban || iban.length <= 8) return iban || ''
  return iban.substring(0, 4) + '****' + iban.substring(iban.length - 4)
}

// Scopo: Severity tag per tipo uso.
function usoSeverity(uso) {
  const map = { INCASSO: 'success', PAGAMENTO: 'info', RIMBORSO: 'warn', GENERICO: 'secondary' }
  return map[uso] || 'secondary'
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
      <DrawerTitle :action="formMode === 'new' ? t('common.new') : t('common.edit')" :title="t('conti_bancari.titolo')" icon="pi pi-wallet" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <!-- Loading -->
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <!-- Lista conti esistenti -->
      <template v-if="!listLoading">
        <div v-if="contiList.length === 0 && !formMode" class="app-empty-state">
          <i class="pi pi-wallet" />
          <p>{{ t('conti_bancari.nessun_conto') }}</p>
        </div>

        <div v-else-if="contiList.length > 0" class="conti-list">
          <div v-for="c in contiList" :key="c.id"
            class="conto-card" :class="{ 'conto-card-inherited': c.fonte === 'soggetto' }">
            <div class="conto-card-content">
              <div class="conto-card-header">
                <Tag v-if="c.fonte" :value="c.fonte === 'soggetto' ? t('common.soggetto') : t('common.ruolo')"
                  :severity="c.fonte === 'soggetto' ? 'secondary' : 'info'" />
                <Tag :value="c.uso" :severity="usoSeverity(c.uso)" />
                <i v-if="c.predefinito" class="pi pi-star-fill conto-star" :title="t('conti_bancari.predefinito')" />
                <Tag v-if="c.bloccato" :value="t('conti_bancari.bloccato')" severity="danger" />
              </div>
              <div class="conto-card-iban">{{ c.iban }}</div>
              <div class="conto-card-detail">
                <span v-if="c.bic_swift"><i class="pi pi-code" /> {{ c.bic_swift }}</span>
                <span v-if="c.filiale_nome"><i class="pi pi-building" /> {{ c.filiale_nome }}</span>
              </div>
            </div>
            <div v-if="!formMode && c.fonte !== 'soggetto'" class="conto-card-actions">
              <Button icon="pi pi-pencil" text rounded size="small"
                class="app-action-btn" :title="t('common.edit')" @click="onStartEdit(c)" />
              <Button icon="pi pi-trash" severity="danger" text rounded size="small"
                :title="t('common.delete')" @click="onDelete(c)" />
            </div>
          </div>
        </div>

        <!-- Pulsante aggiungi -->
        <div v-if="!formMode" class="mt-05">
          <Button
            :label="t('conti_bancari.aggiungi_conto')"
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
          <h4>{{ formMode === 'edit' ? t('conti_bancari.modifica_conto') : t('conti_bancari.nuovo_conto') }}</h4>
        </div>
        <ContoBancarioForm
          :form="conto.form"
          :usi-disponibili="conto.usiDisponibili"
          :errors="formErrors"
          :disabled="false"
          @iban-select="conto.onIbanSelect"
          @iban-clear="conto.onIbanClear"
          @branch-select="conto.onBranchSelect"
        />

        <DrawerFooter
          :loading="loading"
          :disabled="!conto.form.iban?.trim()"
          @save="onSaveForm"
          @cancel="onCancelForm"
        />
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.conti-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.conto-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-sm, 4px);
  padding: 0.5rem 0.75rem;
}

.conto-card-inherited {
  background: var(--p-surface-50);
  opacity: 0.8;
}

.conto-card-content {
  flex: 1;
  min-width: 0;
}

.conto-card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.conto-star {
  color: var(--p-yellow-500);
  font-size: 0.75rem;
}

.conto-card-iban {
  font-size: 0.85rem;
  font-weight: 600;
  font-family: monospace;
  color: var(--p-text-color);
  margin-bottom: 0.15rem;
}

.conto-card-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.conto-card-detail i {
  font-size: 0.75rem;
  margin-right: 0.15rem;
}

.conto-card-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}
</style>
