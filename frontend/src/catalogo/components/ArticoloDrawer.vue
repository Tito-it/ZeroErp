<script setup>
// Scopo: Drawer crea/modifica articolo.
//        Include combo conti contabili vendita/acquisto e auto-propose IVA da parameters.
//        In edit: riepilogo UoM/BoM/Note (e le sezioni contribuite: lotti) con pulsante "Gestisci" che apre sub-drawer dedicato.
//        ⭐ I LOTTI di magazzino (2026-09-21): la sezione compare solo se l'articolo
//        e' `gestito_a_magazzino` (un lotto ha senso su merce che movimenta); con
//        `requires_lotto` lo DICE. Il drawer vive in `src/magazzino` (Q-1 del piano
//        anagrafiche-fuori-dal-pannello-config: chi possiede il dato possiede il componente).
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useAuthStore } from '../../stores/auth'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useContatoreNote } from '../../core/composables/useContatoreNote'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { lookupArticoloUom, listArticoloComponenti, makeArticoloNotesApi, getArticoloFormDefaults } from '../api/catalogo'
import { DATE_FORMAT, DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { oggiAziendaleString, parseIsoDate, toDateString } from '../../core/utils/date'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import ActionBadge from '../../core/components/ActionBadge.vue'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import LookupSelect from '../../core/components/LookupSelect.vue'
import IvaSelect from '../../core/components/IvaSelect.vue'
import ContoContabileSelect from '../../core/components/ContoContabileSelect.vue'
import ArticoloUomDrawer from './ArticoloUomDrawer.vue'
import ArticoloBomDrawer from './ArticoloBomDrawer.vue'
import ArticoloNoteDrawer from './ArticoloNoteDrawer.vue'
import PuntoEstensione from '../../core/components/PuntoEstensione.vue'
import { PUNTI_ESTENSIONE, precaricaPunto } from '../../core/estensioni'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'

const { t } = useI18n()
const store = useArticoliStore()
const auth = useAuthStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  articoloId: { type: [String, null], default: null }
})

// I contributi al punto si caricano ora, non quando il punto si monta.
precaricaPunto(PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI)

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
// Modifiche non salvate: fotografia all'apertura (anche in creazione) e
// conferma se si chiude con modifiche (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Fase 5: lista campi immutabili dopo create. Arriva dal detail come metadata
// (`detail.non_editable_fields`, fonte = `dbops.vw_non_editable_fields` + gap
// Python su catalogo.articoli). Pilota i `:disabled` invece di cablare
// `isEdit` su singoli campi.
const nonEditableFields = computed(() => detail.value?.non_editable_fields || [])
function isFieldLocked(name) {
  if (correzioneStruttura.value && colonneStruttura.value.includes(name)) return false
  return isEdit.value && nonEditableFields.value.includes(name)
}

// Un articolo-ONERE e' un addebito, non un bene: non va a magazzino, non e'
// composito, non e' a lotti ne' a matricola. Lo rifiuta il guard del DB
// (`trgfn_articoli_guard_onere_natura`, `E_ARTICOLO_ONERE_STRUTTURA`, nessuna
// porta amministratore), e qui i quattro interruttori si spengono invece di
// lasciarli accendere per farsi rispondere. «E' un onere» lo dice il dettaglio
// (`e_onere` di `vw_articoli_dettaglio`, 20261103-53): la causale non e' in
// questo form, quindi in creazione un articolo non e' mai un onere.
// ⚠️ Spenti anche nella correzione di struttura: il guard non ha eccezioni.
const ONERE_SENZA = ['gestito_a_magazzino', 'is_composito', 'requires_lotto', 'requires_serial']
const eOnere = computed(() => detail.value?.e_onere === true)
// ⭐ Composito e solo componente si escludono: lo dice il CHECK
// `chk_articoli_composito_non_solo_componente` (brief-db-revisione-catalogo,
// BE10). Il form spegne l'interruttore dell'uno finche' l'altro e' acceso, cosi'
// l'operatore non arriva al rifiuto; nessun valore cambia da solo (un flag
// spento in silenzio potrebbe essere una colonna bloccata, e il PATCH tornerebbe
// rosso per un campo che l'operatore non ha toccato).
// ⚠️ E' una copia della regola del DB, voluta: giudica il form NON salvato,
// che il dettaglio non puo' descrivere. Il presidio che il CHECK c'e' ancora,
// col nome che il service traduce, e' `test_vincoli_catalogo_db` (BE, e2e).
const ESCLUSI = { is_composito: 'is_solo_componente', is_solo_componente: 'is_composito' }
function esclusoDallAltro(name) {
  return name in ESCLUSI && form.value[ESCLUSI[name]] === true
}
function isFieldDisabled(name) {
  return (eOnere.value && ONERE_SENZA.includes(name)) || esclusoDallAltro(name) || isFieldLocked(name)
}

