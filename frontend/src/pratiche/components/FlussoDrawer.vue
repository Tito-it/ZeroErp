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
import { getUiActivity } from '../uiActivityRegistry'
import { DRAWER_WIDTH, STATO_FLUSSO, MANAGE_ICONS } from '../../core/constants'
import { statoFlussoSeverity, esitoFlussoSeverity } from '../../core/utils/severity'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import PraticaContextHeader from './PraticaContextHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FlussoAssegnaDialog from './FlussoAssegnaDialog.vue'
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
  // Pratica in stato terminale (CHIUSA/ANNULLATA): sola lettura. Il flusso si
  // puo' consultare ma non avviare/completare e non si generano flussi a valle.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved', 'open-attivita'])

const esito = ref(null)
const noteEsito = ref('')

const esitiOptions = computed(() => [
  { value: 'POSITIVO', label: t('pratiche.esito_positivo') },
  { value: 'NEGATIVO', label: t('pratiche.esito_negativo') },
  { value: 'PARZIALE', label: t('pratiche.esito_parziale') },
  { value: 'NON_APPLICABILE', label: t('pratiche.esito_non_applicabile') },
])

const stato = computed(() => props.flusso?.stato_codice_interno || '')

// Dialog di assegnazione (reparto + operatore). L'assegnazione ha senso finche'
// il flusso e' attivo: non su COMPLETATO/ANNULLATO ne' in sola lettura.
const assegnaVisible = ref(false)
const canAssign = computed(() =>
  !effectiveReadonly.value
  && !!props.flusso
  && stato.value !== STATO_FLUSSO.COMPLETATO
  && stato.value !== STATO_FLUSSO.ANNULLATO,
)

// Sola lettura "effettiva": readonly da permessi operatore (iniettato dalla
// view via useReadonlyMode) OR pratica in stato terminale (prop readonly).
// Ri-fornito ai figli (DrawerTitle/ReadonlyBadge, DrawerActionsBar) come da
// convenzione useReadonlyMode, cosi' il badge "sola lettura" compare in alto e
// le azioni si disattivano in entrambi i casi.
const injectedReadonly = useInjectReadonly()
const effectiveReadonly = computed(() => injectedReadonly.value || props.readonly)
provide(READONLY_KEY, effectiveReadonly)

// Configurazione esito dello step (20260617-01, esposta dal BE sul flusso):
//   MANUALE     = avvio poi form esito (comportamento storico);
//   AUTOMATICO  = un'azione "Avvia e completa" con esito_default (no scelta umana);
//   CONTESTUALE = avvio + esito in un'unica azione (form subito su DA_ESEGUIRE,
//                 esito_default pre-selezionato e modificabile).
const modalita = computed(() => props.flusso?.template_modalita_esito || 'MANUALE')
const esitoDefault = computed(() => props.flusso?.template_esito_default || null)

// Form esito visibile: completamento manuale su IN_CORSO (come oggi) OPPURE
// modalita CONTESTUALE su DA_ESEGUIRE (avvio+esito contestuale).
const showEsitoForm = computed(() =>
  !effectiveReadonly.value && (
    stato.value === STATO_FLUSSO.IN_CORSO
    || (stato.value === STATO_FLUSSO.DA_ESEGUIRE && modalita.value === 'CONTESTUALE')
  )
)

// Attività UI data-driven: il flusso porta `template_azione_ui_key` (catalogo DB
// pratiche.azioni_ui), risolta nel registry FE → drawer di dominio da aprire.
const uiActivity = computed(() => getUiActivity(props.flusso?.template_azione_ui_key))
// Gating cliente attivo: alcune attività (offerta/contratto) richiedono il BA.
// Il flusso espone il BA risolto della pratica (NULL = prospect).
const hasActiveClient = computed(() => props.flusso?.pratica_billing_account_id != null)
const uiActivityVisible = computed(
  () => !effectiveReadonly.value
    && !!uiActivity.value
    && (!uiActivity.value.requiresActiveClient || hasActiveClient.value),
)

// Deferimento contenuto: il drawer ha solo Select statico + Textarea, ma
// applichiamo il pattern per coerenza con gli altri drawer entita'.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

