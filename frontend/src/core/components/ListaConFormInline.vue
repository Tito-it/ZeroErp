<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la shell «lista configurabile + form della voce sotto», cieca sul
//        dominio (2026-10-31, regola del 2, ok Tid — brief-db-liste-datatable-
//        grezze-secondo-giro righe 3 e 4). Possiede la lista a catalogo
//        (`useDrawerTabLista` + `<DrawerTabLista>`), la ricerca, «Nuovo» fra le
//        azioni della lista, il clic che apre la voce, la macchina del form
//        (`useFormInline`) e la sua fotografia. Il form e le celle speciali
//        sono del chiamante (slot).
//        ⭐ Nata alla 2ª e 3ª copia della stessa forma: le note (`NoteDrawer`,
//        liste `vendite.note` e `catalogo.note`) e le UoM di un articolo
//        (`ArticoloUomDrawer`, `catalogo.articolo_uom`). La prima copia e'
//        `RigheMasterDetailTable`, che resta sua: e' legata alle righe di un
//        documento di vendita (componenti BoM, export obbligatorio, testata).
//
// ⭐ IL PADRE. `parentId` e' l'id nel PATH (puo' essere un uuid o un percorso:
//    lo store sa che farne). Con `emittenteFiscaleId` dichiarato
//    (`conEmittente`) il padre e' COMPOSTO: l'emittente scioglie il cancello
//    di perimetro, e finche' non arriva la lista aspetta (`useListaStoreCore`).
//    ⚠️ Lo store lo chiama `padreId`: `createListaStore(id, { fetchPage,
//    parentField: 'padreId' })`, con `emittenteParam` se il padre e' composto.
//
// Slot:
//   #form="{ riga, mode, onSaved, onCancel, registra }" → il form della voce
//     (`registra` va su `:ref` del form: la sua fotografia, D-13; `riga` e'
//     null in creazione)
//   #filtri                         → filtri oltre la ricerca (inoltrato)
//   #cell-<codice>="{ data, value }"→ celle (inoltrate alla lista)
//   ⚠️ `#actions` e `#filtri-sempre` sono del BB: le azioni di riga arrivano da
//      `rowActions(riga)`, la ricerca la mette lui.
//
// Eventi: `changed` (dopo un salvataggio o un'azione che lo chiede col
// `cambiata()` esposto), `form-aperto` (il drawer nasconde il suo footer).
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import { useDrawerTabLista } from '../composables/useDrawerTabLista'
import { useFormInline } from '../composables/useFormInline'
import { unisciFotografie } from '../composables/useDrawerFormPreserve'
import DrawerTabLista from './DrawerTabLista.vue'
import RowActionsMenu from './RowActionsMenu.vue'

const { t } = useI18n()

const SLOT_PROPRI = ['form', 'actions', 'filtri-sempre']

const props = defineProps({
  // La lista a catalogo (`catalogo.articolo_uom`).
  codice: { type: String, required: true },
  // Lo store-lista della voce, con `parentField` (uno per istanza o per sede).
  store: { type: Object, required: true },
  // L'id del padre nel path. `null` = nessun padre (la lista si azzera).
  parentId: { type: [Number, String], default: null },
  // Il padre e' composto (lista col perimetro dell'emittente).
  conEmittente: { type: Boolean, default: false },
  // L'emittente del padre (PK): lasciapassare del cancello di perimetro.
  emittenteFiscaleId: { type: Number, default: null },
  // Le voci si scrivono: governa «Nuovo» e il clic che apre la modifica.
  isModificabile: { type: Boolean, default: true },
  newTooltipKey: { type: String, required: true },
  newLabelKey: { type: String, required: true },
  editLabelKey: { type: String, required: true },
  dataKey: { type: String, default: 'id' },
  // (riga) => actions[]: le azioni di riga del dominio (kebab).
  rowActions: { type: Function, default: () => [] },
})
const emit = defineEmits(['changed', 'form-aperto'])

// La fotografia del form della voce: il form si registra con `:ref`.
const formVoce = ref(null)
function registraForm(el) {
  formVoce.value = el
}
const fotografia = unisciFotografie(() => formVoce.value)