// ⭐ La CORREZIONE DI STRUTTURA (A-10, Lotto 3u): un articolo usato non cambia
// la sua struttura, e la via normale e' un articolo nuovo. Per un errore di
// caricamento il SUPER_ADMIN ha una porta sola, il verbo
// `catalogo.fn_articolo_correggi_struttura`. Qui l'azione riapre i campi
// strutturali bloccati; al salvataggio quelli cambiati viaggiano nello STESSO
// PATCH (`correzione_struttura`), e il backend li scrive col verbo e poi
// l'UPDATE in una transazione (R-BE-1, 2026-10-18).
// ⭐ Quali campi riaprire lo dice il dettaglio (`struttura_correggibile`), dalla
// sede del DB da cui il verbo legge le colonne ammesse (R-DB-3): nessuna copia
// qui. La causale onere non e' in questo form.
const colonneStruttura = computed(() => detail.value?.struttura_correggibile || [])
const correzioneStruttura = ref(false)
const strutturaBloccata = computed(() =>
  colonneStruttura.value.some(c => nonEditableFields.value.includes(c)))

// Scopo: le colonne strutturali che l'amministratore ha cambiato rispetto al
// dettaglio caricato: le sole da mandare al verbo.
function campiStrutturaCambiati() {
  const campi = {}
  for (const c of colonneStruttura.value) {
    if (!(c in form.value)) continue
    if (form.value[c] !== detail.value?.[c]) campi[c] = form.value[c]
  }
  return campi
}
// I flag struttura arrivano nel `non_editable_fields` quando l'articolo
// partecipa a una BoM attiva (is_composito, is_solo_componente,
// requires_serial; migrations 20260522-02..04) e, da A-10
// (brief-db-articoli-ammessi-per-documento, 2026-10-13), quando e' USATO: le
// otto colonne strutturali (natura, tipologia di listino, causale onere,
// composito, solo componente, gestito a magazzino, lotto, seriale). Lock
// condizionali in `dbops.lock_columns_conditional` + `dbops.fn_non_editable_fields`.
// Single source of truth BE — nessuna logica locale FE: ogni campo che il DB
// puo' bloccare legge `isFieldLocked`. La causale onere non e' in questo form.

// Sub-drawer e riepilogo (edit mode)
const uomDrawerVisible = ref(false)
const uomRiepilogo = ref([])
const bomDrawerVisible = ref(false)
const bomRiepilogo = ref([])
const noteDrawerVisible = ref(false)
const noteRiepilogo = ref([])
// Il numero delle note sul pulsante «Gestisci note», come su ogni documento
// (BB `useContatoreNote`). Qui il dettaglio non porta i contatori: il numero
// e' il totale della lista del riepilogo, che si rilegge dopo ogni salvataggio.
const contatoreNote = useContatoreNote()

