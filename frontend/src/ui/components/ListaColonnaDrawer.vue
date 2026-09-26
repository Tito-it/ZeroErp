<script setup>
// Scopo: Drawer crea/modifica `ui.lista_colonna` (Blocco F Fase 2 —
//        DEF-5b). 17 campi del catalogo splittati in 3 sotto-tab per
//        UX (decisione 8 _def.md):
//          - Generale: codice, etichetta, etichetta_estesa,
//            etichetta_i18n_key, tipo_colonna, tipo_dato, campo_sorgente
//          - Comportamento: filtrabile, ordinabile, esportabile,
//            ricercabile_full, sensibile, attivo
//          - Layout: formato, larghezza_default, ordine_default,
//            allineamento, gruppo, gruppo_ordine
//
//        UX vincoli (decisione 6):
//          - tipo_colonna='azione' -> esportabile forzato a False e
//            disabilitato (CHECK constraint DB)
//          - lista_id immutabile (in edit non editabile, in create
//            arriva dal Select header via prop)
//          - etichetta_i18n_key + etichetta separati (decisione 3):
//            il BE risolve la cascata `t(key) || etichetta` lato runtime.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { DRAWER_WIDTH } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
import { useUiColonnaAdminStore } from '../stores/uiColonnaAdmin'



const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  recordId: { type: Number, default: null },
  recordData: { type: Object, default: null },
  listaId: { type: Number, default: null },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const colonnaStore = useUiColonnaAdminStore()
const { execute, loading, campiErrati } = useApiHandler()

const isEdit = computed(() => props.mode === 'edit')
const activeTab = ref('generale')

// Snapshot di listaId al momento dell'apertura del drawer in create:
// se l'utente cambia il Select header "Lista corrente" mentre il drawer
// e' aperto, props.listaId reattiva cambia ma la colonna deve finire
// nella lista selezionata all'apertura — non in quella corrente.
// In edit non serve: lista_id e' immutabile per design (pattern del
// service `_build_update_data`).
const drawerListaId = ref(null)

// Enum statici DB - duplicati lato FE per Select. La FK enum garantisce
// la guard finale; qui filtriamo presto per UX.
const tipoColonnaOptions = computed(() => [
  { label: t('ui.admin.tipo_colonna_identificatore'), value: 'identificatore' },
  { label: t('ui.admin.tipo_colonna_informazione'), value: 'informazione' },
  { label: t('ui.admin.tipo_colonna_azione'), value: 'azione' },
])

const tipoDatoOptions = computed(() => [
  { label: t('ui.admin.tipo_dato_string'), value: 'string' },
  { label: t('ui.admin.tipo_dato_numeric'), value: 'numeric' },
  { label: t('ui.admin.tipo_dato_date'), value: 'date' },
  { label: t('ui.admin.tipo_dato_datetime'), value: 'datetime' },
  { label: t('ui.admin.tipo_dato_boolean'), value: 'boolean' },
  { label: t('ui.admin.tipo_dato_enum'), value: 'enum' },
])

const allineamentoOptions = computed(() => [
  { label: t('ui.admin.allineamento_left'), value: 'left' },
  { label: t('ui.admin.allineamento_right'), value: 'right' },
  { label: t('ui.admin.allineamento_center'), value: 'center' },
])

function defaultForm() {
  return {
    codice: '',
    etichetta: '',
    etichetta_estesa: '',
    etichetta_i18n_key: '',
    tipo_colonna: 'informazione',
    tipo_dato: 'string',
    campo_sorgente: '',
    filtrabile: true,
    ordinabile: true,
    esportabile: true,
    ricercabile_full: false,
    sensibile: false,
    attivo: true,
    formato: '',
    larghezza_default: null,
    ordine_default: 100,
    allineamento: 'left',
    gruppo: '',
    gruppo_ordine: null,
  }
}

const form = ref(defaultForm())
// Modifiche non salvate: fotografia a form popolato, conferma alla chiusura
// (BB useDrawerFormPreserve). Prima del watch immediate (TDZ).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

watch(
  () => [props.visible, props.recordData],
  ([visible, data]) => {
    if (!visible) return
    activeTab.value = 'generale'
    // Snapshot lista_id solo all'apertura. Resta congelato finche' il
    // drawer non viene chiuso, anche se il Select header cambia.
    drawerListaId.value = props.listaId
    if (isEdit.value && data) {
      form.value = {
        codice: data.codice ?? '',
        etichetta: data.etichetta ?? '',
        etichetta_estesa: data.etichetta_estesa ?? '',
        etichetta_i18n_key: data.etichetta_i18n_key ?? '',
        tipo_colonna: data.tipo_colonna ?? 'informazione',
        tipo_dato: data.tipo_dato ?? 'string',
        campo_sorgente: data.campo_sorgente ?? '',
        filtrabile: !!data.filtrabile,
        ordinabile: !!data.ordinabile,
        esportabile: !!data.esportabile,
        ricercabile_full: !!data.ricercabile_full,
        sensibile: !!data.sensibile,
        attivo: !!data.attivo,
        formato: data.formato ?? '',
        larghezza_default: data.larghezza_default ?? null,
        ordine_default: data.ordine_default ?? 100,
        allineamento: data.allineamento ?? 'left',
        gruppo: data.gruppo ?? '',
        gruppo_ordine: data.gruppo_ordine ?? null,
      }
    } else {
      form.value = defaultForm()
    }
    fissa()
  },
  { immediate: true },
)

