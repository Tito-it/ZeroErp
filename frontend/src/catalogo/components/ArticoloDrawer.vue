<script setup>
// Scopo: Drawer crea/modifica articolo.
//        Include combo conti contabili vendita/acquisto e auto-propose IVA da parameters.
//        In edit: riepilogo UoM/BoM/Note con pulsante "Gestisci" che apre sub-drawer dedicato.
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { listArticoloUom, listArticoloComponenti, makeArticoloNotesApi, getArticoloFormDefaults } from '../api/catalogo'
import { DRAWER_WIDTH } from '../../core/constants'
import { toDateString } from '../../core/utils/date'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
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
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

// Fase 5: lista campi immutabili dopo create. Arriva dal detail come metadata
// (`detail.non_editable_fields`, fonte = `dbops.vw_non_editable_fields` + gap
// Python su catalogo.articoli). Pilota i `:disabled` invece di cablare
// `isEdit` su singoli campi.
const nonEditableFields = computed(() => detail.value?.non_editable_fields || [])
function isFieldLocked(name) {
  return isEdit.value && nonEditableFields.value.includes(name)
}

// Articolo con almeno un componente BoM attivo: i flag struttura
// (is_composito, is_solo_componente, requires_serial) diventano immutabili.
// Modificarli causerebbe incoerenze col modello distinta base esistente:
//  - togliere `is_composito` con componenti vivi -> orfani
//  - togliere `is_solo_componente` -> permette di venderlo standalone, ma
//    la BoM corrente lo categorizza come pezzo
//  - togliere `requires_serial` -> incoerenza con eventuali requisiti di
//    tracciabilita' della BoM
// Il BE oggi non ritorna questi campi nel `non_editable_fields` (lock
// condizionale non gestito da `dbops.vw_non_editable_fields`): guard FE
// difensivo + segnalato come gap.
const hasBomAttiva = computed(() => bomRiepilogo.value.length > 0)
function isFlagStrutturaLocked() {
  return isEdit.value && hasBomAttiva.value
}

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer
// (pattern feedback_content_ready_after_show centralizzato in useDrawerContentReady).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

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
    listino_tipologia_id: null,
    spesa_id: null, iva_id: null,
    conto_contabile_vendita_id: null, conto_contabile_acquisto_id: null,
    is_composito: false, is_solo_componente: false,
    requires_serial: false,
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
    const righe = payload?.results || payload || []
    const oggi = toDateString(new Date())
    // Scopo: il riepilogo nel drawer articolo mostra le stesse righe
    // inizialmente visibili nel sub-drawer BoM: righe senza valido_al
    // oppure con valido_al maggiore/uguale a oggi.
    bomRiepilogo.value = righe
      .filter(r => !r.valido_al || r.valido_al >= oggi)
      .sort((a, b) => (a.componente_codice || '').localeCompare(b.componente_codice || ''))
  } catch { bomRiepilogo.value = [] }
}

// Scopo: Carica riepilogo note (preview prime 80 char in panel sezione).
//        Usa il BB partizionato `makeArticoloNotesApi` per coerenza col drawer
//        figlio `ArticoloNoteDrawer`. Refactor 2026-05-21 (Fase 2.B).
async function loadNoteRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await makeArticoloNotesApi(props.articoloId).listNote()
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
    listino_tipologia_id: data.listino_tipologia_id,
    spesa_id: data.spesa_id,
    iva_id: data.iva_id,
    conto_contabile_vendita_id: data.conto_contabile_vendita_id,
    conto_contabile_acquisto_id: data.conto_contabile_acquisto_id,
    is_composito: data.is_composito || false,
    is_solo_componente: data.is_solo_componente || false,
    requires_serial: data.requires_serial || false,
  }
  // Carica riepilogo in parallelo
  await Promise.all([loadUomRiepilogo(), loadBomRiepilogo(), loadNoteRiepilogo()])
}

// Fase 8 (A5): defaults form articolo via endpoint dedicato
// /catalogo/articoli/form-defaults/. Tipi gia' castati lato BE.
async function applyFormDefaults() {
  try {
    const res = await getArticoloFormDefaults()
    const defaults = res.data?.data || {}
    if (defaults.default_iva_id != null) {
      form.value.iva_id = defaults.default_iva_id
    }
  } catch (err) {
    // Best-effort: in caso di errore l'utente compila manualmente.
    // Il warning console aiuta il debug senza disturbare l'utente.
    console.warn('[ArticoloDrawer] form-defaults non disponibili', err)
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return  // contentReady reset gestito da useDrawerContentReady
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
    await applyFormDefaults()
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
      listino_tipologia_id: f.listino_tipologia_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
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
      listino_tipologia_id: f.listino_tipologia_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
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

// Fase 7: disattivazione/riattivazione come azione di dominio.
// L'`attivo` non passa piu' da PATCH: pulsanti dedicati con conferma
// e refresh detail al ritorno dall'API.
async function refreshAfterStateChange(result) {
  if (result === null) return
  detail.value = result
  emit('saved', result)
}

function onConfirmDisattiva() {
  if (!detail.value) return
  confirmAction({
    title: t('catalogo.disattiva_dialog_titolo'),
    message: t('catalogo.disattiva_dialog_messaggio', { codice: detail.value.codice }),
    acceptLabel: t('catalogo.disattiva_articolo'),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => store.disattiva(props.articoloId),
        { successMessage: t('catalogo.articolo_disattivato') }
      )
      await refreshAfterStateChange(result)
    }
  })
}