function defaultForm() {
  return {
    codice: '', descrizione: '', descrizione_breve: '',
    uom_id: null, tipo_voce_id: null, gruppo_voce_id: null,
    listino_tipologia_id: null, natura_vendita_id: null,
    spesa_id: null, iva_id: null,
    conto_contabile_vendita_id: null, conto_contabile_acquisto_id: null,
    is_composito: false, is_solo_componente: false,
    requires_serial: false,
    // Lotto 2 di magazzino (brief §4.9, M-5): «per lotti», deciso dall'articolo
    // come `requires_serial` — ⛔ ma FUORI dal lock BoM (nessun `isFieldLocked`).
    requires_lotto: false,
    // Blocco B (brief-db-modifiche-certe-ciclo-vendita-e-articolo): DA DOVE
    // arriva l'articolo. `modo_approvvigionamento_id` NOT NULL a DB con
    // DEFAULT ACQUISTO (null = «lascia decidere il default», come la natura);
    // `gestito_a_magazzino` fail-safe a false; `lead_time_giorni` null = non
    // si applica (una prestazione), e 0 NON e' «non si applica».
    modo_approvvigionamento_id: null,
    gestito_a_magazzino: false,
    lead_time_giorni: null,
    // Il ritiro (brief-db-articoli-obsoleto-dal): la data da cui l'articolo
    // non si sceglie piu' per una riga nuova. null = si sceglie. ⛔ Se e'
    // ritirato OGGI lo dice `detail.e_obsoleto` (il DB, alla data operativa):
    // qui non si confrontano date.
    obsoleto_dal: null,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  uomRiepilogo.value = []
  bomRiepilogo.value = []
  noteRiepilogo.value = []
  contatoreNote.azzera()
}

// Scopo: Carica riepilogo UoM operative. ⚠️ Dal lookup, che le da' TUTTE:
//        dal 2026-10-31 `listArticoloUom` e' la pagina della lista
//        `catalogo.articolo_uom`, e un riepilogo non si tronca alla prima.
async function loadUomRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await lookupArticoloUom(props.articoloId)
    const payload = res.data?.data
    uomRiepilogo.value = payload?.results || payload || []
  } catch { uomRiepilogo.value = [] }
}

// Scopo: Carica riepilogo componenti BoM.
async function loadBomRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await listArticoloComponenti(props.articoloId)
    const payload = res.data?.data
    const righe = payload?.results || payload || []
    const oggi = oggiAziendaleString()
    // Scopo: il riepilogo nel drawer articolo mostra le stesse righe
    // inizialmente visibili nel sub-drawer BoM: righe senza valido_al
    // oppure con valido_al maggiore/uguale a oggi.
    bomRiepilogo.value = righe
      .filter(r => !r.valido_al || r.valido_al >= oggi)
      .sort((a, b) => (a.componente_codice || '').localeCompare(b.componente_codice || ''))
  } catch { bomRiepilogo.value = [] }
}

// Scopo: Carica riepilogo note (preview prime 80 char in panel sezione).
//        Usa il BB partizionato `makeArticoloNotesApi` per coerenza col drawer
//        figlio `ArticoloNoteDrawer`. Refactor 2026-05-21 (Fase 2.B).
async function loadNoteRiepilogo() {
  if (!props.articoloId) return
  try {
    const res = await makeArticoloNotesApi(props.articoloId).listNote()
    const payload = res.data?.data
    noteRiepilogo.value = payload?.results || payload || []
    // Il totale della lista, non le righe di questa pagina.
    contatoreNote.aggiorna(typeof payload?.count === 'number' ? payload.count : noteRiepilogo.value.length)
  } catch {
    noteRiepilogo.value = []
    contatoreNote.azzera()
  }
}

async function loadDetail() {
  if (!props.articoloId) return
  const data = await store.fetchDetail(props.articoloId)
  if (!data) return
  detail.value = data
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    descrizione_breve: data.descrizione_breve || '',
    uom_id: data.uom_id,
    tipo_voce_id: data.tipo_voce_id,
    gruppo_voce_id: data.gruppo_voce_id,
    listino_tipologia_id: data.listino_tipologia_id,
    natura_vendita_id: data.natura_vendita_id,
    spesa_id: data.spesa_id,
    iva_id: data.iva_id,
    conto_contabile_vendita_id: data.conto_contabile_vendita_id,
    conto_contabile_acquisto_id: data.conto_contabile_acquisto_id,
    is_composito: data.is_composito || false,
    is_solo_componente: data.is_solo_componente || false,
    requires_serial: data.requires_serial || false,
    requires_lotto: data.requires_lotto || false,
    modo_approvvigionamento_id: data.modo_approvvigionamento_id,
    gestito_a_magazzino: data.gestito_a_magazzino || false,
    lead_time_giorni: data.lead_time_giorni ?? null,
    obsoleto_dal: parseIsoDate(data.obsoleto_dal),
  }
  fissa()
  correzioneStruttura.value = false
  // Carica riepilogo in parallelo
  await Promise.all([loadUomRiepilogo(), loadBomRiepilogo(), loadNoteRiepilogo()])
}

