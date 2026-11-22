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
//        UX vincoli (i vincoli li tiene il DB, giro 4 di
//        brief-db-revisione-ui; qui il form non propone cio' che il DB
//        rifiuterebbe):
//          - tipo_colonna='azione' -> campo sorgente vuoto e spento (U24)
//          - senza campo sorgente -> esportabile False e spento (U25)
//          - origine_campo='LINEAGE' -> filtrabile, ordinabile e
//            ricercabile False e spenti (la genealogia si mostra soltanto)
//          - lista_id e codice immutabili (in edit non editabili e fuori dal
//            PATCH; codice dal giro 4, BE12; lista_id in create arriva dal
//            Select header via prop)
//          - etichetta_i18n_key + etichetta separati (decisione 3):
//            il BE risolve la cascata `t(key) || etichetta` lato runtime.
//          - su una colonna nata dal seed di primo impianto i campi del
//            software sono spenti col motivo e restano fuori dal PATCH
//            (R-UI-sup di brief-db-seed-primo-impianto-non-si-riscrive §16.15)
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
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
import AppDrawer from '../../core/components/AppDrawer.vue'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useUiColonnaAdminStore } from '../stores/uiColonnaAdmin'
import { campoDelSoftware } from '../../core/utils/campoDelSoftware'
import { campoFermo } from '../../core/utils/campoFermo'
import MotivoDelProgramma from '../../core/components/MotivoDelProgramma.vue'
import { senzaCampiFermi } from '../../core/utils/senzaCampiFermi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  recordId: { type: Number, default: null },
  recordData: { type: Object, default: null },
  listaId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const colonnaStore = useUiColonnaAdminStore()
const { execute, loading, campiErrati } = useApiHandler()

const isEdit = computed(() => props.mode === 'edit')

// Scopo: il campo lo stabilisce il programma su questa colonna (riga di
// seed)? L'elenco viaggia con la riga della lista (`campi_del_software`).
const delProgramma = (campo) => isEdit.value && campoDelSoftware(props.recordData, campo)
// Scopo: il campo e' fermo in modifica: del programma, oppure fermo per
// modello (il codice, chiave di preferenze e preset: giro 4, BE12). Lo dice la
// riga (`campi_del_software`, `non_editable_fields`), BB `campoFermo`.
const fermo = (campo) => isEdit.value && campoFermo(props.recordData, campo)
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

