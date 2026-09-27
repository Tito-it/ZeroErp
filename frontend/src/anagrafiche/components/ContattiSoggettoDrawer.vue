<script setup>
// Scopo: Drawer dedicato per gestione contatti di un soggetto.
// Riutilizzabile da: SoggettoDrawer (edit), futuro ClienteDrawer, FornitoreDrawer.
// Lista contatti esistenti (click per modifica) + aggiungi nuovo.

import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
import { useContattoForm } from '../composables/useContattoForm'
import { useSoggettoRuoloCollection } from '../composables/useSoggettoRuoloCollection'
import {
  listSoggettoContatti, createSoggettoContatto,
  updateSoggettoContatto, deleteSoggettoContatto,
  listRuoloContatti, createRuoloContatto,
  updateRuoloContatto, deleteRuoloContatto
} from '../api/anagrafiche'
import { DRAWER_WIDTH, MANAGE_ICONS, RECAPITO_ICONS, STATUS_ICONS } from '../../core/constants'
import ContattoForm from './ContattoForm.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
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

const emit = defineEmits(['update:visible', 'saved'])

// Backbone master-detail soggetto/ruolo (B4, regola del 2): stato form +
// load con split fonte + handler start/save/delete. La card list e il form
// restano nel template. Contatti: delete diretto (no confirmDelete), sub-lookup
// tipiContatto/unitaOrganizzative caricati allo start.
const {
  list: contattiList,
  listLoading,
  saving,
  formMode,
  formErrors,
  startNew: onStartNew,
  startEdit: onStartEdit,
  saveForm: onSaveForm,
  deleteItem: onDelete,
  modificato: modificatoInline,
  annullaForm,
  chiudiConConferma,
} = useSoggettoRuoloCollection({
  visible: () => props.visible,
  context: () => props.context,
  ownerId: () => props.soggettoId,
  istanzaUtilityId: () => props.istanzaUtilityId,
  apiMap: {
    soggetto: { list: listSoggettoContatti, create: createSoggettoContatto,
                update: updateSoggettoContatto, remove: deleteSoggettoContatto },
    ruolo: { list: listRuoloContatti, create: createRuoloContatto,
             update: updateRuoloContatto, remove: deleteRuoloContatto },
  },
  splitKeys: { propri: 'contatti_ruolo', ereditati: 'contatti_soggetto' },
  flatSort: (a, b) =>
    (a.tipo_contatto_descrizione || '').localeCompare(b.tipo_contatto_descrizione || ''),
  resetForm: () => contatto.reset(),
  validateForm: () => contatto.validate(),
  populateForm: (item) => contatto.populate(item),
  buildCreatePayload: () => ({ ...contatto.form }),
  buildUpdatePayload: () => ({ ...contatto.form }),
  onAfterStartNew: () => {
    contatto.tipiContatto.load()
    contatto.unitaOrganizzative.load()
  },
  onAfterStartEdit: () => {
    contatto.tipiContatto.load()
    contatto.unitaOrganizzative.load()
  },
  messages: {
    created: t('anagrafiche.contatto.contatto_creato'),
    saved: t('anagrafiche.contatto.contatto_salvato'),
    deleted: t('anagrafiche.contatto.contatto_eliminato'),
  },
  onSaved: () => emit('saved'),
  formDaConfrontare: () => ({ ...contatto.form }),
})

// Scopo: chiusura drawer dal pulsante Chiudi del footer (modalita' lista).
const onClose = useDrawerClose(emit)
// Uscite dal drawer: con il form inline modificato si chiede prima.
const chiudi = () => chiudiConConferma(onClose)
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle :modificato="modificatoInline" :action="t('common.edit')" :title="t('anagrafiche.soggetti.section_contatto')" :icon="MANAGE_ICONS.CONTATTI" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <!-- Loading -->
      <div v-if="listLoading" class="app-loading">
        <i :class="STATUS_ICONS.CARICAMENTO" />
      </div>

      <!-- Lista contatti esistenti -->
      <template v-if="!listLoading">
        <div v-if="contattiList.length === 0 && !formMode" class="app-empty-state">
          <i :class="MANAGE_ICONS.CONTATTI" />
          <p>{{ t('anagrafiche.contatto.nessun_contatto') }}</p>
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
                <span v-if="c.email"><i :class="RECAPITO_ICONS.EMAIL" /> {{ c.email }}</span>
                <span v-if="c.telefono"><i :class="RECAPITO_ICONS.TELEFONO" /> {{ c.telefono }}</span>
                <span v-if="c.cellulare"><i :class="RECAPITO_ICONS.CELLULARE" /> {{ c.cellulare }}</span>
                <span v-if="c.pec"><i :class="RECAPITO_ICONS.PEC" /> {{ c.pec }}</span>
              </div>
            </div>
            <div v-if="!formMode && !isReadonly && c.fonte !== 'soggetto'" class="contatto-card-actions">
              <Button :icon="MANAGE_ICONS.EDIT" text rounded size="small"
                class="app-action-btn" :title="t('common.edit')" @click="onStartEdit(c)" />
              <Button :icon="MANAGE_ICONS.DELETE" text rounded size="small"
                class="app-delete-btn" :title="t('common.delete')" @click="onDelete(c)" />
            </div>
          </div>
        </div>

        <!-- Pulsante aggiungi (nascosto in readonly) -->
        <div v-if="!formMode && !isReadonly" class="mt-05">
          <Button
            :label="t('anagrafiche.contatto.aggiungi_contatto')"
            :icon="MANAGE_ICONS.ADD"
            text
            size="small"
            class="app-action-btn"
            @click="onStartNew"
          />
        </div>
      </template>

      <FormFooter v-if="!formMode" close-only @cancel="chiudi" />

      <!-- Form (aggiungi o modifica) -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('anagrafiche.contatto.modifica_contatto') : t('anagrafiche.contatto.nuovo_contatto') }}</h4>
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

        <FormFooter
          :loading="saving"
          :disabled="!contatto.form.nominativo?.trim()"
          @save="onSaveForm"
          @cancel="annullaForm"
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
  border-color: var(--app-fonte-soggetto-color);
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
  color: var(--app-text-muted);
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
