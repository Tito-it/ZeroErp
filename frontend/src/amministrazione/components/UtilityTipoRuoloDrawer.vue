<script setup>
// Scopo: Drawer crea/modifica riga matrice config.utilities_tipi_ruolo.
//        - In create: select FK utility e tipo_ruolo abilitati.
//        - In edit:   FK disabilitate (immutabili), toggle attivo modificabile,
//                     tab "Utilizzo" mostra emittenti fiscali con override
//                     per la stessa coppia.
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import ToggleSwitch from 'primevue/toggleswitch'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import AttivoTag from '../../core/components/AttivoTag.vue'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useUtilitiesTipiRuoloStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  // Prop esplicita: si combina con inject readonly del parent.
  readonly: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

const form = ref({
  utility_id: null,
  tipo_ruolo_id: null,
  attivo: true
})

const activeTab = ref('dati')
const usageRows = ref([])
const usageCount = ref(0)
const usageLoading = ref(false)
const usageLoaded = ref(false)

function resetForm() {
  form.value = { utility_id: null, tipo_ruolo_id: null, attivo: true }
}

// Scopo: Reset stato tab Utilizzo. Eseguito ad ogni apertura del drawer per
//        evitare di mostrare dati di un record precedente (bug stale data
//        quando il drawer rimane montato tra aperture diverse).
function resetUsage() {
  usageRows.value = []
  usageCount.value = 0
  usageLoaded.value = false
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  form.value = {
    utility_id: data.utility_id ?? null,
    tipo_ruolo_id: data.tipo_ruolo_id ?? null,
    attivo: data.attivo ?? true
  }
}

async function loadUsage() {
  if (!props.recordId || usageLoaded.value) return
  usageLoading.value = true
  try {
    const data = await store.fetchUsage(props.recordId, { limit: 100 })
    usageRows.value = data.results || []
    usageCount.value = data.count || 0
    usageLoaded.value = true
  } finally {
    usageLoading.value = false
  }
}

// Watch combinato su visible+recordId: gestisce sia open/close sia switch
// tra record diversi a drawer aperto. Reset usage SEMPRE ad ogni apertura.
watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    activeTab.value = 'dati'
    resetUsage()
    if (isEdit.value) {
      loadDetail()
    } else {
      resetForm()
    }
  }
)

watch(activeTab, (tab) => {
  if (tab === 'usage' && isEdit.value) loadUsage()
})

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  if (isEdit.value) return true // attivo e' boolean, sempre valido
  return form.value.utility_id != null && form.value.tipo_ruolo_id != null
})

// Scopo: Salva e delega la chiusura al parent (pattern PraticaDrawer).
// Il drawer NON chiama close() qui per evitare il "rimbalzo" visivo: se il
// drawer si auto-chiudesse in parallelo con l'await fetchList del parent,
// l'animazione di chiusura del Drawer e il re-render della tabella sotto
// causerebbero un jitter percepito. Unico punto di chiusura: il parent in
// onDrawerSaved dopo await fetchList.
async function handleSave() {
  if (isEdit.value) {
    const payload = { attivo: form.value.attivo }
    const result = await execute(
      () => store.update(props.recordId, payload),
      { successMessage: t('amministrazione.matrice_utilities_ruoli.saved') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const payload = {
      utility_id: form.value.utility_id,
      tipo_ruolo_id: form.value.tipo_ruolo_id,
      attivo: form.value.attivo
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('amministrazione.matrice_utilities_ruoli.created') }
    )
    if (result !== null) emit('saved', result)
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('amministrazione.matrice_utilities_ruoli.drawer_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <Tabs v-model:value="activeTab">
        <TabList>
          <Tab value="dati">{{ t('amministrazione.matrice_utilities_ruoli.tab_dati') }}</Tab>
          <Tab v-if="isEdit" value="usage">
            {{ t('amministrazione.matrice_utilities_ruoli.tab_usage') }}
          </Tab>
        </TabList>
        <TabPanels>
          <!-- TAB Dati -->
          <TabPanel value="dati">
            <div class="form-grid">
              <div class="form-field">
                <label>{{ t('amministrazione.matrice_utilities_ruoli.field_utility') }}</label>
                <LookupSelect
                  v-model="form.utility_id"
                  rel="config.utilities"
                  :placeholder="t('amministrazione.matrice_utilities_ruoli.field_utility_placeholder')"
                  :disabled="isEdit || isReadOnlyEffective"
                />
              </div>
              <div class="form-field">
                <label>{{ t('amministrazione.matrice_utilities_ruoli.field_tipo_ruolo') }}</label>
                <LookupSelect
                  v-model="form.tipo_ruolo_id"
                  rel="config.tipi_ruoli"
                  :placeholder="t('amministrazione.matrice_utilities_ruoli.field_tipo_ruolo_placeholder')"
                  :disabled="isEdit || isReadOnlyEffective"
                />
              </div>
              <div class="form-field">
                <label>{{ t('common.attivo') }}</label>
                <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective" />
              </div>
              <Message v-if="isEdit" severity="info" :closable="false">
                {{ t('amministrazione.matrice_utilities_ruoli.fk_immutable_hint') }}
              </Message>
            </div>
          </TabPanel>

          <!-- TAB Usage -->
          <TabPanel v-if="isEdit" value="usage">
            <div class="form-field">
              <Message severity="info" :closable="false">
                {{ t('amministrazione.matrice_utilities_ruoli.usage_hint') }}
              </Message>
            </div>
            <div class="form-field">
              <strong>{{ t('amministrazione.matrice_utilities_ruoli.usage_count') }}:</strong>
              {{ usageCount }}
            </div>
            <DataTable
              :value="usageRows"
              :loading="usageLoading"
              striped-rows
              size="small"
              class="app-datatable"
              data-key="emittente_id"
            >
              <Column
                field="emittente_codice"
                :header="t('amministrazione.matrice_utilities_ruoli.usage_col_codice')"
                style="width: 140px;"
              />
              <Column
                field="emittente_descrizione"
                :header="t('amministrazione.matrice_utilities_ruoli.usage_col_ragione_sociale')"
                style="min-width: 220px;"
              />
              <Column
                field="emittente_attivo"
                :header="t('common.attivo')"
                style="width: 100px;"
              >
                <template #body="{ data }">
                  <AttivoTag :active="data.emittente_attivo" />
                </template>
              </Column>
            </DataTable>
          </TabPanel>
        </TabPanels>
      </Tabs>

      <FormFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="close"
      />
    </div>
  </Drawer>
</template>