// UX vincolo (decisione 6 _def.md): se tipo_colonna='azione' forziamo
// esportabile=false. Coerente col CHECK chk_ui_lista_colonna_azione_non_esportabile.
const isAzione = computed(() => form.value.tipo_colonna === 'azione')

watch(isAzione, (azione) => {
  if (azione && form.value.esportabile) {
    form.value.esportabile = false
  }
})

const canSave = computed(() => {
  if (!form.value.codice?.trim()) return false
  if (!form.value.etichetta?.trim()) return false
  if (!form.value.tipo_colonna) return false
  if (!form.value.tipo_dato) return false
  if (form.value.ordine_default == null) return false
  if (!isEdit.value && drawerListaId.value == null) return false
  return true
})

function buildPayload() {
  // Empty string -> null per opzionali (pattern null_vs_empty BE-aware).
  const payload = {
    codice: form.value.codice.trim(),
    etichetta: form.value.etichetta.trim(),
    etichetta_estesa: form.value.etichetta_estesa?.trim() || null,
    etichetta_i18n_key: form.value.etichetta_i18n_key?.trim() || null,
    tipo_colonna: form.value.tipo_colonna,
    tipo_dato: form.value.tipo_dato,
    campo_sorgente: form.value.campo_sorgente?.trim() || null,
    formato: form.value.formato?.trim() || null,
    larghezza_default: form.value.larghezza_default,
    ordine_default: form.value.ordine_default,
    allineamento: form.value.allineamento,
    gruppo: form.value.gruppo?.trim() || null,
    gruppo_ordine: form.value.gruppo_ordine,
    filtrabile: form.value.filtrabile,
    ordinabile: form.value.ordinabile,
    esportabile: form.value.esportabile,
    ricercabile_full: form.value.ricercabile_full,
    sensibile: form.value.sensibile,
    attivo: form.value.attivo,
  }
  return payload
}

async function onSave() {
  if (!canSave.value) return
  const payload = buildPayload()
  let result
  if (isEdit.value) {
    result = await execute(
      () => colonnaStore.update(props.recordId, payload),
      { successMessage: t('notifications.save_success') },
    )
  } else {
    result = await execute(
      () => colonnaStore.create(drawerListaId.value, payload),
      { successMessage: t('notifications.save_success') },
    )
  }
  if (result !== null) {
    emit('saved', result)
  }
}

