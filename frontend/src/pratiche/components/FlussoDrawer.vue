<script setup>
// Scopo: Drawer esecuzione flusso — avvio, completamento con esito, sospensione.
// Riutilizzabile: riceve flusso via props, emette eventi per refresh.
// Il contenuto e' dinamico: mostra azioni in base allo stato corrente del flusso.
import { ref, watch, computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { cambiaStatoFlusso } from '../api/pratiche-api'
import { completaApprovazioneFlusso } from '../../vendite/preventivi/api/preventiviApi'
import { DRAWER_WIDTH, STATO_FLUSSO } from '../../core/constants'

// Processo PREVENTIVI (percorso pratica-first): prefisso tipo_prestazione +
// codici template che abilitano il ramo preventivo/M2.
const TIPO_PREVENTIVI_PREFIX = 'PREVENTIVI'
const TEMPLATE_PREVENTIVAZIONE = 'PREVENTIVAZIONE'
const TEMPLATE_APPROVAZIONE_CLIENTE = 'APPROVAZIONE_CLIENTE'
import { statoFlussoSeverity, esitoFlussoSeverity } from '../../core/utils/severity'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import PraticaContextHeader from './PraticaContextHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  flusso: { type: Object, default: null },
  praticaId: { type: Number, default: null },
  // Codice tipo_prestazione della pratica: discrimina il routing PREVENTIVI
  // (es. APPROVAZIONE_CLIENTE → endpoint M2) da altri processi che riusano gli
  // stessi codici template (es. OFFERTA_QUADRO).
  tipoPrestazioneCodice: { type: String, default: '' },
  // Pratica in stato terminale (CHIUSA/ANNULLATA): sola lettura. Il flusso si
  // puo' consultare ma non avviare/completare e non si generano flussi a valle.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved', 'open-preventivo'])

// È un processo PREVENTIVI (pratica-first) → abilita il ramo preventivo/M2.
const isPreventivi = computed(
  () => (props.tipoPrestazioneCodice || '').startsWith(TIPO_PREVENTIVI_PREFIX)
)
const templateCodice = computed(() => props.flusso?.template_flusso_codice || '')

const esito = ref(null)
const noteEsito = ref('')

const esitiOptions = computed(() => [
  { value: 'POSITIVO', label: t('pratiche.esito_positivo') },
  { value: 'NEGATIVO', label: t('pratiche.esito_negativo') },
  { value: 'PARZIALE', label: t('pratiche.esito_parziale') },
  { value: 'NON_APPLICABILE', label: t('pratiche.esito_non_applicabile') },
])

const stato = computed(() => props.flusso?.stato_codice_interno || '')

// Sola lettura "effettiva": readonly da permessi operatore (iniettato dalla
// view via useReadonlyMode) OR pratica in stato terminale (prop readonly).
// Ri-fornito ai figli (DrawerTitle/ReadonlyBadge, DrawerActionsBar) come da
// convenzione useReadonlyMode, cosi' il badge "sola lettura" compare in alto e
// le azioni si disattivano in entrambi i casi.
const injectedReadonly = useInjectReadonly()
const effectiveReadonly = computed(() => injectedReadonly.value || props.readonly)
provide(READONLY_KEY, effectiveReadonly)

// Deferimento contenuto: il drawer ha solo Select statico + Textarea, ma
// applichiamo il pattern per coerenza con gli altri drawer entita'.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

watch(() => props.visible, (val) => {
  if (val) { esito.value = null; noteEsito.value = '' }
})

// Azioni della testata flusso consumate da DrawerActionsBar.
// Solo "Avvia" come azione semplice (DA_ESEGUIRE -> IN_CORSO). "Completa"
// resta inline come transizione con dati di processo (richiede esito
// obbligatorio + note opzionali, pattern feedback_dialog_cambio_stato_dati_processo).
const drawerActions = computed(() => {
  if (!props.flusso) return []
  return [
    {
      key: 'avvia',
      kind: 'state',
      label: t('pratiche.flusso_avvia'),
      icon: 'pi pi-play',
      severity: 'info',
      visible: !effectiveReadonly.value && stato.value === STATO_FLUSSO.DA_ESEGUIRE,
      disabled: loading.value,
      command: onAvvia,
    },
    // PREVENTIVAZIONE (pratica-first): apre il PreventivoDrawer collegato.
    // L'aggancio ROOT preventivo↔pratica avviene al salvataggio (gestito dal
    // parent, che ospita il drawer e chiama collega-pratica).
    {
      key: 'apri-preventivo',
      kind: 'secondary',
      label: t('pratiche.flusso_apri_preventivo'),
      icon: 'pi pi-file-edit',
      severity: 'secondary',
      visible: !effectiveReadonly.value && isPreventivi.value && templateCodice.value === TEMPLATE_PREVENTIVAZIONE,
      disabled: loading.value,
      command: () => emit('open-preventivo', props.praticaId),
    },
  ]
})

// Scopo: Avvia il flusso (DA_ESEGUIRE → IN_CORSO).
async function onAvvia() {
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, props.flusso.id, { nuovo_stato: 'IN_CORSO' }),
    { successMessage: t('pratiche.flusso_avviato') }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

// Scopo: Completa il flusso con esito obbligatorio.
// Routing M2 (§8.3): per APPROVAZIONE_CLIENTE di una pratica PREVENTIVI, il
// completamento guida l'accettazione del preventivo collegato → endpoint
// vendite dedicato (preventivo risolto a BE dal ROOT). Altri flussi: generico.
async function onCompleta() {
  if (!esito.value) return
  const isApprovazioneM2 =
    isPreventivi.value && templateCodice.value === TEMPLATE_APPROVAZIONE_CLIENTE
  const action = isApprovazioneM2
    ? () => completaApprovazioneFlusso({
        pratica_id: props.praticaId,
        flusso_id: props.flusso.id,
        esito: esito.value,
        note_esito: noteEsito.value || null,
      })
    : () => cambiaStatoFlusso(props.praticaId, props.flusso.id, {
        nuovo_stato: 'COMPLETATO',
        esito: esito.value,
        note_esito: noteEsito.value || null,
      })
  const result = await execute(action, { successMessage: t('pratiche.flusso_completato') })
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="t('pratiche.flusso_esecuzione')"
        :title="flusso?.template_flusso_codice || t('pratiche.flusso_generico')"
        icon="pi pi-sitemap"
      />
    </template>

    <div v-if="flusso" class="app-drawer-content" :class="{ 'app-readonly': effectiveReadonly }">
      <template v-if="contentReady">

      <!-- Header standard contesto pratica (BB PraticaContextHeader):
           numero pratica + soggetto + data apertura + id fiscale, identico
           su ogni drawer di esecuzione flusso. "Completa con esito" resta
           inline come transizione con dati di processo (form esito
           obbligatorio). -->
      <PraticaContextHeader
        :codice="flusso.pratica_codice"
        :pratica-id="flusso.pratica_id"
        :soggetto="flusso.pratica_soggetto_display"
        :data-apertura="flusso.pratica_data_apertura"
        :id-fiscale="flusso.pratica_soggetto_id_fiscale"
      >
        <template #status>
          <Tag :value="stato" :severity="statoFlussoSeverity(stato)" />
        </template>
      </PraticaContextHeader>

      <DrawerActionsBar :actions="drawerActions" />

      <!-- Info flusso: template descrittivo (codice gia' visibile nel titolo). -->
      <div v-if="flusso.template_flusso_descrizione" class="form-field">
        <label>{{ t('pratiche.flusso_col_template') }}</label>
        <span class="form-value">{{ flusso.template_flusso_descrizione }}</span>
      </div>

      <!-- IN_CORSO: Form completamento con esito.
           Resta inline (transizione con dati di processo, non comprimibile
           a `command: () => void` del BB DrawerActionsBar). -->
      <div v-if="stato === STATO_FLUSSO.IN_CORSO && !effectiveReadonly" class="flusso-actions">
        <h4>{{ t('pratiche.flusso_completa_con_esito') }}</h4>
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('pratiche.flusso_esito') }} *</label>
            <Select
              v-model="esito"
              :options="esitiOptions"
              option-label="label" option-value="value"
              class="w-full"
              :placeholder="t('pratiche.flusso_esito')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.flusso_note_esito') }}</label>
            <Textarea v-model="noteEsito" class="w-full" rows="3" auto-resize />
          </div>
        </div>
      </div>

      <!-- COMPLETATO: Mostra esito (readonly) -->
      <div v-if="stato === STATO_FLUSSO.COMPLETATO" class="form-grid mt-3">
        <div class="form-field">
          <label>{{ t('pratiche.flusso_esito') }}</label>
          <Tag :value="flusso.esito" :severity="esitoFlussoSeverity(flusso.esito)" />
        </div>
        <div v-if="flusso.note_esito" class="form-field">
          <label>{{ t('pratiche.flusso_note_esito') }}</label>
          <span class="form-value">{{ flusso.note_esito }}</span>
        </div>
      </div>

      <!-- Footer standard: in IN_CORSO il completamento esito usa il BB
           FormFooter (Annulla + Salva), niente pulsante Chiudi separato.
           Negli altri stati (Avvia in alto / COMPLETATO / sola lettura) resta
           il solo Chiudi. -->
      <FormFooter
        v-if="stato === STATO_FLUSSO.IN_CORSO && !effectiveReadonly"
        :loading="loading"
        :disabled="!esito"
        @save="onCompleta"
        @cancel="onClose"
      />
      <FormFooter v-else close-only @cancel="onClose" />
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.flusso-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.form-value {
  font-size: 0.9rem;
  color: var(--text-color);
}
</style>
