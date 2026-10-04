<script setup>
// Scopo: Sub-drawer per gestione conversioni UoM di una specifica unita' di misura.
// Layout: lista conversioni sempre visibile in alto con fattore editabile inline,
// form inserimento nuova conversione in basso (solo "A" selezionabile, "Da" e' la UoM corrente).
//
// ⭐ PORTATO SULLO STANDARD IL 2026-09-26 (piano PrimeVue 5, Gruppo A): la
//    lista e' `catalogo.conversioni_uom` filtrata sulla UoM — lo stesso
//    catalogo e lo stesso endpoint paginato della schermata Conversioni —
//    con `useDrawerTabLista` + `<DrawerTabLista>` e uno store suo
//    (`uomConversioni`). Prima era una `DataTable` grezza su `limit: 200`
//    senza paginator. Il fattore resta modificabile sulla riga: e' lo slot
//    `cell-fattore`.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve, unisciFotografie } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useLookupCodici } from '../../core/composables/useLookupCodici'
import { createConversioneUom, updateConversioneUom } from '../api/catalogo'
import { useUomConversioniStore } from '../stores/uomConversioni'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const ALWAYS_VALID_FROM = '1900-01-01'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()
const uomLookup = useLookupCodici('catalogo.unita_misura', { immediate: true })

const props = defineProps({
  visible: { type: Boolean, default: false },
  uomId: { type: [Number, null], default: null },
  uomCodice: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'saved'])

const store = useUomConversioniStore()
const adding = ref(false)

function defaultForm() {
  return {
    uom_to_id: null,
    fattore: 1,
    valido_dal: parseIsoDate(ALWAYS_VALID_FROM),
    valido_dal_sempre: true
  }
}

const form = ref(defaultForm())
const currentTipoUomId = computed(() => {
  const selected = uomLookup.items.value.find(item => item.id === props.uomId)
  return selected?.tipo_uom_id ?? null
})

// Edit inline fattore
const editingFattoreId = ref(null)
const editingFattoreValue = ref(null)

// Modifiche non salvate: due form indipendenti, ognuno con la sua fotografia —
// il form «nuova conversione» (vive finche' `adding`) e il fattore in modifica
// sulla riga (vive finche' c'e' `editingFattoreId`). Il fattore e' un numero:
// il BB confronta oggetti, quindi lo si avvolge.
const inline = useDrawerFormPreserve(form, { visibile: () => props.visible && adding.value })
const fattoreInline = useDrawerFormPreserve(
  computed(() => ({ fattore: editingFattoreValue.value })),
  { visibile: () => props.visible && editingFattoreId.value !== null },
)
// Una domanda sola per le due fotografie (chiusura del drawer).
const { modificato: modificatoTutto, chiudiConConferma: chiudiTutto } =
  unisciFotografie(inline, fattoreInline)

// ⚠️ `parentId` porta l'id SOLO a drawer aperto: il `null` alla chiusura
//    chiama `store.reset()`, o le conversioni della UoM precedente
//    lampeggerebbero sotto la prossima.
// ⚠️ Il «Nuovo» entra da `extraActions`: e' spento mentre il form e' aperto,
//    una condizione che `onNew` non sa dire.
const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.uomId : null),
  parentField: 'uomId',
  // Nessun `searchTableOptions`: l'ordinamento di partenza lo dichiara lo
  // store, e una seconda copia qui divergerebbe in silenzio (vince lo store).
  extraActions: () => [{
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('catalogo.nuova_conversione_uom'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    disabled: adding.value,
    command: startAdd,
  }],
})

watch(() => props.visible, (val) => {
  if (!val) return
  adding.value = false
  form.value = defaultForm()
  editingFattoreId.value = null
})

watch(currentTipoUomId, (tipoId) => {
  if (tipoId == null || form.value.uom_to_id == null) return
  const selectedTo = uomLookup.items.value.find(item => item.id === form.value.uom_to_id)
  if (selectedTo && selectedTo.tipo_uom_id !== tipoId) {
    form.value.uom_to_id = null
  }
})

function todayLocalDate() {
  return parseIsoDate(toDateString(new Date()))
}

watch(() => form.value.valido_dal_sempre, (sempre) => {
  form.value.valido_dal = sempre ? parseIsoDate(ALWAYS_VALID_FROM) : todayLocalDate()
})

// --- Inserimento nuova conversione ---

function startAdd() {
  form.value = defaultForm()
  adding.value = true
  inline.fissa()
}

function cancelAdd() {
  adding.value = false
  form.value = defaultForm()
}

// Annulla del form «nuova conversione»: con modifiche chiede conferma.
const annullaAdd = () => inline.chiudiConConferma(cancelAdd)

const canSaveNew = computed(() => {
  return form.value.uom_to_id != null && form.value.fattore > 0
})

