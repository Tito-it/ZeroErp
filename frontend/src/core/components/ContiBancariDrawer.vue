<script setup>
// Scopo: Drawer dedicato per gestione conti bancari di un soggetto (o ruolo).
// Riutilizzabile da: SoggettoDrawer (edit), futuro RuoloDrawer.
// Lista conti esistenti (click per modifica) + aggiungi nuovo.
// Context 'soggetto' o 'ruolo' determina API chiamate.

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useReadonlyMode, useInjectBlocked } from '../composables/useReadonlyMode'
import { useDrawerClose } from '../composables/useDrawerClose'
import { useContoBancarioForm } from '../composables/useContoBancarioForm'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useSoggettoRuoloCollection } from '../composables/useSoggettoRuoloCollection'
import {
  listSoggettoContiBancari, createSoggettoContoBancario,
  updateSoggettoContoBancario, deleteSoggettoContoBancario,
  listRuoloContiBancari, createRuoloContoBancario,
  updateRuoloContoBancario, deleteRuoloContoBancario
} from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH, MANAGE_ICONS, READONLY_DOMAINS, READONLY_MODELS } from '../constants'
import ContoBancarioForm from './ContoBancarioForm.vue'
import DrawerTitle from './DrawerTitle.vue'
import FormFooter from './FormFooter.vue'
import AccessoBloccatoPanel from './AccessoBloccatoPanel.vue'
import PageActionsBar from './PageActionsBar.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
// Drawer autonomo: dichiara scope oggetto per reagire all'override
// `anagrafiche.conto_bancario` indipendentemente dal parent.
// L'OR interno di useReadonlyMode garantisce comunque rispetto dello stato
// readonly ereditato (se parent e' readonly, anche il drawer lo resta).
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE, READONLY_MODELS.CONTO_BANCARIO)
const isBlocked = useInjectBlocked()
const conto = useContoBancarioForm()
const { confirmDelete } = useConfirmAction()

// Context 'soggetto' (default) o 'ruolo': determina quale set di API usare.
// Per 'soggetto': ownerId = soggetto UUID. Per 'ruolo': ownerId = soggetto_ruolo_id (int).
const props = defineProps({
  visible: { type: Boolean, default: false },
  ownerId: { type: [String, Number], default: null },
  ownerName: { type: String, default: '' },
  context: { type: String, default: 'soggetto' },
  istanzaUtilityId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

// Backbone master-detail soggetto/ruolo (B4, regola del 2): stato form +
// load con split fonte + handler start/save/delete. La card list, il form,
// readonly/blocked e la toolbar PageActionsBar restano nel drawer. Conti:
// delete con conferma su IBAN mascherato; nessun side-effect allo start.
const {
  list: contiList,
  listLoading,
  saving,
  formMode,
  formErrors,
  loadList: loadConti,
  startNew: onStartNew,
  startEdit: onStartEdit,
  cancelForm: onCancelForm,
  saveForm: onSaveForm,
  deleteItem: onDelete,
} = useSoggettoRuoloCollection({
  visible: () => props.visible,
  context: () => props.context,
  ownerId: () => props.ownerId,
  istanzaUtilityId: () => props.istanzaUtilityId,
  apiMap: {
    soggetto: { list: listSoggettoContiBancari, create: createSoggettoContoBancario,
                update: updateSoggettoContoBancario, remove: deleteSoggettoContoBancario },
    ruolo: { list: listRuoloContiBancari, create: createRuoloContoBancario,
             update: updateRuoloContoBancario, remove: deleteRuoloContoBancario },
  },
  splitKeys: { propri: 'conti_ruolo', ereditati: 'conti_ereditati' },
  flatSort: (a, b) => (a.uso || '').localeCompare(b.uso || ''),
  resetForm: () => conto.reset(props.ownerName),
  validateForm: () => conto.validate(),
  populateForm: (item) => conto.populate(item),
  buildCreatePayload: () => conto.toCreatePayload(),
  buildUpdatePayload: () => conto.toUpdatePayload(),
  // confirmDelete signature: (itemName, onAccept). Passare un oggetto
  // {message, accept} fa cadere il dialog (onAccept undefined): il pulsante
  // di conferma non triggera la delete (bug latente storico).
  confirmDelete: (item, doDelete) => {
    const itemName = `${item.uso} — ${maskIban(item.iban)}`
    confirmDelete(itemName, doDelete)
  },
  messages: {
    created: t('anagrafiche.conti_bancari.conto_creato'),
    saved: t('anagrafiche.conti_bancari.conto_salvato'),
    deleted: t('anagrafiche.conti_bancari.conto_eliminato'),
  },
  onSaved: () => emit('saved'),
})

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: loadConti,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('anagrafiche.conti_bancari.aggiungi_conto'),
    icon: MANAGE_ICONS.ADD,
    command: onStartNew,
  },
])

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

