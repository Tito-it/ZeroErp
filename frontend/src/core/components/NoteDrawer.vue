<script setup>
// Building block "drawer note partizionate" — riusabile cross-dominio.
// Consumato da wrapper di dominio thin (VenditeNoteDrawer, ArticoloNoteDrawer,
// la BoM dell'articolo) che istanziano l'apiClient con `makeNotesApi(basePath)`.
//
// ⭐ Dal 2026-10-31 la lista e' a catalogo (brief-db-liste-datatable-grezze-
//    secondo-giro riga 3, D-2): `vendite.note` o `catalogo.note` secondo la
//    sede (`codice`), sul BB `ListaConFormInline` — pagina, ricerca e
//    ordinamento lato server, colonne e personalizzazione dal catalogo. Il
//    form della nota e' `NotaForm`. ⛔ Fino a quel giorno una `DataTable`
//    grezza sulle prime 200 note, con `useNote` (ritirato).
// ⭐ Le note di vendita hanno il perimetro dell'emittente: il wrapper passa
//    l'emittente del documento (`emittenteFiscaleId`), lasciapassare del
//    cancello per chi vede piu' emittenti.
//
// supportsRiga + righeOptions abilitano nota-di-riga: il select riga diventa
// visibile in creazione; in modifica la riga non si cambia (BE blocca).
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

import { useApiHandler } from '../composables/useApiHandler'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useDrawerListaConForm } from '../composables/useDrawerListaConForm'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../constants'
import { NOTE_CON_EMITTENTE, useNoteListaStore } from '../stores/noteLista'
import AppDrawer from './AppDrawer.vue'
import ListaConFormInline from './ListaConFormInline.vue'
import NotaForm from './NotaForm.vue'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute } = useApiHandler()
const { confirmDelete } = useConfirmAction()

const props = defineProps({
  visible: { type: Boolean, default: false },
  apiClient: { type: Object, required: true },
  // La lista a catalogo della sede: `vendite.note` o `catalogo.note`.
  codice: { type: String, required: true },
  // L'emittente del documento (PK), per `vendite.note`.
  emittenteFiscaleId: { type: Number, default: null },
  title: { type: String, default: null },
  // Quando true mostra il select "Riga" nel form (per partizioni con anchor=RIGA).
  supportsRiga: { type: Boolean, default: false },
  // Opzioni per il select riga: [{ value: <id>, label: <codice o descrizione> }].
  // Il caller costruisce l'array dalle righe gia' caricate nel drawer padre.
  righeOptions: { type: Array, default: () => [] },
})

// `saved` porta il TOTALE note del documento dopo l'operazione (create, update
// o delete): il drawer lo sa dalla lista appena ricaricata, cosi' il padre
// aggiorna un badge counter senza una seconda chiamata.
const emit = defineEmits(['update:visible', 'saved'])

// ⭐ Uno store per ISTANZA (`storePerIstanza`): le note dell'articolo e
//    quelle di un suo componente BoM, vive insieme, non si toccano.
const store = useNoteListaStore(props.codice)
const conEmittente = NOTE_CON_EMITTENTE[props.codice]

// La colla col BB (`useDrawerListaConForm`): il padre e' il percorso delle
// note, SOLO a drawer aperto; footer e uscita seguono il form della nota.
const {
  listaRef, formAperto, padre, modificato, chiudiConConferma, footer, onFormAperto,
} = useDrawerListaConForm({
  visible: () => props.visible,
  padre: () => props.apiClient.basePath,
})

// Scopo: dopo una scrittura, il totale per il badge del padre. ⚠️ La lista si
//        rilegge in differita (`reloadAll` non e' awaitable): il totale si
//        manda a lettura FINITA, non al gesto — quello di prima sarebbe
//        sbagliato di uno.
// ⛔ Il flag vale per IL padre su cui e' stato alzato: se la rilettura non
//    parte (drawer chiuso subito, lettura scartata) non deve sopravvivere al
//    cambio di padre, o alla lettura del documento successivo partirebbe
//    `saved` col totale di un altro documento.
let totaleDaMandare = false
function notificaTotale() {
  totaleDaMandare = true
}
watch(padre, () => { totaleDaMandare = false })
watch(() => store.loading, (inCorso) => {
  if (inCorso || !totaleDaMandare) return
  totaleDaMandare = false
  emit('saved', store.totalRecords)
})

// Scopo: elimina la nota con conferma, rilegge la lista, avvisa il padre.
function onDelete(n) {
  confirmDelete(n.testo_md || n.testo || `#${n.id}`, async () => {
    const result = await execute(() => props.apiClient.deleteNota(n.id))
    if (result === null) return
    if (listaRef.value) listaRef.value.cambiata()
  })
}

function rowActions(n) {
  return [
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !isReadonly.value && !formAperto.value,
      command: () => onDelete(n),
    },
  ]
}

// Decorazione lista: etichetta riga dal mapping righeOptions, fallback id.
function rigaLabel(n) {
  if (n.target_riga_id == null) return null
  const found = props.righeOptions.find(opt => opt.value === n.target_riga_id)
  return found ? found.label : `#${n.target_riga_id}`
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). Ogni uscita (X, ESC,
       clic fuori, Chiudi) passa dalla conferma del form inline; il «Chiudi»
       sparisce a form aperto, che ha gia' il suo Annulla/Salva. -->
  <AppDrawer
    :visible="visible"
    :proteggi-corpo="false"
    :title="title || t('note.titolo_default')"
    :icon="MANAGE_ICONS.NOTE"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.WIDE"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="footer"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <ListaConFormInline
      ref="listaRef"
      :codice="codice"
      :store="store"
      :parent-id="padre"
      :con-emittente="conEmittente"
      :emittente-fiscale-id="emittenteFiscaleId"
      :is-modificabile="!isReadonly"
      new-tooltip-key="note.aggiungi"
      new-label-key="note.nuova"
      edit-label-key="note.modifica"
      :row-actions="rowActions"
      @changed="notificaTotale"
      @form-aperto="onFormAperto"
    >
      <template #cell-anchor_tipo="{ data }">
        <Tag
          :value="data.anchor_tipo === 'RIGA' ? t('note.tag_riga') : t('note.tag_documento')"
          :severity="data.anchor_tipo === 'RIGA' ? 'info' : 'secondary'"
        />
      </template>
      <template #cell-riga="{ data }">
        <span v-if="rigaLabel(data)">{{ rigaLabel(data) }}</span>
        <span v-else class="text-muted">—</span>
      </template>
      <template #cell-testo="{ data }">
        <span class="nota-card-testo">{{ data.testo_md || data.testo }}</span>
      </template>
      <template #cell-lingua="{ data }">
        <span :title="data.lingua_descrizione || ''">{{ data.lingua_codice_iso || '—' }}</span>
      </template>

      <template #form="{ riga, onSaved, onCancel, registra }">
        <NotaForm
          :ref="registra"
          :riga="riga"
          :api-client="apiClient"
          :supports-riga="supportsRiga"
          :righe-options="righeOptions"
          @saved="onSaved"
          @cancel="onCancel"
        />
      </template>
    </ListaConFormInline>
  </AppDrawer>
</template>

<style scoped>
.nota-card-testo {
  font-size: 0.85rem;
  color: var(--app-text-color);
  white-space: pre-wrap;
  word-break: break-word;
}
.text-muted {
  color: var(--app-text-muted);
}
</style>