// Fase 8 (A5): defaults form articolo via endpoint dedicato
// /catalogo/articoli/form-defaults/. Tipi gia' castati lato BE.
async function applyFormDefaults() {
  try {
    const res = await getArticoloFormDefaults()
    const defaults = res.data?.data || {}
    if (defaults.default_iva_id != null) {
      form.value.iva_id = defaults.default_iva_id
    }
  } catch (err) {
    // Best-effort: in caso di errore l'utente compila manualmente.
    // Il warning console aiuta il debug senza disturbare l'utente.
    console.warn('[ArticoloDrawer] form-defaults non disponibili', err)
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return  // contentReady reset gestito da useDrawerContentReady
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
    await applyFormDefaults()
    // Dopo i default: l'IVA proposta non e' una modifica dell'operatore.
    fissa()
  }
})

const canSave = computed(() => {
  return form.value.codice?.trim() && form.value.descrizione?.trim() && form.value.uom_id != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    // uom_id e' immutabile dopo create (lock_columns DDL): non inviarlo mai in PATCH.
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      descrizione_breve: f.descrizione_breve?.trim() || null,
      tipo_voce_id: f.tipo_voce_id,
      gruppo_voce_id: f.gruppo_voce_id,
      listino_tipologia_id: f.listino_tipologia_id,
      // NOT NULL a DB: in EDIT il valore arriva sempre dal detail, mai null.
      natura_vendita_id: f.natura_vendita_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
      requires_lotto: f.requires_lotto,
      // NOT NULL a DB: in EDIT il valore arriva sempre dal detail, mai null.
      modo_approvvigionamento_id: f.modo_approvvigionamento_id,
      gestito_a_magazzino: f.gestito_a_magazzino,
      lead_time_giorni: f.lead_time_giorni,
      // Data svuotata = null = il ritiro si toglie.
      obsoleto_dal: toDateString(f.obsoleto_dal),
    }
    // La struttura cambiata viaggia nel PATCH: il backend la passa prima al
    // verbo dell'amministratore, poi aggiorna il resto (che porta gli stessi
    // valori), in una transazione. Un rifiuto annulla tutto.
    if (correzioneStruttura.value) {
      const campi = campiStrutturaCambiati()
      if (Object.keys(campi).length) payload.correzione_struttura = campi
    }
    const result = await execute(
      () => store.update(props.articoloId, payload),
      { successMessage: t('catalogo.articolo_salvato') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      codice: f.codice?.trim(),
      descrizione: f.descrizione?.trim(),
      descrizione_breve: f.descrizione_breve?.trim() || null,
      uom_id: f.uom_id,
      tipo_voce_id: f.tipo_voce_id,
      gruppo_voce_id: f.gruppo_voce_id,
      listino_tipologia_id: f.listino_tipologia_id,
      // NOT NULL a DB con DEFAULT MERCE: si invia solo se scelta esplicita
      // (null esplicito verrebbe rifiutato dal BE).
      ...(f.natura_vendita_id != null ? { natura_vendita_id: f.natura_vendita_id } : {}),
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
      requires_lotto: f.requires_lotto,
      // NOT NULL a DB con DEFAULT ACQUISTO: si invia solo se scelto esplicitamente.
      ...(f.modo_approvvigionamento_id != null
        ? { modo_approvvigionamento_id: f.modo_approvvigionamento_id } : {}),
      gestito_a_magazzino: f.gestito_a_magazzino,
      lead_time_giorni: f.lead_time_giorni,
      obsoleto_dal: toDateString(f.obsoleto_dal),
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('catalogo.articolo_creato') }
    )
    if (result !== null) { emit('saved', result); close() }
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}

// Fase 7: disattivazione/riattivazione come azione di dominio.
// L'`attivo` non passa piu' da PATCH: pulsanti dedicati con conferma
// e refresh detail al ritorno dall'API.
async function refreshAfterStateChange(result) {
  if (result === null) return
  detail.value = result
  emit('saved', result)
}