// Scopo: chiusura drawer dal pulsante Chiudi del footer (modalita' lista).
const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle :action="formMode === 'new' ? t('common.new') : t('common.edit')" :title="t('anagrafiche.conti_bancari.titolo')" :icon="MANAGE_ICONS.CONTI_BANCARI" />
    </template>

    <!-- Livello oggetto BLOCCATO: pannello sostitutivo (safety net se
         l'utente raggiunge il drawer bypassando l'azione di riga). -->
    <AccessoBloccatoPanel v-if="isBlocked" />

    <div v-else class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <!-- Loading -->
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <!-- Toolbar standard sub-drawer: reload + nuovo (allineato a
           ContrattoRigheDrawer / ArticoloBomDrawer). Visibile sempre
           quando non in form mode, anche con lista vuota: il pulsante
           "Nuovo" deve essere immediatamente raggiungibile. -->
      <div v-if="!listLoading && !formMode && !isReadonly" class="app-page-toolbar">
        <div class="app-page-filters" />
        <PageActionsBar :actions="pageActions" />
      </div>

      <!-- Lista conti esistenti -->
      <template v-if="!listLoading">
        <div v-if="contiList.length === 0 && !formMode" class="app-empty-state">
          <i class="pi pi-wallet" />
          <p>{{ t('anagrafiche.conti_bancari.nessun_conto') }}</p>
        </div>

        <div v-else-if="contiList.length > 0" class="conti-list">
          <div v-for="c in contiList" :key="c.id"
            class="conto-card" :class="{ 'conto-card-soggetto': c.fonte === 'soggetto', 'conto-card-ruolo': c.fonte === 'ruolo' || c.fonte === 'istanza' }">
            <div class="conto-card-content">
              <div class="conto-card-header">
                <Tag v-if="c.fonte" :value="c.fonte === 'soggetto' ? t('common.soggetto') : (c.fonte === 'istanza' && c.utility_codice ? c.utility_codice : t('common.ruolo'))"
                  :severity="c.fonte === 'soggetto' ? 'secondary' : 'info'" />
                <Tag :value="c.uso" :severity="usoSeverity(c.uso)" />
                <Tag v-if="c.bloccato" :value="t('anagrafiche.conti_bancari.bloccato')" severity="danger" />
                <Tag v-if="c.verificato && !c.bloccato" :value="t('anagrafiche.conti_bancari.verificato')" severity="info" />
              </div>
              <div class="conto-card-iban">
                <i v-if="c.predefinito" class="pi pi-check-circle conto-predefinito" v-tooltip.top="t('anagrafiche.conti_bancari.predefinito')" />
                {{ c.iban }}
              </div>
              <div class="conto-card-detail">
                <span v-if="c.bic_swift"><i class="pi pi-code" /> {{ c.bic_swift }}</span>
                <span v-if="c.filiale_nome"><i class="pi pi-building" /> {{ c.filiale_nome }}</span>
              </div>
            </div>
            <div v-if="!formMode && !isReadonly && c.fonte !== 'soggetto'" class="conto-card-actions">
              <Button :icon="MANAGE_ICONS.EDIT" text rounded size="small"
                class="app-action-btn" :title="t('common.edit')" @click="onStartEdit(c)" />
              <Button :icon="MANAGE_ICONS.DELETE" text rounded size="small"
                class="app-delete-btn" :title="t('common.delete')" @click="onDelete(c)" />
            </div>
          </div>
        </div>

      </template>

      <FormFooter v-if="!formMode" close-only @cancel="onClose" />

      <!-- Form (aggiungi o modifica) -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('anagrafiche.conti_bancari.modifica_conto') : t('anagrafiche.conti_bancari.nuovo_conto') }}</h4>
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

        <FormFooter
          :loading="saving"
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

.conto-card-soggetto {
  border-color: var(--p-orange-300);
  opacity: 0.5;
}
.conto-card-ruolo {
  border-color: var(--p-blue-300);
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

.conto-predefinito {
  color: var(--p-green-500);
  font-size: 1.1rem;
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
