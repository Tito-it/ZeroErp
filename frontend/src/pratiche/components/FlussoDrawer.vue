<script setup>
// Scopo: Drawer esecuzione flusso — avvio, completamento con esito, sospensione.
// Riutilizzabile: riceve flusso via props, emette eventi per refresh.
// Il contenuto e' dinamico: mostra azioni in base allo stato corrente del flusso.
import { ref, shallowRef, markRaw, watch, computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { cambiaStatoFlusso } from '../api/pratiche-api'
import { useInjectTechnicalMode } from '../../core/composables/useTechnicalMode'
import { getUiActivity } from '../uiActivityRegistry'
import { getCompletionDialog } from '../flussoCompletionRegistry'
import { getDomainCompletion } from '../flussoDomainCompletionRegistry'
import { DRAWER_WIDTH, STATO_FLUSSO, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { statoFlussoSeverity, esitoFlussoSeverity } from '../../core/utils/severity'
import AppDrawer from '../../core/components/AppDrawer.vue'
import PraticaContextHeader from './PraticaContextHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FlussoAssegnaDialog from './FlussoAssegnaDialog.vue'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useLookupCodici } from '../../core/composables/useLookupCodici'

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

// Modifiche non salvate: il form esito e' spezzato su due ref, si raccolgono.
const formEsito = computed(() => ({ esito: esito.value, note_esito: noteEsito.value }))
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(formEsito, { visibile: () => props.visible })

// GUIDA (D4): step PROJECTION-DRIVEN = attende il verdetto di un documento
// (`template_attende_sorgente_tipo_id` non-null, esposto dal BE). Per questi
// «Accetta/Rifiuta» agisce sul DOCUMENTO e il milestone avanza da solo via
// trigger DB. Distingue i tipi già invertiti (cutover) da quelli con lo STESSO
// codice step ma ancora su handler (es. tipi deprecati): lì il flag è NULL →
// comportamento legacy (completamento flusso).
const projectionDriven = computed(() => props.flusso?.template_attende_sorgente_tipo_id != null)

// Flag modalita' tecnica (super-admin): default false = vista operatore. Fornito
// da PraticheDashboard (provideTechnicalMode, toggle gateato su auth.isSuperAdmin);
// qui riespone il "plumbing" (codice template).
const tecnico = useInjectTechnicalMode()

// Esiti data-driven dal vocabolario globale config.esiti_flussi_pratiche (§9.1-A):
// non piu' 4 valori hardcodati in i18n. Il Select offre SOLO i verdetti
// dell'operatore: il lookup espone `selezionabile_operatore` (derivato a BE da
// is_verdetto, verita' unica a DB) e gli esiti di RAMO calcolati dal dominio
// (es. bivio SMISTAMENTO) vengono filtrati qui; il guard BE
// (require_esito_selezionabile_operatore) resta la difesa in profondita'.
// value = codice_interno (inviato al BE), label = descrizione umana. Cache
// modulo-level condivisa (useGlobalLookup), caricata all'apertura del drawer.
const { items: esitiCatalogo, load: loadEsiti, loading: esitiLoading } = useLookupCodici('config.esiti_flussi_pratiche')
const esitiOptions = computed(() => {
  const base = esitiCatalogo.value
    .filter(e => e.selezionabile_operatore)
    .map(e => ({ value: e.codice_interno, label: e.descrizione }))
  // GUIDA (D4): per uno step PROJECTION-DRIVEN l'esito pilota una transizione del
  // DOCUMENTO (registry `esitoToStato`) → offri solo gli esiti mappati (es.
  // POSITIVO=Accetta / NEGATIVO=Rifiuta), non tutti i verdetti.
  const def = getCompletionDialog(props.flusso?.template_flusso_codice)
  if (projectionDriven.value && def?.docAction && def.esitoToStato) {
    const allowed = new Set(Object.keys(def.esitoToStato))
    return base.filter(o => allowed.has(o.value))
  }
  return base
})

const stato = computed(() => props.flusso?.stato_codice_interno || '')
// Descrizione umana dello stato (display field BE `stato_descrizione`): mostrata nel Tag.
// Il `stato` codice_interno resta per la logica (transizioni, visibilita' azioni, severity).
const statoDescrizione = computed(() => props.flusso?.stato_descrizione || stato.value)

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

// Step a completamento di DOMINIO (esito CALCOLATO dal BE, non scelto): il picker
// esito e' soppresso e il completamento passa da un'azione dedicata che chiama
// l'endpoint di dominio (registry per template_flusso_codice, import lazy). Es.
// SMISTAMENTO → MERCE_PRESENTE/SOLO_SERVIZI, il bivio che attiva o meno i flussi
// merce a valle (CONFERMA_ORDINE/INVIO_COMMESSA).
const domainCompletion = computed(() => getDomainCompletion(props.flusso?.template_flusso_codice))

// Azione di completamento di dominio: disponibile quando lo step e' completabile
// (IN_CORSO) — mirror della visibilita' del form esito generico, ma senza picker.
const showDomainComplete = computed(() =>
  !effectiveReadonly.value
  && !!domainCompletion.value
  && stato.value === STATO_FLUSSO.IN_CORSO
)

// Form esito visibile: completamento manuale su IN_CORSO (come oggi) OPPURE
// modalita CONTESTUALE su DA_ESEGUIRE (avvio+esito contestuale). SOPPRESSO per gli
// step a completamento di dominio (registry) E, fail-closed, per QUALSIASI step
// `modalita_esito === 'DOMINIO'` (companion FE-1.5): l'esito è calcolato, mai un
// verdetto scelto — così un DOMINIO senza entry registry non mostra mai il picker
// (che il guard DB id 504 rifiuterebbe).
const showEsitoForm = computed(() =>
  !effectiveReadonly.value
  && !domainCompletion.value
  && modalita.value !== 'DOMINIO'
  && (
    stato.value === STATO_FLUSSO.IN_CORSO
    || (stato.value === STATO_FLUSSO.DA_ESEGUIRE && modalita.value === 'CONTESTUALE')
  )
)

// Step DOMINIO completabile ma SENZA azione di completamento cablata nel registry
// FE: al posto del picker (soppresso) mostra un messaggio informativo — l'esito lo
// produce il processo di dominio, non l'operatore. Fail-closed leggibile invece di
// un form che porterebbe al 504.
const showEsitoDominioInfo = computed(() =>
  !effectiveReadonly.value
  && !domainCompletion.value
  && modalita.value === 'DOMINIO'
  && stato.value === STATO_FLUSSO.IN_CORSO
)

// Attività UI data-driven: il flusso porta `template_azione_ui_key` (catalogo DB
// pratiche.azioni_ui), risolta nel registry FE → drawer di dominio da aprire.
const uiActivity = computed(() => getUiActivity(props.flusso?.template_azione_ui_key))
// Gating cliente attivo: alcune attività (offerta/contratto) richiedono il BA.
// Il flusso espone il BA della pratica (colonna, D-9 di brief-db-istanza-nasce-col-ba;
// NULL = pratica di un altro ruolo, interna o con la sola istanza).
const hasActiveClient = computed(() => props.flusso?.pratica_billing_account_id != null)
const uiActivityVisible = computed(
  () => !effectiveReadonly.value
    && !!uiActivity.value
    && (!uiActivity.value.requiresActiveClient || hasActiveClient.value),
)

watch(() => props.visible, (val) => {
  if (val) {
    esito.value = null
    noteEsito.value = ''
    fissa()
    // Pre-seleziona l'esito_default (CONTESTUALE) SOLO se presente fra le
    // opzioni selezionabili caricate: un default fuori lista sarebbe un
    // valore invisibile a video ma inviato al BE (stessa classe di bug del
    // preset tipo in PraticaDrawer). Lookup fallito/vuoto → nessuna
    // preselezione, Select vuoto e "Salva" disabilitato (:disabled="!esito").
    // Guard `esito.value == null`: con cache fredda la promise risolve tardi
    // e NON deve sovrascrivere una scelta gia' fatta dall'operatore.
    loadEsiti()
      .then(() => {
        const def = esitoDefault.value
        if (esito.value == null && def && esitiOptions.value.some(o => o.value === def)) {
          // La preselezione e' del codice, non dell'operatore: la fotografia
          // la include — ma solo se l'operatore non ha gia' scritto le note
          // (fissare ora le assorbirebbe come «salvate»).
          const intatto = !modificato.value
          esito.value = def
          if (intatto) fissa()
        }
      })
      .catch(() => { /* errore gia' in errorRef del lookup */ })
  }
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
      icon: modalita.value === 'AUTOMATICO' ? MANAGE_ICONS.ESEGUI : MANAGE_ICONS.PLAY,
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
// Dialog di completamento (registry-driven): alcuni step richiedono dati di
// processo all'esito (es. APPROVAZIONE_CLIENTE/POSITIVO → modalita'+competenza
// di fatturazione). Il componente e' caricato lazy e reso inline; il suo payload
// viaggia come `meta` del completamento (FlussoDrawer resta generico).
const completionDialogVisible = ref(false)
const completionDialogComponent = shallowRef(null)
const completionDialogDef = computed(() =>
  getCompletionDialog(props.flusso?.template_flusso_codice),
)
// Drawer riusato per flussi diversi: al cambio flusso azzera la dialog cachata,
// così non resta montato il dialog di completamento del flusso precedente.
watch(() => props.flusso?.id, () => {
  completionDialogVisible.value = false
  completionDialogComponent.value = null
})

// Esegue il completamento; `meta` opzionale = contesto d'azione (es. accettazione).
async function _doComplete(meta = null) {
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, props.flusso.id, {
      nuovo_stato: 'COMPLETATO',
      esito: esito.value,
      note_esito: noteEsito.value || null,
      ...(meta ? { meta } : {}),
    }),
    { successMessage: t('pratiche.flusso_completato') },
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

// GUIDA (D4): step PROJECTION-DRIVEN → l'azione va sul DOCUMENTO (registry
// `docAction`), NON completa il flusso: il milestone avanza da solo via trigger
// DB. Idempotente/coerente col percorso standalone (stesso endpoint del drawer
// preventivo). `meta` = dati di processo del dialog (es. billing su accettazione).
async function _doDocAction(meta = null) {
  const def = completionDialogDef.value
  const result = await execute(
    () => def.docAction({ praticaId: props.praticaId, esito: esito.value, meta }),
    { successMessage: t('pratiche.flusso_completato') },
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

async function onCompleta() {
  if (!esito.value) return
  const def = completionDialogDef.value
  // Se l'esito richiede dati di processo (dialog registry) → raccoglili PRIMA
  // (vale sia per il completamento flusso legacy sia per l'azione documento).
  if (def && esito.value === def.esitoRichiesto) {
    if (!completionDialogComponent.value) {
      const mod = await def.loadComponent()
      completionDialogComponent.value = markRaw(mod.default)
    }
    completionDialogVisible.value = true
    return
  }
  // Step projection-driven senza dialog per questo esito (es. rifiuto) → azione
  // documento diretta. Altrimenti completamento flusso generico.
  if (projectionDriven.value && def?.docAction) await _doDocAction(null)
  else await _doComplete(null)
}

// Conferma della dialog: projection-driven → azione documento; legacy → meta del
// completamento flusso.
async function onCompletionConfirm(meta) {
  completionDialogVisible.value = false
  const def = completionDialogDef.value
  if (projectionDriven.value && def?.docAction) await _doDocAction(meta)
  else await _doComplete(meta)
}

// Completamento di DOMINIO: delega alla voce di registry (es. SMISTAMENTO →
// completa-smistamento), che calcola l'esito di ramo lato BE e verifica gli
// invarianti. Niente esito scelto qui: il picker e' soppresso.
async function onDomainComplete() {
  const entry = domainCompletion.value
  if (!entry) return
  const result = await execute(
    () => entry.complete({ praticaId: props.praticaId, flusso: props.flusso }),
    {
      successMessage: t('pratiche.flusso_completato'),
      errorMessage: t('pratiche.flusso_completa_dominio_errore'),
    },
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- Il footer segue lo stato del flusso: l'esito da registrare, il
       completamento di dominio (etichetta sua), oppure il solo «Chiudi». -->
  <AppDrawer
    :visible="props.visible"
    :title="flusso?.template_flusso_descrizione || t('pratiche.flusso_generico')"
    :icon="NAV_ICONS.PRATICHE"
    :action="t('pratiche.flusso_esecuzione')"
    :width="DRAWER_WIDTH.STANDARD"
    :readonly="effectiveReadonly"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="showEsitoForm || showDomainComplete ? 'form' : 'chiudi'"
    :loading="loading"
    :save-disabled="showEsitoForm && !esito"
    :save-label="!showEsitoForm && showDomainComplete ? t(domainCompletion.label) : null"
    @update:visible="(v) => emit('update:visible', v)"
    @save="showEsitoForm ? onCompleta() : onDomainComplete()"
  >
    <template v-if="flusso">

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
        <Tag :value="statoDescrizione" :severity="statoFlussoSeverity(stato)" />
      </template>
    </PraticaContextHeader>

    <DrawerActionsBar :actions="drawerActions" />

    <!-- La descrizione dell'attivita' e' gia' nel titolo del drawer: niente campo
         "Template" per l'operatore (era gergo di configurazione). In modalita'
         tecnica (super-admin) riespone codice + descrizione del template. -->
    <div v-if="tecnico" class="form-field">
      <label>{{ t('pratiche.flusso_col_template') }}</label>
      <span class="form-value">{{ flusso.template_flusso_codice }} — {{ flusso.template_flusso_descrizione }}</span>
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
            :placeholder="t('pratiche.flusso_esito')"
          />
          <!-- Lookup esiti fallito o vuoto: senza feedback l'operatore resta
               bloccato (Salva disabilitato) senza capire perche'. -->
          <small
            v-if="!esitiLoading && !esitiOptions.length"
            class="p-error"
          >
            {{ t('pratiche.flusso_esiti_non_disponibili') }}
          </small>
        </div>
        <div class="form-field">
          <label>{{ t('pratiche.flusso_note_esito') }}</label>
          <Textarea v-model="noteEsito" rows="3" auto-resize />
        </div>
      </div>
    </div>

    <!-- Completamento di DOMINIO (es. SMISTAMENTO): niente picker esito — il BE
         calcola l'esito di ramo dallo split gia' eseguito nel Pannello e completa
         lo step. Una sola azione conferma; il BE rifiuta se restano righe non
         smistate (residuo merce/servizi) con errore parlante. -->
    <div v-if="showDomainComplete" class="flusso-actions">
      <h4>{{ t(domainCompletion.label) }}</h4>
      <p class="flusso-domain-hint">{{ t('pratiche.flusso_completa_dominio_hint') }}</p>
    </div>

    <!-- Step DOMINIO senza azione di completamento cablata: niente picker
         verdetti (il DB lo rifiuterebbe) — solo un messaggio: l'esito lo
         produce il processo di dominio. -->
    <div v-else-if="showEsitoDominioInfo" class="flusso-actions">
      <p class="flusso-domain-hint">{{ t('pratiche.flusso_esito_dominio_senza_azione') }}</p>
    </div>

    <!-- COMPLETATO: Mostra esito (readonly) -->
    <div v-if="stato === STATO_FLUSSO.COMPLETATO" class="form-grid">
      <div class="form-field">
        <label>{{ t('pratiche.flusso_esito') }}</label>
        <Tag :value="flusso.esito_descrizione || flusso.esito" :severity="esitoFlussoSeverity(flusso.esito)" />
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
    </template>

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

    <!-- Dialog di completamento dinamica (registry): raccoglie i dati di processo
         dell'esito e li inoltra come `meta` del completamento flusso. -->
    <component
      :is="completionDialogComponent"
      v-if="completionDialogComponent"
      v-model:visible="completionDialogVisible"
      :readonly="effectiveReadonly"
      @confirm="onCompletionConfirm"
    />
  </AppDrawer>
</template>

<style scoped>
.flusso-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--app-border-color);
}

.flusso-domain-hint {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: var(--app-text-muted);
}

.form-value {
  font-size: 0.9rem;
  color: var(--app-text-color);
}
</style>