// Il campo «Ritirato dal», per portarci l'operatore quando il DB rifiuta lo
// spegnimento e indica il ritiro (vedi `portaAlRitiro`).
const campoRitiroRef = ref(null)

// Scopo: un articolo nominato da altre righe (distinte, documenti, listini)
//        non si spegne, si RITIRA (Q35 (c), Tid 2026-11-12): il DB rifiuta con
//        409 `E_ATTIVO_BLOCK_SI_RITIRA` e `fields: ['obsoleto_dal']`. Il campo
//        e' gia' rosso (`campiErrati`) e il toast dice la soluzione; qui si
//        porta lo sguardo e il fuoco sul campo, che sta piu' in basso del
//        pulsante appena premuto. ⛔ La data NON la sceglie il drawer: oggi o
//        un giorno futuro (ritiro programmato) e' una decisione di chi compila.
//        Il segnale e' il CAMPO nominato dall'errore, non il codice: e' il
//        contratto dell'envelope (`fields`), lo stesso che accende il rosso.
async function portaAlRitiro() {
  if (!campiErrati.value.includes('obsoleto_dal')) return
  await nextTick()
  const el = campoRitiroRef.value
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.querySelector('input')?.focus({ preventScroll: true })
}

function onConfirmDisattiva() {
  if (!detail.value) return
  confirmAction({
    header: t('catalogo.disattiva_dialog_titolo'),
    message: t('catalogo.disattiva_dialog_messaggio', { codice: detail.value.codice }),
    acceptLabel: t('catalogo.disattiva_articolo'),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => store.disattiva(props.articoloId),
        { successMessage: t('catalogo.articolo_disattivato') }
      )
      if (result === null) {
        await portaAlRitiro()
        return
      }
      await refreshAfterStateChange(result)
    }
  })
}

function onConfirmCorreggiStruttura() {
  if (!detail.value) return
  confirmAction({
    header: t('catalogo.correggi_struttura_dialog_titolo'),
    message: t('catalogo.correggi_struttura_dialog_messaggio', { codice: detail.value.codice }),
    acceptLabel: t('catalogo.correggi_struttura'),
    onAccept: () => { correzioneStruttura.value = true },
  })
}

function onConfirmRiattiva() {
  if (!detail.value) return
  confirmAction({
    header: t('catalogo.riattiva_dialog_titolo'),
    message: t('catalogo.riattiva_dialog_messaggio', { codice: detail.value.codice }),
    acceptLabel: t('catalogo.riattiva_articolo'),
    onAccept: async () => {
      const result = await execute(
        () => store.riattiva(props.articoloId),
        { successMessage: t('catalogo.articolo_riattivato') }
      )
      await refreshAfterStateChange(result)
    }
  })
}

