<script setup>
// Scopo: Drawer crea/modifica articolo.
//        Include combo conti contabili vendita/acquisto e auto-propose IVA da parameters.
//        In edit: riepilogo UoM/BoM/Note con pulsante "Gestisci" che apre sub-drawer dedicato.
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { listArticoloUom, listArticoloComponenti, listArticoloNote } from '../api/catalogo'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import IvaSelect from '../../core/components/IvaSelect.vue'
import ContoContabileSelect from '../../core/components/ContoContabileSelect.vue'
import ArticoloUomDrawer from './ArticoloUomDrawer.vue'
import ArticoloBomDrawer from './ArticoloBomDrawer.vue'
import ArticoloNoteDrawer from './ArticoloNoteDrawer.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = useArticoliStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults(['DEFAULT_IVA_ID'])
// Pre-fetch al setup: quando il drawer si apre il valore e' gia' in cache
loadDefaults()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer
const contentReady = ref(false)

function onAfterShow() {
  contentReady.value = true
}

// Sub-drawer e riepilogo (edit mode)
const uomDrawerVisible = ref(false)
const uomRiepilogo = ref([])
const bomDrawerVisible = ref(false)
const bomRiepilogo = ref([])
const noteDrawerVisible = ref(false)
const noteRiepilogo = ref([])

function defaultForm() {
  return {
    codice: '', descrizione: '', descrizione_breve: '',
    uom_id: null, tipo_voce_id: null, gruppo_voce_id: null,
    spesa_id: null, iva_id: null,
    conto_contabile_vendita_id: null, conto_contabile_acquisto_id: null,
    is_composito: false, is_solo_componente: false,
    requires_serial: false, voce_utility: false,
    attivo: true
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  uomRiepilogo.value = []
  bomRiepilogo.value = []
  noteRiepilogo.value = []
}

// Scopo: Carica riepilogo UoM operative.
async function loadUomRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await listArticoloUom(props.articoloId)
    const payload = res.data?.data
    uomRiepilogo.value = payload?.results || payload || []
  } catch { uomRiepilogo.value = [] }
}

// Scopo: Carica riepilogo componenti BoM.
async function loadBomRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await listArticoloComponenti(props.articoloId)
    const payload = res.data?.data
    bomRiepilogo.value = payload?.results || payload || []
  } catch { bomRiepilogo.value = [] }
}

// Scopo: Carica riepilogo note.
async function loadNoteRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await listArticoloNote(props.articoloId)
    const payload = res.data?.data
    noteRiepilogo.value = payload?.results || payload || []
  } catch { noteRiepilogo.value = [] }
}

async function loadDetail() {
  if (!props.articoloId) return
  const data = await store.fetchDetail(props.articoloId)
  if (!data) return
  detail.value = data
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    descrizione_breve: data.descrizione_breve || '',
    uom_id: data.uom_id,
    tipo_voce_id: data.tipo_voce_id,
    gruppo_voce_id: data.gruppo_voce_id,
    spesa_id: data.spesa_id,
    iva_id: data.iva_id,
    conto_contabile_vendita_id: data.conto_contabile_vendita_id,
    conto_contabile_acquisto_id: data.conto_contabile_acquisto_id,
    is_composito: data.is_composito || false,
    is_solo_componente: data.is_solo_componente || false,
    requires_serial: data.requires_serial || false,
    voce_utility: data.voce_utility || false,
    attivo: data.attivo ?? true
  }
  // Carica riepilogo in parallelo
  await Promise.all([loadUomRiepilogo(), loadBomRiepilogo(), loadNoteRiepilogo()])
}

watch(() => props.visible, (v) => {
  if (!v) {
    contentReady.value = false
    return
  }
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
    if (paramDefaults.value.DEFAULT_IVA_ID) {
      form.value.iva_id = Number(paramDefaults.value.DEFAULT_IVA_ID)
    }
  }
})

