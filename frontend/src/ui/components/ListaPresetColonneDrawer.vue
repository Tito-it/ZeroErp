<script setup>
// Scopo: Sub-drawer composizione preset (`ui.lista_preset_colonna`).
//        Pattern master-detail inline:
//          - lista paginata sopra (DataTable compatta)
//          - form aggiungi/modifica sotto (inline)
//          - Salva (PUT atomico replace) in fondo
//        DRAWER_WIDTH.WIDE perche' la lista + form + catalogo richiedono
//        spazio. Carica catalogo on-mount per la combo "aggiungi colonna".
//        L'ordine si modifica con frecce (no drag-and-drop esterno).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
// DataTable grezza: la composizione del preset si edita PER INTERO nel client
// (ordine a frecce, PUT atomico che rimpiazza tutto) ed e' limitata dalle
// colonne della lista — un editor di un insieme ordinato, non una lista.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import AppDrawer from '../../core/components/AppDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useUiPresetAdminStore } from '../stores/uiPresetAdmin'



const props = defineProps({
  visible: { type: Boolean, default: false },
  presetId: { type: Number, default: null },
  listaId: { type: Number, default: null },
  presetCodice: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
})


const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const presetStore = useUiPresetAdminStore()
const { execute, loading } = useApiHandler()
const injectedReadonly = useInjectReadonly()
const isReadonlyEffective = computed(
  () => props.readonly || injectedReadonly.value,
)

const composizione = ref([]) // [{colonna_id, codice, etichetta, ordine, larghezza, visibile, fissata}]
const catalogo = ref([])     // [{id, codice, etichetta, gruppo, tipo_colonna}]
const fetching = ref(false)
const fetchError = ref(null)

// Modifiche non salvate (conferma alla chiusura, pallino, titolo arancio):
// si confronta cio' che il Salva manda, senza `ordine`, che lo spostamento
// rinumera (l'ordine lo dice la posizione nell'elenco).
// ⭐ E' l'UNICA risposta a «c'e' qualcosa da salvare?»: abilita il Salva,
//    mostra l'avviso e chiede conferma all'uscita (prima un `dirty` acceso a
//    mano la affiancava, e diceva «toccato» invece di «diverso»: spostare una
//    colonna e rimetterla a posto lasciava il Salva acceso).
// ⚠️ L'InputNumber della larghezza scrive il modello solo al blur: nel
//    template lo si aggiorna anche su `@input`, o il Salva resterebbe spento
//    durante la digitazione (e un Salva spento non toglie il fuoco al campo).
const composizioneDaSalvare = computed(() =>
  composizione.value.map((c) => ({
    colonna_id: c.colonna_id,
    larghezza: c.larghezza ?? null,
    visibile: c.visibile,
    fissata: c.fissata,
  })),
)
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(composizioneDaSalvare, { visibile: () => props.visible })

// Colonne del catalogo NON ancora in composizione (combo "aggiungi").
const catalogoDisponibile = computed(() => {
  const presenti = new Set(composizione.value.map((c) => c.colonna_id))
  return catalogo.value.filter((c) => !presenti.has(c.id))
})

const colonnaDaAggiungere = ref(null)

watch(() => props.visible, async (visible) => {
  if (!visible) return
  await loadAll()
})

async function loadAll() {
  if (!props.presetId || !props.listaId) return
  fetching.value = true
  fetchError.value = null
  try {
    const [comp, cat] = await Promise.all([
      presetStore.listColonne(props.presetId),
      presetStore.listCatalogo(props.listaId),
    ])
    // La risposta composizione gia' include codice/etichetta via JOIN;
    // mantengo solo i campi mutabili lato FE per il form.
    composizione.value = comp.map((row) => ({
      colonna_id: row.colonna_id,
      codice: row.codice,
      etichetta: row.etichetta,
      tipo_colonna: row.tipo_colonna,
      ordine: row.ordine,
      larghezza: row.larghezza,
      visibile: !!row.visibile,
      fissata: !!row.fissata,
    }))
    catalogo.value = cat
    fissa()
    colonnaDaAggiungere.value = null
  } catch (e) {
    fetchError.value = e
  } finally {
    fetching.value = false
  }
}

function aggiungiColonna() {
  if (!colonnaDaAggiungere.value) return
  const cat = catalogo.value.find((c) => c.id === colonnaDaAggiungere.value)
  if (!cat) return
  const nextOrdine =
    composizione.value.length > 0
      ? Math.max(...composizione.value.map((c) => c.ordine || 0)) + 10
      : 10
  composizione.value.push({
    colonna_id: cat.id,
    codice: cat.codice,
    etichetta: cat.etichetta,
    tipo_colonna: cat.tipo_colonna,
    ordine: nextOrdine,
    larghezza: null,
    visibile: true,
    fissata: false,
  })
  colonnaDaAggiungere.value = null
}

function rimuoviColonna(colonna_id) {
  composizione.value = composizione.value.filter(
    (c) => c.colonna_id !== colonna_id,
  )
}