// Azioni della testata articolo consumate da DrawerActionsBar (refactor
// UI drawer 2026-05-21, Fase 2.A). Solo state actions: Disattiva/Riattiva
// in alternativa esclusiva tramite `visible`. UoM/BoM/Note restano panel
// inline (pattern misto: state in alto + sub-entita' eterogenee panel).
// `hideWhenReadonly` rispetta il pattern degli altri drawer: in modalita'
// LETTURA le azioni di stato si nascondono.
const drawerActions = computed(() => {
  if (!isEdit.value || !detail.value) return []
  return [
    {
      key: 'disattiva',
      kind: 'state',
      label: t('catalogo.disattiva_articolo'),
      icon: MANAGE_ICONS.DISATTIVA,
      severity: 'danger',
      outlined: true,
      visible: detail.value.attivo === true,
      hideWhenReadonly: true,
      command: onConfirmDisattiva,
    },
    {
      key: 'riattiva',
      kind: 'state',
      label: t('catalogo.riattiva_articolo'),
      icon: MANAGE_ICONS.RIATTIVA,
      severity: 'success',
      visible: detail.value.attivo === false,
      hideWhenReadonly: true,
      command: onConfirmRiattiva,
    },
    {
      // Solo l'amministratore, e solo quando c'e' davvero una struttura
      // bloccata da riaprire. Il permesso lo ripete il verbo DB.
      key: 'correggi_struttura',
      kind: 'state',
      label: t('catalogo.correggi_struttura'),
      icon: MANAGE_ICONS.SBLOCCA,
      outlined: true,
      visible: auth.isSuperAdmin && strutturaBloccata.value && !correzioneStruttura.value,
      hideWhenReadonly: true,
      command: onConfirmCorreggiStruttura,
    },
  ]
})
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('catalogo.articolo')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >

    <!-- Refactor UI drawer 2026-05-21 (Fase 2.A): header info + barra
         azioni state in alto, simmetrici a contratti/preventivi.
         Tag stato a destra, Disattiva/Riattiva nel BB azioni; UoM/BoM/Note
         restano panel inline piu' sotto (pattern misto). -->
    <template v-if="isEdit && detail">
      <DrawerEntityHeader>
        <Tag :value="detail.codice" severity="secondary" />
        <template #status>
          <!-- Ritirato alla data operativa: lo dice il DB (`e_obsoleto`). -->
          <Tag v-if="detail.e_obsoleto" :value="t('catalogo.tag_ritirato')" severity="warn" />
          <AttivoTag :active="detail.attivo" />
        </template>
      </DrawerEntityHeader>

      <DrawerActionsBar :actions="drawerActions" />
      <small v-if="correzioneStruttura" class="app-field-hint">{{ t('catalogo.correggi_struttura_attiva') }}</small>
    </template>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('catalogo.field_codice') }} *</label>
        <InputText v-model="form.codice" class="app-codice-input" :disabled="isFieldLocked('codice')"
          :invalid="campiErrati.includes('codice')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_uom') }} *</label>
        <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
          :placeholder="t('catalogo.select_uom')" :disabled="isFieldLocked('uom_id')" />
      </div>
    </div>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('catalogo.field_descrizione') }} *</label>
        <InputText v-model="form.descrizione"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_descrizione_breve') }}</label>
        <InputText v-model="form.descrizione_breve" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_iva') }}</label>
        <IvaSelect v-model="form.iva_id" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('catalogo.field_tipologia') }}</label>
        <LookupSelect v-model="form.tipo_voce_id" rel="vendite.articoli_tipologie" :placeholder="t('catalogo.select_tipologia')" show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_gruppo') }}</label>
        <LookupSelect v-model="form.gruppo_voce_id" rel="vendite.articoli_gruppi" :placeholder="t('catalogo.select_gruppo')" show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_listino_tipologia') }}</label>
        <LookupSelect v-model="form.listino_tipologia_id" rel="config.listini_tipologie" :placeholder="t('catalogo.select_listino_tipologia')" show-clear
          :disabled="isFieldLocked('listino_tipologia_id')" />
        <small class="app-text-muted mt-025">{{ t('catalogo.hint_listino_tipologia') }}</small>
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_spesa') }}</label>
        <LookupSelect v-model="form.spesa_id" rel="vendite.articoli_spesa" :placeholder="t('catalogo.select_spesa')" show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_natura_vendita') }}</label>
        <!-- NOT NULL a DB (default MERCE): niente show-clear -->
        <LookupSelect v-model="form.natura_vendita_id" rel="config.nature_vendita" :placeholder="t('catalogo.select_natura_vendita')"
          :disabled="isFieldLocked('natura_vendita_id')" />
        <small class="app-text-muted mt-025">{{ t('catalogo.hint_natura_vendita') }}</small>
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('catalogo.field_conto_vendita') }}</label>
        <ContoContabileSelect v-model="form.conto_contabile_vendita_id" tipo="V" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_conto_acquisto') }}</label>
        <ContoContabileSelect v-model="form.conto_contabile_acquisto_id" tipo="A" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('catalogo.field_composito') }}</label>
        <ToggleSwitch v-model="form.is_composito"
          :disabled="isFieldDisabled('is_composito')" />
        <small v-if="eOnere" class="app-text-muted mt-025">{{ t('catalogo.hint_onere_struttura') }}</small>
        <small v-else-if="esclusoDallAltro('is_composito')" class="app-text-muted mt-025">{{ t('catalogo.hint_composito_solo_componente') }}</small>
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_solo_componente') }}</label>
        <ToggleSwitch v-model="form.is_solo_componente"
          :disabled="isFieldDisabled('is_solo_componente')" />
        <small v-if="esclusoDallAltro('is_solo_componente')" class="app-text-muted mt-025">{{ t('catalogo.hint_composito_solo_componente') }}</small>
      </div>
    </div>

    <!-- La GRANA del registro di magazzino, decisa dall'articolo (M-5): per
         seriale e/o per lotti, «o sempre o mai». `requires_serial` entra
         nel lock BoM; `requires_lotto` no (Lotto 1 §4.3: il lotto non entra
         nella distinta), ma da A-10 entrambi si fermano quando l'articolo e'
         USATO. Il lucchetto lo dice il DB in `non_editable_fields`: qui si
         legge e basta, per tutte le colonne che il DB puo' bloccare. -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('catalogo.field_requires_serial') }}</label>
        <ToggleSwitch v-model="form.requires_serial"
          :disabled="isFieldDisabled('requires_serial')" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_requires_lotto') }}</label>
        <ToggleSwitch v-model="form.requires_lotto"
          :disabled="isFieldDisabled('requires_lotto')" />
        <small class="app-text-muted mt-025">{{ t('catalogo.hint_requires_lotto') }}</small>
      </div>
    </div>

    <!-- Blocco B: da dove arriva l'articolo. Il modo e' un vocabolario
         (`config.modi_approvvigionamento`, come la natura di vendita):
         NOT NULL a DB, niente show-clear. `gestito_a_magazzino` e' una
         domanda DIVERSA dalla natura MERCE (una merce puo' essere venduta
         senza passare da giacenza). Il lead time e' in giorni, >= 0, e
         vuoto significa «non si applica». -->
    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('catalogo.field_modo_approvvigionamento') }}</label>
        <LookupSelect v-model="form.modo_approvvigionamento_id" rel="config.modi_approvvigionamento"
          :placeholder="t('catalogo.select_modo_approvvigionamento')" />
        <small class="app-text-muted mt-025">{{ t('catalogo.hint_modo_approvvigionamento') }}</small>
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_gestito_a_magazzino') }}</label>
        <ToggleSwitch v-model="form.gestito_a_magazzino"
          :disabled="isFieldDisabled('gestito_a_magazzino')" />
        <!-- Su un onere l'interruttore e' spento: qui, nella sua sezione, si
             dice perche' (la stessa frase sta sotto «composito»). -->
        <small class="app-text-muted mt-025">{{ t(eOnere ? 'catalogo.hint_onere_struttura' : 'catalogo.hint_gestito_a_magazzino') }}</small>
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_lead_time_giorni') }}</label>
        <InputNumber v-model="form.lead_time_giorni" :min="0" :use-grouping="false"
          :invalid="campiErrati.includes('lead_time_giorni')" />
      </div>
      <!-- Il ritiro: la data si mette e si toglie (il pulsante «Cancella» del
           calendario); togliendola l'articolo torna a scegliersi. -->
      <div ref="campoRitiroRef" class="form-field">
        <label>{{ t('catalogo.field_obsoleto_dal') }}</label>
        <DatePicker v-model="form.obsoleto_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar
          :invalid="campiErrati.includes('obsoleto_dal')" />
        <small class="app-text-muted mt-025">{{ t('catalogo.hint_obsoleto_dal') }}</small>
      </div>
    </div>
    <!-- Sezione: UoM riepilogo (edit mode) -->
    <template v-if="isEdit && detail">
      <div class="app-drawer-section"><h4>{{ t('catalogo.tab_uom') }}</h4></div>
      <div class="app-riepilogo-section">
        <div v-if="uomRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="u in uomRiepilogo" :key="u.id" class="app-riepilogo-item">
            <Tag v-if="u.is_base" :value="t('catalogo.tag_base')" severity="info" />
            <strong>{{ u.uom_codice }}</strong>
            <span class="app-riepilogo-detail">{{ u.uom_descrizione }}</span>
            <span v-if="u.factor_to_base != null && u.factor_to_base !== 1" class="app-riepilogo-detail">
              ({{ t('catalogo.col_fattore') }}: {{ u.factor_to_base }})
            </span>
          </div>
        </div>
        <div v-else class="app-riepilogo-empty">{{ t('catalogo.nessuna_uom') }}</div>
        <Button v-if="!isReadonly"
          :label="t('catalogo.gestisci_uom')" :icon="MANAGE_ICONS.UOM"
          text size="small" class="app-action-btn app-escape mt-025"
          @click="uomDrawerVisible = true" />
      </div>
    </template>

    <!-- Sezione: BoM riepilogo (edit mode). ⛔ La decide `puo_gestire_bom` del
         dettaglio (vw_articoli_dettaglio), non il `form.is_composito` non ancora
         salvato: il picker della distinta (`fn_articoli_ammessi`, ARTICOLO) su
         un padre che a DB non e' composito solleva E_ARTICOLO_NON_COMPOSITO
         (brief-db-revisione-catalogo, BE12). -->
    <template v-if="isEdit && detail?.puo_gestire_bom">
      <div class="app-drawer-section"><h4>{{ t('catalogo.tab_bom') }}</h4></div>
      <div class="app-riepilogo-section">
        <div v-if="bomRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="c in bomRiepilogo" :key="c.id" class="app-riepilogo-item">
            <strong>{{ c.componente_codice }}</strong>
            <span class="app-riepilogo-detail">{{ c.componente_descrizione }}</span>
            <span class="app-riepilogo-detail">(x{{ c.coeff_qta }})</span>
          </div>
        </div>
        <div v-else class="app-riepilogo-empty">{{ t('catalogo.nessun_componente') }}</div>
        <Button v-if="!isReadonly"
          :label="t('catalogo.gestisci_bom')" :icon="MANAGE_ICONS.BOM"
          text size="small" class="app-action-btn app-escape mt-025"
          @click="bomDrawerVisible = true" />
      </div>
    </template>

    <!-- Sezioni contribuite da altri domini (oggi: i lotti di magazzino).
         La scheda offre il punto, non sa chi ci contribuisce: ogni
         contributo decide da se' se mostrarsi (core/estensioni.js). -->
    <PuntoEstensione
      v-if="isEdit && detail"
      :punto="PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI"
      :articolo-id="props.articoloId"
      :articolo="form"
    />

    <!-- Sezione: Note riepilogo (edit mode) -->
    <template v-if="isEdit && detail">
      <div class="app-drawer-section"><h4>{{ t('catalogo.tab_note') }}</h4></div>
      <div class="app-riepilogo-section">
        <div v-if="noteRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="n in noteRiepilogo" :key="n.id" class="app-riepilogo-item">
            <span class="app-riepilogo-detail">{{ ((n.testo_md || n.testo) || '').substring(0, 80) }}{{ ((n.testo_md || n.testo) || '').length > 80 ? '...' : '' }}</span>
          </div>
        </div>
        <div v-else class="app-riepilogo-empty">{{ t('catalogo.nessuna_nota') }}</div>
        <!-- Il numero delle note sopra l'icona: l'involucro posizionato e
             `ActionBadge` sono quelli della barra azioni dei documenti. -->
        <span v-if="!isReadonly" class="app-action-tooltip-wrap mt-025">
          <Button
            :label="t('catalogo.gestisci_note')" :icon="MANAGE_ICONS.NOTE"
            text size="small" class="app-action-btn app-escape"
            @click="noteDrawerVisible = true" />
          <ActionBadge :valore="contatoreNote.badge.value" />
        </span>
      </div>
    </template>
  </AppDrawer>

  <!-- Sub-drawer UoM operative -->
  <ArticoloUomDrawer
    :visible="uomDrawerVisible"
    @update:visible="v => uomDrawerVisible = v"
    :articolo-id="props.articoloId"
    @saved="loadUomRiepilogo"
  />
  <!-- Sub-drawer Distinta Base -->
  <ArticoloBomDrawer
    :visible="bomDrawerVisible"
    @update:visible="v => bomDrawerVisible = v"
    :articolo-id="props.articoloId"
    @saved="loadBomRiepilogo"
  />
  <!-- Sub-drawer Note -->
  <ArticoloNoteDrawer
    :visible="noteDrawerVisible"
    @update:visible="v => noteDrawerVisible = v"
    :articolo-id="props.articoloId"
    @saved="loadNoteRiepilogo"
  />
</template>