watch(() => props.visible, (val) => {
  // Pre-seleziona l'esito_default (CONTESTUALE) o resta null (MANUALE: esito_default
  // NULL → nessuna pre-selezione, comportamento odierno).
  if (val) { esito.value = esitoDefault.value; noteEsito.value = '' }
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
      // AUTOMATICO: un'unica azione "Avvia e completa" (il BE auto-completa con
      // esito_default). MANUALE: "Avvia" (poi form esito su IN_CORSO). CONTESTUALE
      // NON usa questo bottone: il form esito è già inline su DA_ESEGUIRE.
      label: modalita.value === 'AUTOMATICO'
        ? t('pratiche.flusso_avvia_e_completa')
        : t('pratiche.flusso_avvia'),
      icon: modalita.value === 'AUTOMATICO' ? 'pi pi-check' : 'pi pi-play',
      severity: 'info',
      visible: !effectiveReadonly.value
        && stato.value === STATO_FLUSSO.DA_ESEGUIRE
        && modalita.value !== 'CONTESTUALE',
      disabled: loading.value,
      command: onAvvia,
    },
    // Attività UI di dominio (data-driven): se il template del flusso dichiara
    // un'azione UI (azione_ui_key), apre il drawer di dominio risolto dal registry.
    // kind:'manage' = apertura sub-drawer → inline su desktop, nel kebab solo su
    // schermo piccolo (è l'azione principale dello step). Label/icona dal registry.
    {
      key: 'apri-attivita',
      kind: 'manage',
      label: uiActivity.value ? t(uiActivity.value.label) : '',
      icon: uiActivity.value?.icon,
      visible: uiActivityVisible.value,
      disabled: loading.value,
      command: () => emit('open-attivita', {
        key: props.flusso.template_azione_ui_key,
        praticaId: props.praticaId,
        // Aggancio per-flusso: qui il flusso esiste gia' (lo stiamo guardando) →
        // passiamo il suo id (l'host non lo ri-crea) e il template (per uniformita'
        // col percorso). Senza questi l'host proverebbe a creare il flusso con
        // template vuoto → E_FLUSSO_VALIDATION.
        flussoId: props.flusso.id,
        templateFlussoId: props.flusso.template_flusso_id,
        // Contesto cliente risolto dalla pratica (esposto sul flusso dal BE):
        // il documento aperto eredita+blocca istanza (+ BA se cliente attivo).
        billingAccountId: props.flusso.pratica_billing_account_id ?? null,
        istanzaUtilityId: props.flusso.pratica_istanza_utility_id ?? null,
      }),
    },
    // Assegnazione del flusso a un reparto e/o operatore (policy reparto-first).
    // kind:'manage' = apre il dialog dedicato. Disponibile finche' il flusso e'
    // attivo (non COMPLETATO/ANNULLATO) e non in sola lettura. `action` gatea sul
    // permesso di processo `assegna_pratica` (stesso codename del POST BE): chi
    // non lo possiede non vede il pulsante, invece di scoprire il 403 al click.
    {
      key: 'assegna',
      kind: 'manage',
      label: t('pratiche.flusso_assegna'),
      icon: MANAGE_ICONS.ASSIGN,
      action: 'assegna_pratica',
      visible: canAssign.value,
      disabled: loading.value,
      command: () => { assegnaVisible.value = true },
    },
  ]
})

// Scopo: Avvia il flusso (DA_ESEGUIRE → IN_CORSO). Per modalita AUTOMATICO il BE
// auto-completa nella stessa richiesta → il messaggio rispecchia il completamento.
async function onAvvia() {
  const isAuto = modalita.value === 'AUTOMATICO'
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, props.flusso.id, { nuovo_stato: 'IN_CORSO' }),
    { successMessage: isAuto ? t('pratiche.flusso_completato') : t('pratiche.flusso_avviato') }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

// Scopo: Completa il flusso con esito obbligatorio (completamento GENERICO).
// Le azioni di dominio al completamento (es. accettazione del preventivo per
// APPROVAZIONE_CLIENTE) sono ora SERVER-SIDE e data-driven: il motore pratiche
// le esegue dai binding pratiche.template_flussi_handler_eventi nella stessa
// transazione. Niente più routing M2 / endpoint dedicato nel FE.
async function onCompleta() {
  if (!esito.value) return
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, props.flusso.id, {
      nuovo_stato: 'COMPLETATO',
      esito: esito.value,
      note_esito: noteEsito.value || null,
    }),
    { successMessage: t('pratiche.flusso_completato') },
  )
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

      <!-- Assegnazione corrente del flusso (reparto + operatore), display fields
           dal BE. Mostrata solo se almeno uno valorizzato. -->
      <div v-if="flusso.unita_organizzativa_descrizione || flusso.risorsa_umana_display"
           class="form-grid-2col">
        <div v-if="flusso.unita_organizzativa_descrizione" class="form-field">
          <label>{{ t('pratiche.flusso_reparto') }}</label>
          <span class="form-value">{{ flusso.unita_organizzativa_descrizione }}</span>
        </div>
        <div v-if="flusso.risorsa_umana_display" class="form-field">
          <label>{{ t('pratiche.flusso_assegnatario') }}</label>
          <span class="form-value">{{ flusso.risorsa_umana_display }}</span>
        </div>
      </div>

      <!-- Form esito inline: completamento manuale su IN_CORSO oppure modalita
           CONTESTUALE su DA_ESEGUIRE (avvio+esito in un'unica azione). Resta inline
           (transizione con dati di processo, non comprimibile a `command` del BB). -->
      <div v-if="showEsitoForm" class="flusso-actions">
        <h4>{{ stato === STATO_FLUSSO.DA_ESEGUIRE
          ? t('pratiche.flusso_avvia_e_registra_esito')
          : t('pratiche.flusso_completa_con_esito') }}</h4>
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
        v-if="showEsitoForm"
        :loading="loading"
        :disabled="!esito"
        @save="onCompleta"
        @cancel="onClose"
      />
      <FormFooter v-else close-only @cancel="onClose" />
      </template>
    </div>

    <!-- Dialog assegnazione: reparto + operatore del reparto. Su saved chiude il
         drawer (emit saved) → il parent ricarica percorso/coda/lista. -->
    <FlussoAssegnaDialog
      v-if="flusso"
      v-model:visible="assegnaVisible"
      :pratica-id="praticaId"
      :flusso-id="flusso.id"
      :current-risorsa-id="flusso.risorsa_umana_id"
      :current-unita-id="flusso.unita_organizzativa_id"
      @saved="() => { emit('saved'); emit('update:visible', false) }"
    />
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
