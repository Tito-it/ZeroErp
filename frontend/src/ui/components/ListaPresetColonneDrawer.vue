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
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
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
const dirty = ref(false)
const fetchError = ref(null)

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
    dirty.value = false
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
  markDirty()
}

function rimuoviColonna(colonna_id) {
  composizione.value = composizione.value.filter(
    (c) => c.colonna_id !== colonna_id,
  )
  markDirty()
}

function spostaSu(idx) {
  if (idx <= 0) return
  const items = [...composizione.value]
  ;[items[idx - 1], items[idx]] = [items[idx], items[idx - 1]]
  composizione.value = riassegnaOrdini(items)
  markDirty()
}

function spostaGiu(idx) {
  if (idx >= composizione.value.length - 1) return
  const items = [...composizione.value]
  ;[items[idx + 1], items[idx]] = [items[idx], items[idx + 1]]
  composizione.value = riassegnaOrdini(items)
  markDirty()
}

function riassegnaOrdini(items) {
  return items.map((c, i) => ({ ...c, ordine: (i + 1) * 10 }))
}

function markDirty() {
  dirty.value = true
}

const canSave = computed(() => dirty.value && !fetching.value)

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
    dirty.value = false
    emit('saved', result)
  }
}

function onCancel() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="(v) => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :modal="true"
    :dismissable-mask="false"
  >
    <template #header>
      <DrawerTitle
        :title="`${t('ui.admin.preset_composizione')} — ${presetCodice}`"
        icon="pi pi-table"
      />
    </template>

    <div
      class="app-drawer-content"
      :class="{ 'app-readonly': isReadonlyEffective }"
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
          icon="pi pi-plus"
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
                icon="pi pi-chevron-up"
                text
                rounded
                size="small"
                :disabled="isReadonlyEffective || index === 0"
                @click="spostaSu(index)"
              />
              <Button
                icon="pi pi-chevron-down"
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
              @input="markDirty"
            />
          </template>
        </Column>
        <Column :header="t('ui.admin.composizione_col_visibile')" style="width: 90px">
          <template #body="{ data }">
            <Checkbox
              v-model="data.visibile"
              binary
              :disabled="isReadonlyEffective || data.tipo_colonna === 'identificatore' || data.tipo_colonna === 'azione'"
              @change="markDirty"
            />
          </template>
        </Column>
        <Column :header="t('ui.admin.composizione_col_fissata')" style="width: 90px">
          <template #body="{ data }">
            <Checkbox
              v-model="data.fissata"
              binary
              :disabled="isReadonlyEffective"
              @change="markDirty"
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
        v-if="dirty"
        severity="warn"
        :closable="false"
        size="small"
        class="mt-1"
      >
        {{ t('ui.admin.composizione_dirty_warning') }}
      </Message>
    </div>

    <FormFooter
      v-if="!isReadonlyEffective"
      :loading="loading"
      :disabled="!canSave"
      @save="onSave"
      @cancel="onCancel"
    />
  </Drawer>
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