// Scopo: Crea nuova conversione. Da = UoM corrente, A = selezionata.
async function onSaveNew() {
  const result = await execute(
    () => createConversioneUom({
      uom_from_id: props.uomId,
      uom_to_id: form.value.uom_to_id,
      fattore: form.value.fattore,
      valido_dal: form.value.valido_dal_sempre
        ? ALWAYS_VALID_FROM
        : toDateString(form.value.valido_dal),
    }),
    { successMessage: t('catalogo.conversione_creata') }
  )
  if (result === null) return
  adding.value = false
  form.value = defaultForm()
  reloadAll()
  emit('saved')
}

// --- Edit inline fattore ---

// ⚠️ Passare a un'altra riga butta il fattore scritto sulla precedente: con
//    modifiche si chiede prima.
function startEditFattore(row) {
  fattoreInline.chiudiConConferma(() => {
    editingFattoreId.value = row.id
    editingFattoreValue.value = row.fattore
    fattoreInline.fissa()
  })
}

async function confirmEditFattore(row) {
  const result = await execute(
    () => updateConversioneUom(row.id, { fattore: editingFattoreValue.value }),
    { successMessage: t('catalogo.conversione_salvata') }
  )
  if (result === null) return
  editingFattoreId.value = null
  editingFattoreValue.value = null
  reloadAll()
  emit('saved')
}

function cancelEditFattore() {
  editingFattoreId.value = null
  editingFattoreValue.value = null
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="uomCodice"
    :icon="NAV_ICONS.UNITA_MISURA"
    :action="t('catalogo.gestisci_conversioni')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificatoTutto"
    :conferma-uscita="chiudiTutto"
    :footer="adding ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- Lista conversioni: catalogo `catalogo.conversioni_uom`, filtrata
         sulla UoM. Il fattore si modifica sulla riga (slot `cell-fattore`). -->
    <DrawerTabLista
      ref="listaRef"
      codice="catalogo.conversioni_uom"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <!-- La frase del dominio al posto dell'empty-state generico, e solo se
           la lettura e' riuscita: con `erroreCaricamento` la lista e' vuota
           per un'altra ragione. -->
      <template #empty>
        <span v-if="!store.erroreCaricamento">{{ t('catalogo.nessuna_conversione') }}</span>
      </template>
      <template #cell-fattore="{ data }">
        <template v-if="editingFattoreId === data.id">
          <div>
            <InputNumber v-model="editingFattoreValue" :min="0" :min-fraction-digits="2"
              :max-fraction-digits="10" style="width: 100px;" />
            <Button :icon="MANAGE_ICONS.CONFIRM" text rounded size="small" class="app-action-btn"
              @click="confirmEditFattore(data)" />
            <Button :icon="MANAGE_ICONS.CANCEL" text rounded size="small"
              @click="fattoreInline.chiudiConConferma(cancelEditFattore)" />
          </div>
        </template>
        <template v-else>
          <span v-if="!isReadonly" class="app-mono fattore-cell" @click="startEditFattore(data)">
            {{ data.fattore }}
            <i :class="MANAGE_ICONS.EDIT" style="font-size: 0.7rem; margin-left: 0.25rem; opacity: 0.5;" />
          </span>
          <span v-else class="app-mono">{{ data.fattore }}</span>
        </template>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </DrawerTabLista>

    <!-- Form inserimento nuova conversione (pulsante "Nuovo" e' nella
         toolbar sopra la lista, non piu' inline qui). -->
    <template v-if="!isReadonly">
      <template v-if="adding">
        <div class="app-drawer-section">
          <h4>{{ t('catalogo.nuova_conversione_uom') }}</h4>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_uom_a') }} *</label>
            <LookupSelect v-model="form.uom_to_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom_a')" filter-field="tipo_uom_id"
              :filter-value="currentTipoUomId" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.col_fattore') }} *</label>
            <InputNumber v-model="form.fattore" :min="0" :min-fraction-digits="2"
              :max-fraction-digits="10" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_valido_dal') }}</label>
            <DatePicker
              v-model="form.valido_dal"
              :date-format="DATE_FORMAT"
              show-icon
              show-button-bar
              :disabled="form.valido_dal_sempre"
              :invalid="campiErrati.includes('valido_dal')"
            />
          </div>
        </div>
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.validita_sempre') }}</label>
            <ToggleSwitch v-model="form.valido_dal_sempre" />
          </div>
        </div>
      </template>
    </template>

    <!-- Footer standard: in modalita' adding mostra Annulla/Salva del form,
         altrimenti close-only per chiudere il drawer (pattern speculare
         ArticoloUomDrawer). -->
    <FormFooter
      v-if="adding"
      :loading="loading"
      :disabled="!canSaveNew"
      @save="onSaveNew"
      @cancel="annullaAdd"
    />
  </AppDrawer>
</template>

<style scoped>
.fattore-cell {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.fattore-cell:hover {
  color: var(--app-accent-color);
}
</style>