function spostaSu(idx) {
  if (idx <= 0) return
  const items = [...composizione.value]
  ;[items[idx - 1], items[idx]] = [items[idx], items[idx - 1]]
  composizione.value = riassegnaOrdini(items)
}

function spostaGiu(idx) {
  if (idx >= composizione.value.length - 1) return
  const items = [...composizione.value]
  ;[items[idx + 1], items[idx]] = [items[idx], items[idx + 1]]
  composizione.value = riassegnaOrdini(items)
}

function riassegnaOrdini(items) {
  return items.map((c, i) => ({ ...c, ordine: (i + 1) * 10 }))
}

const canSave = computed(() => modificato.value && !fetching.value)

async function onSave() {
  if (!canSave.value) return
  const payload = {
    colonne: composizione.value.map((c) => ({
      colonna_id: c.colonna_id,
      ordine: c.ordine,
      larghezza: c.larghezza ?? null,
      visibile: c.visibile,
      fissata: c.fissata,
    })),
  }
  const result = await execute(
    () => presetStore.replaceColonne(props.presetId, payload),
    { successMessage: t('notifications.save_success') },
  )
  if (result !== null) {
    // Resta aperto senza ricaricare: la fotografia e' cio' che si e' salvato.
    fissa()
    emit('saved', result)
  }
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="`${t('ui.admin.preset_composizione')} — ${presetCodice}`"
    :icon="NAV_ICONS.PERSONALIZZAZIONI_LISTE"
    :width="DRAWER_WIDTH.WIDE"
    :readonly="isReadonlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="isReadonlyEffective ? 'chiudi' : 'form'"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
  >
    <Message
      v-if="fetchError"
      severity="error"
      :closable="false"
    >
      {{ t('ui.admin.composizione_load_error') }}
    </Message>

    <div class="composizione-toolbar">
      <Select
        v-model="colonnaDaAggiungere"
        :options="catalogoDisponibile"
        option-label="etichetta"
        option-value="id"
        :placeholder="t('ui.admin.composizione_seleziona_colonna')"
        :disabled="isReadonlyEffective || fetching || catalogoDisponibile.length === 0"
        :filter="catalogoDisponibile.length > 5"
        class="composizione-select"
      />
      <Button
        :label="t('common.add')"
        :icon="MANAGE_ICONS.ADD"
        class="app-action-btn"
        :disabled="isReadonlyEffective || !colonnaDaAggiungere"
        @click="aggiungiColonna"
      />
    </div>

    <DataTable
      :value="composizione"
      data-key="colonna_id"
      class="app-datatable"
      :loading="fetching"
      scrollable
      scroll-height="flex"
    >
      <Column field="ordine" :header="t('ui.admin.composizione_col_ordine')" style="width: 90px">
        <template #body="{ index }">
          <div class="ordine-actions">
            <Button
              :icon="MANAGE_ICONS.SPOSTA_SU"
              text
              rounded
              size="small"
              :disabled="isReadonlyEffective || index === 0"
              @click="spostaSu(index)"
            />
            <Button
              :icon="MANAGE_ICONS.SPOSTA_GIU"
              text
              rounded
              size="small"
              :disabled="isReadonlyEffective || index === composizione.length - 1"
              @click="spostaGiu(index)"
            />
          </div>
        </template>
      </Column>
      <Column field="codice" :header="t('ui.admin.composizione_col_codice')" style="width: 180px" />
      <Column field="etichetta" :header="t('ui.admin.composizione_col_etichetta')" />
      <Column :header="t('ui.admin.composizione_col_larghezza')" style="width: 120px">
        <template #body="{ data }">
          <InputNumber
            v-model="data.larghezza"
            :min="40"
            :max="800"
            :disabled="isReadonlyEffective"
            show-buttons
            size="small"
            @input="(e) => (data.larghezza = e.value)"
          />
        </template>
      </Column>
      <Column :header="t('ui.admin.composizione_col_visibile')" style="width: 90px">
        <template #body="{ data }">
          <Checkbox
            v-model="data.visibile"
            binary
            :disabled="isReadonlyEffective || data.tipo_colonna === 'identificatore' || data.tipo_colonna === 'azione'"
          />
        </template>
      </Column>
      <Column :header="t('ui.admin.composizione_col_fissata')" style="width: 90px">
        <template #body="{ data }">
          <Checkbox
            v-model="data.fissata"
            binary
            :disabled="isReadonlyEffective"
          />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" :exportable="false" style="width: 70px">
        <template #body="{ data }">
          <Button
            :icon="MANAGE_ICONS.DELETE"
            text
            rounded
            size="small"
            class="app-delete-btn"
            :disabled="isReadonlyEffective"
            @click.stop="rimuoviColonna(data.colonna_id)"
          />
        </template>
      </Column>
    </DataTable>

    <Message
      v-if="modificato"
      severity="warn"
      :closable="false"
      size="small"
      class="mt-1"
    >
      {{ t('ui.admin.composizione_dirty_warning') }}
    </Message>
  </AppDrawer>
</template>

<style scoped>
.composizione-toolbar {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
.composizione-select {
  flex: 1;
  max-width: 360px;
}
.ordine-actions {
  display: flex;
  gap: 0.125rem;
}
</style>