function onConfirmRiattiva() {
  if (!detail.value) return
  confirmAction({
    title: t('catalogo.riattiva_dialog_titolo'),
    message: t('catalogo.riattiva_dialog_messaggio', { codice: detail.value.codice }),
    acceptLabel: t('catalogo.riattiva_articolo'),
    onAccept: async () => {
      const result = await execute(
        () => store.riattiva(props.articoloId),
        { successMessage: t('catalogo.articolo_riattivato') }
      )
      await refreshAfterStateChange(result)
    }
  })
}

// Azioni della testata articolo consumate da DrawerActionsBar (refactor
// UI drawer 2026-05-21, Fase 2.A). Solo state actions: Disattiva/Riattiva
// in alternativa esclusiva tramite `visible`. UoM/BoM/Note restano panel
// inline (pattern misto: state in alto + sub-entita' eterogenee panel).
// `hideWhenReadonly` rispetta il pattern degli altri drawer: in modalita'
// LETTURA le azioni di stato si nascondono.
const drawerActions = computed(() => {
  if (!isEdit.value || !detail.value) return []
  return [
    {
      key: 'disattiva',
      kind: 'state',
      label: t('catalogo.disattiva_articolo'),
      icon: 'pi pi-ban',
      severity: 'danger',
      outlined: true,
      visible: detail.value.attivo === true,
      hideWhenReadonly: true,
      command: onConfirmDisattiva,
    },
    {
      key: 'riattiva',
      kind: 'state',
      label: t('catalogo.riattiva_articolo'),
      icon: 'pi pi-check',
      severity: 'success',
      visible: detail.value.attivo === false,
      hideWhenReadonly: true,
      command: onConfirmRiattiva,
    },
  ]
})
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

        <!-- Refactor UI drawer 2026-05-21 (Fase 2.A): header info + barra
             azioni state in alto, simmetrici a contratti/preventivi.
             Tag stato a destra, Disattiva/Riattiva nel BB azioni; UoM/BoM/Note
             restano panel inline piu' sotto (pattern misto). -->
        <template v-if="isEdit && detail">
          <DrawerEntityHeader>
            <Tag :value="detail.codice" severity="secondary" />
            <template #status>
              <Tag
                :value="detail.attivo ? t('common.active') : t('common.inactive')"
                :severity="detail.attivo ? 'success' : 'warn'"
              />
            </template>
          </DrawerEntityHeader>

          <DrawerActionsBar :actions="drawerActions" />
        </template>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_codice') }} *</label>
            <InputText v-model="form.codice" :disabled="isFieldLocked('codice')" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_uom') }} *</label>
            <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" :disabled="isFieldLocked('uom_id')" />
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
          <div class="form-field">
            <label>{{ t('catalogo.field_iva') }}</label>
            <IvaSelect v-model="form.iva_id" />
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
            <label>{{ t('catalogo.field_listino_tipologia') }}</label>
            <LookupSelect v-model="form.listino_tipologia_id" rel="config.listini_tipologie" :placeholder="t('catalogo.select_listino_tipologia')" show-clear />
            <small class="text-color-secondary mt-025">{{ t('catalogo.hint_listino_tipologia') }}</small>
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_spesa') }}</label>
            <LookupSelect v-model="form.spesa_id" rel="vendite.articoli_spesa" :placeholder="t('catalogo.select_spesa')" show-clear />
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

        <div class="form-grid-3col">
          <div class="form-field">
            <label>{{ t('catalogo.field_composito') }}</label>
            <ToggleSwitch v-model="form.is_composito"
              :disabled="isFieldLocked('is_composito') || isFlagStrutturaLocked()" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_solo_componente') }}</label>
            <ToggleSwitch v-model="form.is_solo_componente"
              :disabled="isFieldLocked('is_solo_componente') || isFlagStrutturaLocked()" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_requires_serial') }}</label>
            <ToggleSwitch v-model="form.requires_serial"
              :disabled="isFieldLocked('requires_serial') || isFlagStrutturaLocked()" />
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
              <div v-for="n in noteRiepilogo" :key="n.id" class="riepilogo-item">
                <span class="riepilogo-detail">{{ ((n.testo_md || n.testo) || '').substring(0, 80) }}{{ ((n.testo_md || n.testo) || '').length > 80 ? '...' : '' }}</span>
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