function onCancel() {
  emit('cancelled')
  emit('update:visible', false)
}
const chiudi = () => chiudiConConferma(onCancel)
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :modal="true"
    :dismissable-mask="false"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :modificato="modificato"
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('ui.admin.colonna')"
        icon="pi pi-table"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content">
      <Tabs v-model:value="activeTab">
        <TabList>
          <Tab value="generale">{{ t('ui.admin.colonna_tab_generale') }}</Tab>
          <Tab value="comportamento">{{ t('ui.admin.colonna_tab_comportamento') }}</Tab>
          <Tab value="layout">{{ t('ui.admin.colonna_tab_layout') }}</Tab>
        </TabList>

        <TabPanels>
          <TabPanel value="generale">
            <div class="form-grid">
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_codice') }}</label>
                  <InputText v-model="form.codice" maxlength="80"
                    :invalid="campiErrati.includes('codice')"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_campo_sorgente') }}</label>
                  <InputText v-model="form.campo_sorgente" maxlength="80"
                    :invalid="campiErrati.includes('campo_sorgente')"
                  />
                  <Message
                    severity="info"
                    :closable="false"
                    size="small"
                    class="mt-025"
                  >
                    {{ t('ui.admin.colonna_campo_sorgente_hint') }}
                  </Message>
                </div>
              </div>

              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_etichetta') }}</label>
                  <InputText v-model="form.etichetta" maxlength="120"
                    :invalid="campiErrati.includes('etichetta')"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_etichetta_i18n_key') }}</label>
                  <InputText v-model="form.etichetta_i18n_key" maxlength="120"
                    :invalid="campiErrati.includes('etichetta_i18n_key')"
                  />
                  <Message
                    severity="info"
                    :closable="false"
                    size="small"
                    class="mt-025"
                  >
                    {{ t('ui.admin.colonna_etichetta_i18n_hint') }}
                  </Message>
                </div>
              </div>

              <div class="form-field">
                <label>{{ t('ui.admin.colonna_etichetta_estesa') }}</label>
                <InputText v-model="form.etichetta_estesa" maxlength="200"
                  :invalid="campiErrati.includes('etichetta_estesa')"
                />
              </div>

              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_tipo_colonna') }}</label>
                  <Select
                    v-model="form.tipo_colonna"
                    :options="tipoColonnaOptions"
                    option-label="label"
                    option-value="value"
                    :invalid="campiErrati.includes('tipo_colonna')"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_tipo_dato') }}</label>
                  <Select
                    v-model="form.tipo_dato"
                    :options="tipoDatoOptions"
                    option-label="label"
                    option-value="value"
                    :invalid="campiErrati.includes('tipo_dato')"
                  />
                </div>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="comportamento">
            <div class="form-grid">
              <div class="form-grid-2col">
                <div class="form-field form-field-inline">
                  <Checkbox v-model="form.filtrabile" binary input-id="ui-col-filtrabile" />
                  <label for="ui-col-filtrabile">{{ t('ui.admin.colonna_filtrabile') }}</label>
                </div>
                <div class="form-field form-field-inline">
                  <Checkbox v-model="form.ordinabile" binary input-id="ui-col-ordinabile" />
                  <label for="ui-col-ordinabile">{{ t('ui.admin.colonna_ordinabile') }}</label>
                </div>
              </div>

              <div class="form-grid-2col">
                <div class="form-field form-field-inline">
                  <Checkbox
                    v-model="form.esportabile"
                    binary
                    input-id="ui-col-esportabile"
                    :disabled="isAzione"
                  />
                  <label for="ui-col-esportabile">{{ t('ui.admin.colonna_esportabile') }}</label>
                </div>
                <div class="form-field form-field-inline">
                  <Checkbox v-model="form.ricercabile_full" binary input-id="ui-col-ricercabile" />
                  <label for="ui-col-ricercabile">{{ t('ui.admin.colonna_ricercabile_full') }}</label>
                </div>
              </div>
              <Message
                v-if="isAzione"
                severity="info"
                :closable="false"
                size="small"
              >
                {{ t('ui.admin.colonna_azione_non_esportabile_hint') }}
              </Message>

              <div class="form-grid-2col">
                <div class="form-field form-field-inline">
                  <Checkbox v-model="form.sensibile" binary input-id="ui-col-sensibile" />
                  <label for="ui-col-sensibile">{{ t('ui.admin.colonna_sensibile') }}</label>
                </div>
                <div class="form-field form-field-inline">
                  <Checkbox v-model="form.attivo" binary input-id="ui-col-attivo"
                    :invalid="campiErrati.includes('attivo')"
                  />
                  <label for="ui-col-attivo">{{ t('common.active') }}</label>
                </div>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="layout">
            <div class="form-grid">
              <div class="form-grid-3col">
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_ordine_default') }}</label>
                  <InputNumber v-model="form.ordine_default" :min="1" :max="100000" show-buttons
                    :invalid="campiErrati.includes('ordine_default')"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_larghezza_default') }}</label>
                  <InputNumber v-model="form.larghezza_default" :min="1" :max="4000" show-buttons />
                </div>
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_allineamento') }}</label>
                  <Select
                    v-model="form.allineamento"
                    :options="allineamentoOptions"
                    option-label="label"
                    option-value="value"
                    :invalid="campiErrati.includes('allineamento')"
                  />
                </div>
              </div>

              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_formato') }}</label>
                  <InputText v-model="form.formato" maxlength="60"
                    :invalid="campiErrati.includes('formato')"
                  />
                  <Message
                    severity="info"
                    :closable="false"
                    size="small"
                    class="mt-025"
                  >
                    {{ t('ui.admin.colonna_formato_hint') }}
                  </Message>
                </div>
                <div class="form-field">
                  <label>{{ t('ui.admin.colonna_gruppo_ordine') }}</label>
                  <InputNumber v-model="form.gruppo_ordine" :min="1" :max="100000" show-buttons />
                </div>
              </div>

              <div class="form-field">
                <label>{{ t('ui.admin.colonna_gruppo') }}</label>
                <InputText v-model="form.gruppo" maxlength="60"
                  :invalid="campiErrati.includes('gruppo')"
                />
              </div>
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <FormFooter v-if="contentReady"
      :loading="loading"
      :disabled="!canSave"
      @save="onSave"
      @cancel="chiudi"
    />
  </Drawer>
</template>

<style scoped>
.form-field-inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
</style>
