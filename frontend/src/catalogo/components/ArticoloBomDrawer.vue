<script setup>
// Scopo: Sub-drawer per gestione distinta base (BoM) articolo.
// Layout: lista componenti sempre visibile in alto + form inserimento in basso.
// Pattern immutabilità (sviluppo-listini-v5 §14.4 / DEC-4):
//   - i campi struttura (componente, coeff_qta, esposto_in_fattura, ecc.)
//     non sono modificabili in place: trigger DB E_BOM_MODIFICA_VIETATA li
//     blocca. Per correggere si usa "chiudi riga" + "duplica come nuova
//     versione" (l'admin chiude la riga corrente e ne crea una nuova).
//   - delete BoM bloccato dal trigger: il pattern di "rimozione" è chiusura
//     con valido_al = oggi.
//   - valido_al è l'unico campo struttura editabile inline (chiusura riga).
// Lookup componenti filtrato per is_solo_componente=true.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
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
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const componentiList = ref([])
const listLoading = ref(false)

// Form inserimento nuovo componente
const form = ref({})
const componenteObj = ref(null)
const adding = ref(false)

// Edit inline: traccia quale riga ha il DatePicker valido_al aperto.
// valido_al è l'unico campo modificabile in place (DEC-4): permette
// chiusura immediata della riga senza passare dal kebab.
const editingValidoAlId = ref(null)
const editingValidoAlValue = ref(null)

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
  loadComponenti()
})

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
  // Pre-compila componente_obj per restore AutoComplete (display nome).
  componenteObj.value = {
    id: row.componente_id,
    descrizione: row.componente_descrizione,
    codice_interno: row.componente_codice,
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

// Scopo: chiude una riga BoM impostando valido_al = oggi. Sostituisce il
// vecchio "elimina" che oggi è bloccato dal trigger DB E_BOM_MODIFICA_VIETATA.
// Conferma esplicita: l'admin deve sapere che è chiusura, non eliminazione.
function onChiudiRiga(row) {
  const oggi = new Date()
  const oggiStr = displayDate(oggi)
  confirmAction({
    title: t('catalogo.chiudi_riga_confirm_title'),
    message: t('catalogo.chiudi_riga_confirm_message', { data: oggiStr }),
    onAccept: async () => {
      const result = await execute(
        () => updateArticoloComponente(props.articoloId, row.id, {
          valido_al: toDateString(oggi),
        }),
        { successMessage: t('catalogo.componente_chiuso') }
      )
      if (result !== null) {
        await loadComponenti()
        emit('saved')
      }
    }
  })
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

        <!-- Lista componenti (sempre visibile) -->
        <div v-if="componentiList.length === 0 && !adding" class="app-empty-state">
          <i class="pi pi-sitemap" />
          <p>{{ t('catalogo.nessun_componente') }}</p>
        </div>

        <DataTable v-if="componentiList.length > 0" :value="componentiList" class="app-datatable" striped-rows>
          <Column field="componente_codice" :header="t('catalogo.col_codice')" />
          <Column field="componente_descrizione" :header="t('catalogo.col_descrizione')" />
          <Column field="coeff_qta" :header="t('catalogo.col_coeff_qta')" style="width: 70px;" />
          <Column field="esposto_in_fattura" :header="t('catalogo.col_esposto_fattura')" style="width: 80px;">
            <template #body="{ data }">
              <i :class="data.esposto_in_fattura ? 'pi pi-check text-green-500' : 'pi pi-minus text-color-secondary'" />
            </template>
          </Column>
          <Column :header="t('catalogo.field_valido_al')" style="width: 120px;">
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

        <!-- Form inserimento nuovo componente -->
        <template v-if="!isReadonly">
          <div v-if="!adding" class="mt-05">
            <Button
              :label="t('catalogo.aggiungi_componente')"
              icon="pi pi-plus"
              text size="small"
              class="app-action-btn"
              @click="startAdd"
            />
          </div>

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
