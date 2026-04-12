<script setup>
// Scopo: Sub-drawer dettaglio versione listino con righe prezzo.
// Aggiunta riga: select UoM dipendente dall'articolo selezionato — caricato
// dinamicamente da catalogo.articoli_uom_operativa, con pre-selezione della
// UoM base se presente. Evita di proporre UoM incompatibili con l'articolo.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { displayDate } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { listRighe, createRiga, deleteRiga } from '../api/listini'
import { listArticoloUom } from '../../catalogo/api/catalogo'
import { DRAWER_WIDTH } from '../../core/constants'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import ApplicaVariazioneDialog from './ApplicaVariazioneDialog.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  versione: { type: Object, required: true }
})
const emit = defineEmits(['update:visible'])

const righe = ref([])
const adding = ref(false)
const addForm = ref({})

// UoM operative dell'articolo corrente del form add. Caricate on-demand al
// momento della selezione articolo. Ogni elemento ha {uom_id, uom_codice,
// uom_descrizione, is_base, is_sell_uom, ...}.
const uomOptions = ref([])
const uomLoading = ref(false)

async function loadRighe() {
  if (!props.listinoId || !props.versione?.id) return
  const res = await listRighe(props.listinoId, props.versione.id)
  righe.value = res.data.data.results || []
}

// Watch immediate + reattivo a versione.id: il componente viene montato dal
// padre con `visible` gia' true (vedi ListiniView.onOpenRighe), quindi un watch
// non-immediate non scatterebbe mai alla prima apertura. Ricarico anche se la
// versione cambia mentre il drawer e' aperto. Pulisco le righe alla chiusura
// per evitare flash di dati vecchi alla riapertura.
watch(
  () => [props.visible, props.versione?.id],
  ([v, _vid]) => {
    if (v) {
      loadRighe()
    } else {
      righe.value = []
    }
  },
  { immediate: true },
)

function startAdd() {
  adding.value = true
  addForm.value = { articolo_obj: null, uom_id: null, prezzo: null }
  uomOptions.value = []
}

// Quando l'utente seleziona un articolo: carica le UoM operative compatibili
// e pre-seleziona quella base. Se l'articolo viene deselezionato, azzera tutto.
async function onArticoloSelect(articolo) {
  addForm.value.uom_id = null
  uomOptions.value = []
  if (!articolo?.id) return
  uomLoading.value = true
  try {
    const res = await listArticoloUom(articolo.id)
    const list = res.data.data.results || res.data.data || []
    uomOptions.value = list
    // Pre-seleziona la UoM base se presente, altrimenti la prima disponibile.
    const base = list.find(u => u.is_base)
    if (base) {
      addForm.value.uom_id = base.uom_id
    } else if (list.length === 1) {
      addForm.value.uom_id = list[0].uom_id
    }
  } catch {
    uomOptions.value = []
  } finally {
    uomLoading.value = false
  }
}

async function confirmAdd() {
  const payload = {
    articolo_id: addForm.value.articolo_obj?.id,
    uom_id: addForm.value.uom_id,
    prezzo: addForm.value.prezzo,
  }
  await execute(() => createRiga(props.listinoId, props.versione.id, payload), { successMessage: t('listini.riga_creata') })
  adding.value = false
  await loadRighe()
}

async function removeRow(row) {
  await execute(() => deleteRiga(props.listinoId, props.versione.id, row.id), { successMessage: t('listini.riga_eliminata') })
  await loadRighe()
}

const isBozza = computed(() => props.versione?.stato === 'BOZZA')

const showVariazioneDialog = ref(false)

function onVariazioneApplied() {
  loadRighe()
}

// Etichetta UoM nel dropdown: "codice - descrizione (BASE)" se base.
function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="t('listini.versione')" :title="versione?.codice_versione || `#${versione?.id}`" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.col_stato') }}</label>
          <Tag :value="versione?.stato" :severity="statoVersioneListinoSeverity(versione?.stato)" />
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_valido_dal') }}</label>
          <span>{{ displayDate(versione?.valido_dal) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_valido_al') }}</label>
          <span>{{ displayDate(versione?.valido_al) || '—' }}</span>
        </div>
      </div>

      <div class="app-drawer-section"><h4>{{ t('listini.tab_righe') }}</h4></div>

      <div v-if="isBozza && !adding" class="mt-05 flex gap-2">
        <Button icon="pi pi-plus" :label="t('listini.aggiungi_riga')" text size="small"
          class="app-action-btn" @click="startAdd" />
        <Button icon="pi pi-percentage" :label="t('listini.variazione_pct_titolo')" text size="small"
          class="app-action-btn" @click="showVariazioneDialog = true" />
      </div>

      <template v-if="adding">
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('listini.field_articolo') }} *</label>
            <ArticoloLookup v-model="addForm.articolo_obj" @select="onArticoloSelect" />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_uom') }} *</label>
            <Select v-model="addForm.uom_id"
              :options="uomOptions"
              option-value="uom_id"
              :option-label="uomLabel"
              :placeholder="addForm.articolo_obj?.id ? t('catalogo.select_uom') : t('listini.uom_select_articolo_first')"
              :disabled="!addForm.articolo_obj?.id || uomLoading"
              :loading="uomLoading"
              :empty-message="t('listini.uom_no_operative')" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_prezzo') }} *</label>
            <InputNumber v-model="addForm.prezzo" :minFractionDigits="2" :maxFractionDigits="10" />
          </div>
        </div>
      </template>
      <DrawerFooter v-if="adding" :loading="loading"
        :disabled="!addForm.articolo_obj?.id || !addForm.uom_id || addForm.prezzo == null"
        @save="confirmAdd" @cancel="adding = false" />

      <DataTable :value="righe" :loading="loading" striped-rows class="app-datatable" data-key="id">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" style="width: 130px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" style="min-width: 180px;" />
        <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 80px;" />
        <Column field="prezzo" :header="t('listini.col_prezzo')" style="width: 130px;">
          <template #body="{ data }">{{ data.prezzo }}</template>
        </Column>
        <Column field="billing_account_codice" :header="t('listini.col_ba')" style="width: 120px;" />
        <Column field="utility_descrizione" :header="t('listini.col_utility')" style="width: 130px;" />
        <Column field="emittente_descrizione" :header="t('listini.col_emittente')" style="width: 150px;" />
        <Column v-if="isBozza" style="width: 50px;">
          <template #body="{ data }">
            <Button icon="pi pi-trash" text rounded size="small" class="app-delete-btn" @click="removeRow(data)" />
          </template>
        </Column>
      </DataTable>
    </div>

    <ApplicaVariazioneDialog
      :visible="showVariazioneDialog"
      @update:visible="v => showVariazioneDialog = v"
      :listino-id="listinoId"
      :versione-id="versione?.id"
      @applied="onVariazioneApplied" />
  </Drawer>
</template>
