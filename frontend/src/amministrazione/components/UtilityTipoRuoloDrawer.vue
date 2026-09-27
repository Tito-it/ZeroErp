<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer crea/modifica riga matrice config.utilities_tipi_ruolo.
//        - In create: select FK utility e tipo_ruolo abilitati.
//        - In edit:   FK disabilitate (immutabili), toggle attivo modificabile,
//                     tab "Utilizzo" mostra emittenti fiscali con override
//                     per la stessa coppia: la lista a catalogo
//                     `config.utilities_tipi_ruolo_usage` (lista 86), su
//                     `useDrawerTabLista` + `<DrawerTabLista>`.
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import { useUtilityTipoRuoloUsageStore } from '../stores/utilityTipoRuoloUsage'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
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
import InputText from 'primevue/inputtext'
import AttivoTag from '../../core/components/AttivoTag.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useUtilitiesTipiRuoloStore()
const usageStore = useUtilityTipoRuoloUsageStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  // Prop esplicita: si combina con inject readonly del parent.
  readonly: { type: Boolean, default: false }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

const form = ref({
  utility_id: null,
  tipo_ruolo_id: null,
  attivo: true
})
// Modifiche non salvate: fotografia all'apertura (anche in creazione), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

const activeTab = ref('dati')
// ⭐ Il tab «Utilizzo» si legge SOLO se l'operatore ci entra, come prima della
//    conversione: la maggior parte delle aperture resta sul tab Dati, e una
//    query per ogni apertura sarebbe lavoro che nessuno guarda. Una volta
//    aperto resta acceso fino alla prossima riga: tornare su «Dati» e poi
//    rientrare non deve perdere la pagina e l'ordine scelti.
const usageAperto = ref(false)

function resetForm() {
  form.value = { utility_id: null, tipo_ruolo_id: null, attivo: true }
  fissa()
}

// ⚠️ `parentId` porta l'id SOLO a drawer aperto, in modifica e col tab gia'
//    visitato: il `null` chiama `usageStore.reset()`, cosi' gli emittenti
//    della riga precedente non lampeggiano sotto la prossima (era il «bug
//    stale data» del reset a mano di prima, ora e' il BB a farlo).
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(usageStore, {
  parentId: () => (props.visible && isEdit.value && usageAperto.value ? props.recordId : null),
  parentField: 'recordId',
})

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  form.value = {
    utility_id: data.utility_id ?? null,
    tipo_ruolo_id: data.tipo_ruolo_id ?? null,
    attivo: data.attivo ?? true
  }
  fissa()
}

// Watch combinato su visible+recordId: gestisce sia open/close sia switch
// tra record diversi a drawer aperto. Reset usage SEMPRE ad ogni apertura.
watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    activeTab.value = 'dati'
    usageAperto.value = false
    if (isEdit.value) {
      loadDetail()
    } else {
      resetForm()
    }
  }
)

watch(activeTab, (tab) => {
  if (tab === 'usage' && isEdit.value) usageAperto.value = true
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
    if (result !== null) { fissa(); emit('saved', result) }
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
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

function close() {
  chiudiConConferma(() => {
    emit('update:visible', false)
    emit('cancelled')
  })
}
const suVisibile = gestoreVisibile(emit, close)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :modificato="modificato"
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('amministrazione.matrice_utilities_ruoli.drawer_title')"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
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
                <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective"
                  :invalid="campiErrati.includes('attivo')"
                />
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
            <!-- Nessun «Emittenti con override: N» in testa: con una ricerca
                 attiva il totale della lista e' quello delle TROVATE, e la
                 riga direbbe un'altra cosa. Il numero lo da' il paginatore. -->
            <DrawerTabLista
              ref="listaRef"
              codice="config.utilities_tipi_ruolo_usage"
              data-key="emittente_id"
              :store="usageStore"
              :rows="usageStore.items"
              :total="usageStore.totalRecords"
              :loading="usageStore.loading"
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
              <template #filtri-sempre>
                <InputText
                  v-model="searchText"
                  class="app-filter-w-lg"
                  :placeholder="t('amministrazione.matrice_utilities_ruoli.usage_cerca_placeholder')"
                />
              </template>
              <template #cell-emittente_attivo="{ data }">
                <AttivoTag :active="data.emittente_attivo" />
              </template>
              <template #cell-override_attivo="{ data }">
                <AttivoTag :active="data.override_attivo" />
              </template>
            </DrawerTabLista>
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