const canSave = computed(() => {
  return form.value.codice?.trim() && form.value.descrizione?.trim() && form.value.uom_id != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    // uom_id e' immutabile dopo create (lock_columns DDL): non inviarlo mai in PATCH.
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      descrizione_breve: f.descrizione_breve?.trim() || null,
      tipo_voce_id: f.tipo_voce_id,
      gruppo_voce_id: f.gruppo_voce_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
      voce_utility: f.voce_utility,
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.update(props.articoloId, payload),
      { successMessage: t('catalogo.articolo_salvato') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      codice: f.codice?.trim(),
      descrizione: f.descrizione?.trim(),
      descrizione_breve: f.descrizione_breve?.trim() || null,
      uom_id: f.uom_id,
      tipo_voce_id: f.tipo_voce_id,
      gruppo_voce_id: f.gruppo_voce_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
      voce_utility: f.voce_utility,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('catalogo.articolo_creato') }
    )
    if (result !== null) { emit('saved', result); close() }
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }" :dismissable="true"
    @after-show="onAfterShow">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('catalogo.articolo')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_codice') }} *</label>
            <InputText v-model="form.codice" :disabled="isEdit" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_uom') }} *</label>
            <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" :disabled="isEdit" />
          </div>
        </div>

        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_descrizione') }} *</label>
            <InputText v-model="form.descrizione" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_descrizione_breve') }}</label>
            <InputText v-model="form.descrizione_breve" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_tipologia') }}</label>
            <LookupSelect v-model="form.tipo_voce_id" rel="vendite.articoli_tipologie" :placeholder="t('catalogo.select_tipologia')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_gruppo') }}</label>
            <LookupSelect v-model="form.gruppo_voce_id" rel="vendite.articoli_gruppi" :placeholder="t('catalogo.select_gruppo')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_spesa') }}</label>
            <LookupSelect v-model="form.spesa_id" rel="vendite.articoli_spesa" :placeholder="t('catalogo.select_spesa')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_iva') }}</label>
            <IvaSelect v-model="form.iva_id" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_conto_vendita') }}</label>
            <ContoContabileSelect v-model="form.conto_contabile_vendita_id" tipo="V" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_conto_acquisto') }}</label>
            <ContoContabileSelect v-model="form.conto_contabile_acquisto_id" tipo="A" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_composito') }}</label>
            <ToggleSwitch v-model="form.is_composito" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_solo_componente') }}</label>
            <ToggleSwitch v-model="form.is_solo_componente" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_voce_utility') }}</label>
            <ToggleSwitch v-model="form.voce_utility" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_requires_serial') }}</label>
            <ToggleSwitch v-model="form.requires_serial" />
          </div>
          <div v-if="isEdit" class="form-field">
            <label>{{ t('indirizzi.campo_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" />
          </div>
        </div>

        <!-- Sezione: UoM riepilogo (edit mode) -->
        <template v-if="isEdit && detail">
          <div class="app-drawer-section"><h4>{{ t('catalogo.tab_uom') }}</h4></div>
          <div class="riepilogo-section">
            <div v-if="uomRiepilogo.length > 0" class="riepilogo-list">
              <div v-for="u in uomRiepilogo" :key="u.id" class="riepilogo-item">
                <Tag v-if="u.is_base" :value="t('catalogo.tag_base')" severity="info" />
                <strong>{{ u.uom_codice }}</strong>
                <span class="riepilogo-detail">{{ u.uom_descrizione }}</span>
                <span v-if="u.factor_to_base != null && u.factor_to_base !== 1" class="riepilogo-detail">
                  ({{ t('catalogo.col_fattore') }}: {{ u.factor_to_base }})
                </span>
              </div>
            </div>
            <div v-else class="riepilogo-empty">{{ t('catalogo.nessuna_uom') }}</div>
            <Button v-if="!isReadonly"
              :label="t('catalogo.gestisci_uom')" icon="pi pi-box"
              text size="small" class="app-action-btn app-escape mt-025"
              @click="uomDrawerVisible = true" />
          </div>
        </template>

        <!-- Sezione: BoM riepilogo (edit mode, solo se composito) -->
        <template v-if="isEdit && detail && form.is_composito">
          <div class="app-drawer-section"><h4>{{ t('catalogo.tab_bom') }}</h4></div>
          <div class="riepilogo-section">
            <div v-if="bomRiepilogo.length > 0" class="riepilogo-list">
              <div v-for="c in bomRiepilogo" :key="c.id" class="riepilogo-item">
                <strong>{{ c.componente_codice }}</strong>
                <span class="riepilogo-detail">{{ c.componente_descrizione }}</span>
                <span class="riepilogo-detail">(x{{ c.coeff_qta }})</span>
              </div>
            </div>
            <div v-else class="riepilogo-empty">{{ t('catalogo.nessun_componente') }}</div>
            <Button v-if="!isReadonly"
              :label="t('catalogo.gestisci_bom')" icon="pi pi-sitemap"
              text size="small" class="app-action-btn app-escape mt-025"
              @click="bomDrawerVisible = true" />
          </div>
        </template>

        <!-- Sezione: Note riepilogo (edit mode) -->
        <template v-if="isEdit && detail">
          <div class="app-drawer-section"><h4>{{ t('catalogo.tab_note') }}</h4></div>
          <div class="riepilogo-section">
            <div v-if="noteRiepilogo.length > 0" class="riepilogo-list">
              <div v-for="n in noteRiepilogo" :key="n.nota_id" class="riepilogo-item">
                <span class="riepilogo-detail">{{ (n.nota_testo || '').substring(0, 80) }}{{ (n.nota_testo || '').length > 80 ? '...' : '' }}</span>
              </div>
            </div>
            <div v-else class="riepilogo-empty">{{ t('catalogo.nessuna_nota') }}</div>
            <Button v-if="!isReadonly"
              :label="t('catalogo.gestisci_note')" icon="pi pi-file-edit"
              text size="small" class="app-action-btn app-escape mt-025"
              @click="noteDrawerVisible = true" />
          </div>
        </template>
      </template>

      <div v-else class="app-loading">
        <i class="pi pi-spin pi-spinner" style="font-size: 1.5rem;"></i>
      </div>

      <DrawerFooter v-if="contentReady" :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>

  <!-- Sub-drawer UoM operative -->
  <ArticoloUomDrawer
    :visible="uomDrawerVisible"
    @update:visible="v => uomDrawerVisible = v"
    :articolo-id="props.articoloId"
    @saved="loadUomRiepilogo"
  />
  <!-- Sub-drawer Distinta Base -->
  <ArticoloBomDrawer
    :visible="bomDrawerVisible"
    @update:visible="v => bomDrawerVisible = v"
    :articolo-id="props.articoloId"
    @saved="loadBomRiepilogo"
  />
  <!-- Sub-drawer Note -->
  <ArticoloNoteDrawer
    :visible="noteDrawerVisible"
    @update:visible="v => noteDrawerVisible = v"
    :articolo-id="props.articoloId"
    @saved="loadNoteRiepilogo"
  />
</template>

<style scoped>
.riepilogo-section {
  margin-top: 0.5rem;
}
.riepilogo-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.riepilogo-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.riepilogo-detail {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}
.riepilogo-empty {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
</style>