const {
  formMode, rigaInModifica, formAperto,
  apriRiga, chiudiForm, ancoraForm, azioneNuovaRiga,
} = useFormInline({
  padre: () => props.parentId,
  puoModificare: () => props.isModificabile,
  confermaCambio: (procedi) => fotografia.chiudiConConferma(procedi),
})
watch(formAperto, (aperto) => emit('form-aperto', aperto))
// ⚠️ Smontata a form aperto il watch non scatta piu': il drawer resterebbe
//    col suo footer nascosto alla riapertura.
onBeforeUnmount(() => {
  if (formAperto.value) emit('form-aperto', false)
})

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato, reloadAll,
} = useDrawerTabLista(props.store, {
  parentId: props.conEmittente
    ? { padreId: () => props.parentId, emittenteId: () => props.emittenteFiscaleId }
    : () => props.parentId,
  parentField: 'padreId',
  // «Nuovo» fra le azioni della lista: sparisce a form aperto (BB).
  extraActions: () => [
    azioneNuovaRiga({
      key: 'new',
      label: t('common.new'),
      tooltip: t(props.newTooltipKey),
      visible: () => props.isModificabile,
    }),
  ],
})

// Scopo: la voce e' stata scritta: si chiude il form, si rilegge la lista e lo
//        si dice al drawer.
function onSaved() {
  chiudiForm()
  cambiata()
}

// Scopo: la lista e' cambiata da un'azione del chiamante (elimina, attiva):
//        si rilegge e lo si dice. ⚠️ `reloadAll()` non e' awaitable.
function cambiata() {
  reloadAll()
  emit('changed')
}

// ⚠️ Conta le azioni VISIBILI: in sola lettura i chiamanti le spengono con
//    `visible: false`, e la colonna resterebbe con un kebab vuoto.
const haColonnaAzioni = computed(
  () => (props.store.items || []).some(
    (r) => props.rowActions(r).some((a) => a.visible !== false),
  ),
)

// ⛔ Una funzione e non una `computed`: l'oggetto degli slot non e' reattivo.
function slotInoltrati(slots) {
  return Object.keys(slots).filter((n) => !SLOT_PROPRI.includes(n))
}

defineExpose({
  reload: () => reloadAll(),
  cambiata,
  chiudiForm,
  formAperto,
  // D-13: le modifiche della voce aperta, per l'uscita dal drawer.
  modificato: fotografia.modificato,
  chiudiConConferma: fotografia.chiudiConConferma,
})
</script>

<template>
  <div>
    <DrawerTabLista
      ref="listaRef"
      :codice="codice"
      :store="store"
      :data-key="dataKey"
      :emittente-esplicito="conEmittente ? emittenteFiscaleId : null"
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
      :riga-attiva="rigaInModifica?.[dataKey] ?? null"
      :righe-cliccabili="isModificabile"
      @page="onPage"
      @sort="onSort"
      @row-click="apriRiga"
      @config-loaded="onConfigLoaded"
    >
      <template #filtri-sempre>
        <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('common.search')" />
      </template>

      <template v-for="nome in slotInoltrati($slots)" #[nome]="scope" :key="nome">
        <slot :name="nome" v-bind="scope ?? {}" />
      </template>

      <template v-if="haColonnaAzioni" #actions="{ data }">
        <RowActionsMenu :row="data" :actions="rowActions(data)" />
      </template>
    </DrawerTabLista>

    <!-- Il form della voce: visibile SOLO quando aperto. I suoi Salva/Annulla
         sono del form (e' una sezione, non un FormFooter del drawer).
         ⛔ La `key` per voce e' necessaria: il clic su un'altra riga a form
         aperto cambia `riga` senza smontare il form, e i form leggono `riga`
         solo alla nascita — senza `key` salverebbero i dati della voce
         precedente sopra quella nuova.
         Lo stacco dalla lista e' di `app-drawer-section` (margin-top). -->
    <div
      v-if="formAperto"
      :key="rigaInModifica?.[dataKey] ?? '__nuova__'"
      :ref="ancoraForm" class="app-drawer-section">
      <h4>{{ formMode === 'edit' ? t(editLabelKey) : t(newLabelKey) }}</h4>
      <slot
        name="form"
        :riga="rigaInModifica"
        :mode="formMode"
        :on-saved="onSaved"
        :on-cancel="chiudiForm"
        :registra="registraForm"
      />
    </div>
  </div>
</template>