// Enum `ui.origine_campo_lista`: da dove la colonna prende il dato.
const origineCampoOptions = computed(() => [
  { label: t('ui.admin.origine_campo_vista'), value: 'VISTA' },
  { label: t('ui.admin.origine_campo_lineage'), value: 'LINEAGE' },
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
    origine_campo: 'VISTA',
    filtrabile: true,
    ordinabile: true,
    // Il campo sorgente nasce vuoto, quindi la colonna nasce non esportabile
    // (U25); scrivendo il campo si accende (watch `senzaCampo`).
    esportabile: false,
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
        origine_campo: data.origine_campo ?? 'VISTA',
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

// UX vincoli del giro 4 (CHECK del DB, che resta il giudice): il form non
// propone una combinazione che il DB rifiuterebbe. Si spegne cio' che non
// vale piu' quando cambia il campo che lo regge.
// ⚠️ I watch scattano anche al caricamento di una riga (il form si
//    rimpiazza): per questo spengono soltanto, e una riga letta dal DB e' gia'
//    coerente coi CHECK, quindi non la toccano. L'unico che ACCENDE
//    (esportabile quando il campo compare) vale solo in creazione, come il
//    default del service: in modifica lo sceglie l'operatore.
const isAzione = computed(() => form.value.tipo_colonna === 'azione')
const senzaCampo = computed(() => !form.value.campo_sorgente?.trim())
const isLineage = computed(() => form.value.origine_campo === 'LINEAGE')

watch(isAzione, (azione) => {
  if (azione) form.value.campo_sorgente = ''
})
watch(senzaCampo, (senza) => {
  if (senza) form.value.esportabile = false
  else if (!isEdit.value) form.value.esportabile = true
})
watch(isLineage, (lineage) => {
  if (!lineage) return
  form.value.filtrabile = false
  form.value.ordinabile = false
  form.value.ricercabile_full = false
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
    origine_campo: form.value.origine_campo,
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
  // ⛔ Un campo del programma non entra nel PATCH: il guard del DB lo rifiuta.
  const payload = isEdit.value ? senzaCampiFermi(buildPayload(), fermo) : buildPayload()
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

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('ui.admin.colonna')"
    :icon="NAV_ICONS.PERSONALIZZAZIONI_LISTE"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.WIDE"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >
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
                <InputText v-model="form.codice"
                  :disabled="fermo('codice')" maxlength="80"
                  :invalid="campiErrati.includes('codice')"
                />
                <MotivoDelProgramma campo="codice" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_campo_sorgente') }}</label>
                <InputText v-model="form.campo_sorgente"
                  :disabled="isAzione || delProgramma('campo_sorgente')" maxlength="80"
                  :invalid="campiErrati.includes('campo_sorgente')"
                />
                <MotivoDelProgramma campo="campo_sorgente" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
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
                <label>{{ t('ui.admin.colonna_origine_campo') }}</label>
                <Select v-model="form.origine_campo" :options="origineCampoOptions"
                  option-label="label" option-value="value"
                  :disabled="delProgramma('origine_campo')"
                  :invalid="campiErrati.includes('origine_campo')"
                />
                <MotivoDelProgramma campo="origine_campo" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>

            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_etichetta') }}</label>
                <InputText v-model="form.etichetta"
                  :disabled="delProgramma('etichetta')" maxlength="120"
                  :invalid="campiErrati.includes('etichetta')"
                />
                <MotivoDelProgramma campo="etichetta" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_etichetta_i18n_key') }}</label>
                <InputText v-model="form.etichetta_i18n_key"
                  :disabled="delProgramma('etichetta_i18n_key')" maxlength="120"
                  :invalid="campiErrati.includes('etichetta_i18n_key')"
                />
                <MotivoDelProgramma campo="etichetta_i18n_key" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
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
              <InputText v-model="form.etichetta_estesa"
                :disabled="delProgramma('etichetta_estesa')" maxlength="200"
                :invalid="campiErrati.includes('etichetta_estesa')"
              />
              <MotivoDelProgramma campo="etichetta_estesa" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
            </div>

            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_tipo_colonna') }}</label>
                <Select
                  v-model="form.tipo_colonna"
                  :disabled="delProgramma('tipo_colonna')"
                  :options="tipoColonnaOptions"
                  option-label="label"
                  option-value="value"
                  :invalid="campiErrati.includes('tipo_colonna')"
                />
                <MotivoDelProgramma campo="tipo_colonna" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_tipo_dato') }}</label>
                <Select
                  v-model="form.tipo_dato"
                  :disabled="delProgramma('tipo_dato')"
                  :options="tipoDatoOptions"
                  option-label="label"
                  option-value="value"
                  :invalid="campiErrati.includes('tipo_dato')"
                />
                <MotivoDelProgramma campo="tipo_dato" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="comportamento">
          <div class="form-grid">
            <div class="form-grid-2col">
              <div class="form-field form-field-inline">
                <Checkbox v-model="form.filtrabile"
                  :disabled="isLineage || delProgramma('filtrabile')" binary input-id="ui-col-filtrabile" />
                <label for="ui-col-filtrabile">{{ t('ui.admin.colonna_filtrabile') }}</label>
                <MotivoDelProgramma campo="filtrabile" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field form-field-inline">
                <Checkbox v-model="form.ordinabile"
                  :disabled="isLineage || delProgramma('ordinabile')" binary input-id="ui-col-ordinabile" />
                <label for="ui-col-ordinabile">{{ t('ui.admin.colonna_ordinabile') }}</label>
                <MotivoDelProgramma campo="ordinabile" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>

            <div class="form-grid-2col">
              <div class="form-field form-field-inline">
                <Checkbox
                  v-model="form.esportabile"
                  binary
                  input-id="ui-col-esportabile"
                  :disabled="senzaCampo || delProgramma('esportabile')"
                  :invalid="campiErrati.includes('esportabile')"
                />
                <label for="ui-col-esportabile">{{ t('ui.admin.colonna_esportabile') }}</label>
                <MotivoDelProgramma campo="esportabile" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field form-field-inline">
                <Checkbox v-model="form.ricercabile_full"
                  :disabled="isLineage || delProgramma('ricercabile_full')" binary input-id="ui-col-ricercabile" />
                <label for="ui-col-ricercabile">{{ t('ui.admin.colonna_ricercabile_full') }}</label>
                <MotivoDelProgramma campo="ricercabile_full" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>
            <Message
              v-if="senzaCampo"
              severity="info"
              :closable="false"
              size="small"
            >
              {{ t('ui.admin.colonna_senza_campo_non_esportabile_hint') }}
            </Message>
            <Message
              v-if="isLineage"
              severity="info"
              :closable="false"
              size="small"
            >
              {{ t('ui.admin.colonna_lineage_solo_mostrata_hint') }}
            </Message>

            <div class="form-grid-2col">
              <div class="form-field form-field-inline">
                <Checkbox v-model="form.sensibile"
                  :disabled="delProgramma('sensibile')" binary input-id="ui-col-sensibile" />
                <label for="ui-col-sensibile">{{ t('ui.admin.colonna_sensibile') }}</label>
                <MotivoDelProgramma campo="sensibile" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field form-field-inline">
                <Checkbox v-model="form.attivo"
                  :disabled="delProgramma('attivo')" binary input-id="ui-col-attivo"
                  :invalid="campiErrati.includes('attivo')"
                />
                <label for="ui-col-attivo">{{ t('common.active') }}</label>
                <MotivoDelProgramma campo="attivo" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="layout">
          <div class="form-grid">
            <div class="form-grid-3col">
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_ordine_default') }}</label>
                <InputNumber v-model="form.ordine_default"
                  :disabled="delProgramma('ordine_default')" :min="1" :max="100000" show-buttons
                  :invalid="campiErrati.includes('ordine_default')"
                />
                <MotivoDelProgramma campo="ordine_default" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_larghezza_default') }}</label>
                <InputNumber v-model="form.larghezza_default"
                  :disabled="delProgramma('larghezza_default')" :min="1" :max="4000" show-buttons />
                <MotivoDelProgramma campo="larghezza_default" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_allineamento') }}</label>
                <Select
                  v-model="form.allineamento"
                  :disabled="delProgramma('allineamento')"
                  :options="allineamentoOptions"
                  option-label="label"
                  option-value="value"
                  :invalid="campiErrati.includes('allineamento')"
                />
                <MotivoDelProgramma campo="allineamento" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>

            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('ui.admin.colonna_formato') }}</label>
                <InputText v-model="form.formato"
                  :disabled="delProgramma('formato')" maxlength="60"
                  :invalid="campiErrati.includes('formato')"
                />
                <MotivoDelProgramma campo="formato" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
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
                <InputNumber v-model="form.gruppo_ordine"
                  :disabled="delProgramma('gruppo_ordine')" :min="1" :max="100000" show-buttons />
                <MotivoDelProgramma campo="gruppo_ordine" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
              </div>
            </div>

            <div class="form-field">
              <label>{{ t('ui.admin.colonna_gruppo') }}</label>
              <InputText v-model="form.gruppo"
                :disabled="delProgramma('gruppo')" maxlength="60"
                :invalid="campiErrati.includes('gruppo')"
              />
              <MotivoDelProgramma campo="gruppo" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </AppDrawer>
</template>

<style scoped>
.form-field-inline {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
</style>
