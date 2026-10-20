<script setup>
// Scopo: Drawer autonomo di GOVERNO della commessa (cockpit fatturazione,
//        Fase A-4 — brief-be-fe-processi-fatturazione). Complementare al
//        CommessaDrawer lineage (sola lettura): qui l'operatore ESERCITA i
//        processi — approvazione righe (A-1, per selezione o tutte), azioni
//        di stato utente da capabilities data-driven, azioni prezzo N5/N7/
//        sblocco per riga — e consulta contatori + genealogia (Passaggi).
//        Nessuna logica di dominio: testata/righe/guard vivono nel DB/BE,
//        la view invoca e rende (fail-visible sugli errori parlanti).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import AppDialog from '../../core/components/AppDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import CommessaRegistroDialog from './CommessaRegistroDialog.vue'
import DocumentoCollegamentiBar from '../_shared/lineage/DocumentoCollegamentiBar.vue'
import DocumentoAnnulloLegamiDialog from '../_shared/annullo/DocumentoAnnulloLegamiDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import { useSelezioneToggle } from '../../core/composables/useSelezioneToggle'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { lookupRisorseUmane } from '../../core/apiCore'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import DocumentoDrawerHost from '../../core/components/DocumentoDrawerHost.vue'
import { DOCUMENTO_DRAWER_TIPI } from '../../core/drawerEntita'
import { useDocumentoDrawer } from '../../core/composables/useDocumentoDrawer'
import { buildApriDocumentoAction } from '../dashboardAree'
import {
  STATO_APPROVAZIONE_ATTIVITA,
  STATO_COMMESSA,
  STATO_EMISSIONE_ATTIVITA,
  TIPO_MOVIMENTO_ATTIVITA,
} from '../constants'
import { useCommesseStore } from '../stores/commesse'
import { displayDate, toDateString } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { extractApiError } from '../../core/utils/apiError'
import {
  statoApprovazioneAttivitaSeverity,
  statoCommessaSeverity,
  statoEmissioneAttivitaSeverity,
} from '../../core/utils/severity'
import {
  aggiungiOnereCommessa,
  annullaRigaCommessa,
  approvaCommessaAttivita,
  exportCommessaAttivita,
  getCommessaStato,
  listCommessaAttivita,
  riallineaPrezzoAttivita,
  sbloccaPrezzoAttivita,
  updateCommessaTestata,
  variazionePrezzoAttivita,
} from '../api/commesse'
import { lookupArticoli } from '../../catalogo/api/catalogo'
import { MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { useListaDrawerPaginata } from '../../core/composables/useListaDrawerPaginata'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  commessaId: { type: [Number, null], default: null },
  // Ispezione pura (feedback_drawer_readonly): nasconde ogni azione.
  readonly: { type: Boolean, default: false },
  // Filtro stato emissione PREIMPOSTATO dal chiamante: la lista si apre sullo
  // stesso stato della card da cui si arriva (Fatturate → EMESSA, Da emettere
  // → NON_EMESSA), cosi' il valore mostrato dalla card e il contenuto della
  // lista raccontano la stessa cosa. Chi apre la commessa dalla lista generica
  // non lo passa e vede tutte le righe.
  // ⚠️ E' un DEFAULT, non un vincolo: il filtro resta visibile e azzerabile
  // (vedi il Select in toolbar). Nasconderlo produrrebbe una lista di una riga
  // senza spiegazione — la stessa confusione che questo filtro esiste per
  // togliere, solo piu' difficile da diagnosticare.
  statoEmissione: { type: [String, null], default: null },
})

const emit = defineEmits(['update:visible', 'saved'])
const { t, te } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

// Readonly effettivo: area in LETTURA (inject) o prop di ispezione.
const parentReadonly = useInjectReadonly()
const isReadonly = computed(() => parentReadonly.value || props.readonly)
// Gate azione di processo (L2): senza permesso i pulsanti Approva spariscono.
const { isAllowed: canApprovare } = useActionPermission('approva_attivita_commessa')
// Gate unico dell'approvazione (readonly + permesso): un solo predicato per
// toolbar e colonna checkbox — mai due copie che possono divergere.
const canApprova = computed(() => !isReadonly.value && canApprovare.value)
// Gate azioni prezzo N5/N7 (specchio del `post_permission` sugli endpoint:
// senza il permesso il kebab non le propone invece di farle fallire in 403).
const { isAllowed: canPrezzo } = useActionPermission('prezzo_override_manuale')
// Gate della porta oneri: lo STESSO codename autorizza il caricamento di una
// voce manuale e il suo annullamento (decisione Tid §5 del brief) — chi puo'
// caricare puo' disfare, nessun permesso dedicato.
const { isAllowed: canVoceManuale } = useActionPermission('carica_voce_manuale')
// Gate di STATO commessa per le azioni prezzo (specchio di
// `_assert_commessa_modificabile` lato BE, data-driven su
// stati_commessa.modificabile): su CHIUSA/ANNULLATA il kebab non propone
// azioni che il BE rifiuterebbe. Fail-closed: capabilities non ancora
// caricate ⇒ nessuna azione.
const canEditRighe = computed(() => capabilities.value.can_edit_righe === true)

// ------------------------------------------------------------------ stato
const stato = ref(null)
const selected = ref([])
// Filtro stato emissione applicato alla lista: parte dalla prop (card di
// provenienza) ed e' modificabile a video. null = tutte.
const filtroStatoEmissione = ref(props.statoEmissione)
// Filtro natura della riga (changeSet 20260820-09). null = tutti i movimenti.
// Non arriva da nessuna prop: nasce sempre vuoto, perche' nessuna card di
// provenienza parla di movimenti.
const filtroTipoMovimento = ref(null)

// ⭐ La lista delle righe: pagina, ordinamento, dimensione pagina e preset dal
//    BB delle liste in drawer (regola del 2, 2026-09-30) — la stessa macchina
//    era scritta qui a mano, e aveva gia' preso una strada sua (partiva dalla
//    misura di pagina, non da quella compatta di un drawer). Il drawer tiene
//    solo cio' che e' suo: i due filtri e la selezione.
// ⚠️ L'ordinamento e' server-side: l'ORDER BY vive dentro
//    fn_list_commessa_attivita (whitelist chiusa), `null` = ordine storico per
//    id (removable-sort riporta qui).
// ⚠️ Il totale e' il `count` FILTRATO della risposta, non
//    `stato.total_attivita` (contatore di testata, sempre su TUTTE le righe):
//    con un filtro attivo il paginatore direbbe 4 righe mostrandone 1.
const lista = useListaDrawerPaginata(({ page, pageSize, sortBy, sortDir }) =>
  listCommessaAttivita(props.commessaId, {
    limit: pageSize,
    offset: (page - 1) * pageSize,
    ...(sortBy ? { order_by: sortBy, order_dir: sortDir } : {}),
    ...(filtroStatoEmissione.value ? { stato_emissione: filtroStatoEmissione.value } : {}),
    ...(filtroTipoMovimento.value ? { tipo_movimento: filtroTipoMovimento.value } : {}),
  }))
const righe = lista.righe

const capabilities = computed(() => stato.value?.capabilities ?? {})

// Contatori testata (fn_get_commessa_stato): chip di sintesi del funnel.
const contatori = computed(() => {
  const s = stato.value ?? {}
  return [
    { key: 'attivita', label: t('vendite.commesse.tot_attivita'), value: s.total_attivita ?? 0, severity: 'secondary' },
    { key: 'da_approvare', label: t('vendite.commesse.tot_da_approvare'), value: s.total_non_approvate ?? 0, severity: (s.total_non_approvate ?? 0) > 0 ? 'warn' : 'secondary' },
    { key: 'approvate', label: t('vendite.commesse.tot_approvate'), value: s.total_approvate ?? 0, severity: 'success' },
    { key: 'emesse', label: t('vendite.commesse.tot_emesse'), value: s.total_emesse ?? 0, severity: 'info' },
    { key: 'da_riallineare', label: t('vendite.commesse.tot_da_riallineare'), value: s.total_prezzo_da_riallineare ?? 0, severity: (s.total_prezzo_da_riallineare ?? 0) > 0 ? 'warn' : 'secondary' },
  ]
})

// Selezione: solo le righe ancora approvabili (BOZZA + NON_EMESSA).
const righeApprovabili = computed(() =>
  righe.value.filter(
    (r) => r.stato_approvazione === STATO_APPROVAZIONE_ATTIVITA.BOZZA
      && r.stato_emissione === STATO_EMISSIONE_ATTIVITA.NON_EMESSA,
  ),
)
// ⛔ La terna «in pagina», non `toggleAll`/`anySelected`. Questa lista e'
//    paginata LATO SERVER (una fetch a ogni cambio pagina) e il BB della lista
//    NON azzera la selezione: si compone attraverso le pagine, di proposito.
//    Fino al 2026-08-27 qui c'era `toggleAll`, che SOSTITUISCE la selezione con
//    la pagina corrente — spuntare «tutte» a pagina 2 buttava via quanto
//    spuntato a pagina 1, in silenzio. Vedi il blocco in fondo a
//    `useSelezioneToggle`.
const {
  isSelectable, isSelected, toggleRow,
  allInPagina: allSelected,
  anyInPagina: anySelected,
  toggleAllInPagina: toggleAll,
} = useSelezioneToggle({ selected, selezionabili: righeApprovabili })

// ------------------------------------------------------------------ load
// Scopo: carica testata+capabilities; 404/fuori scope RLS → toast + chiusura.
async function loadStato() {
  const res = await loadDetailOrClose(() => getCommessaStato(props.commessaId))
  if (res == null) return false
  stato.value = res.data?.data ?? null
  return true
}

// Scopo: ricarica completa post-azione (testata + righe, selezione azzerata).
async function reloadAll() {
  selected.value = []
  if (await loadStato()) await lista.carica()
}

// ------------------------------------------------------------------ testata leggibile
// Blocco C di brief-db-modifiche-certe-ciclo-vendita-e-articolo: la commessa
// aveva `codice` e nient'altro di parlante. `descrizione` e `responsabile`
// si scrivono (PATCH /commesse/<id>/), `data_apertura` e' in sola lettura —
// la mette il default alla nascita. Nessun guard di stato: il DB non ne
// mette, di proposito (la descrizione di una commessa chiusa si corregge).
const testataForm = ref({ descrizione: '', responsabile_risorsa_umana_id: null })
const testataSaving = ref(false)
// ⚠️ `stato` si ricarica da MOLTI punti (apertura, approva riga, prezzi,
//    cambio stato: ogni `reloadAll`), e il watch qui sotto SOSTITUISCE il
//    form. Senza il BB, una descrizione digitata e non ancora salvata
//    sparirebbe al primo «Approva» su una riga — in silenzio, ed e' il difetto
//    per cui `useDrawerFormPreserve` esiste. La baseline si azzera all'apertura
//    (sotto, nel watch su `visible`/`commessaId`), o il non-salvato della
//    commessa precedente finirebbe su quella nuova.
// Il form e' «sporco» solo se differisce da cio' che il server ha detto: il
// pulsante Salva si accende su una modifica vera, non sull'apertura. La
// risposta e' quella della fotografia del BB, che la dice anche alla tab.
const {
  preserva: preservaTestata,
  reset: resetTestata,
  modificato: testataDirty,
  chiudiConConferma,
} = useDrawerFormPreserve(testataForm, { visibile: () => props.visible })

// Scopo: allinea il form alla testata caricata (a ogni `loadStato`),
//        ripristinando cio' che l'operatore aveva cambiato e non salvato.
watch(stato, (s) => {
  const applica = preservaTestata()
  testataForm.value = {
    descrizione: s?.descrizione ?? '',
    responsabile_risorsa_umana_id: s?.responsabile_risorsa_umana_id ?? null,
  }
  applica()
})

// Le risorse umane ATTIVE (lookup cross-dominio, cache condivisa per chiave).
// Caricate solo quando il campo e' scrivibile: in sola lettura basta il nome
// che il dettaglio porta gia' (`responsabile_display`).
const {
  items: responsabiliAttive,
  loading: responsabiliLoading,
  loaded: responsabiliCaricate,
  load: loadResponsabili,
} = useGlobalLookup('anagrafiche.risorse_umane', () => lookupRisorseUmane())
watch(
  () => [props.visible, isReadonly.value],
  ([visible, readonly]) => {
    if (visible && !readonly) loadResponsabili().catch(() => {})
  },
  { immediate: true },
)
// ⚠️ Il responsabile ATTUALE puo' essere una persona poi disattivata: non sta
//    piu' fra le attive, ma spegnere il select senza dirlo mostrerebbe un
//    campo vuoto su un'assegnazione che esiste. Si aggiunge come voce
//    NON selezionabile, col suo nome, finche' resta assegnata.
// ⛔ «Non e' fra le attive» si puo' dire SOLO a lookup caricato: `items` parte
//    vuoto, e in sola lettura il lookup non si carica affatto — senza il
//    guard su `loaded`, una persona attiva comparirebbe come «non piu'
//    attiva» finche' la lista non arriva (e per sempre in consultazione).
//    Prima di allora la voce e' il solo nome, dal dettaglio.
const responsabiliOptions = computed(() => {
  const attive = responsabiliAttive.value ?? []
  const attualeId = stato.value?.responsabile_risorsa_umana_id ?? null
  if (attualeId == null || attive.some((r) => r.id === attualeId)) return attive
  const nome = stato.value?.responsabile_display ?? `#${attualeId}`
  const nonAttivo = responsabiliCaricate.value
  return [
    {
      id: attualeId,
      display: nonAttivo ? t('vendite.commesse.responsabile_non_attivo', { nome }) : nome,
      attivo: !nonAttivo,
    },
    ...attive,
  ]
})

// Scopo: salva la testata (PATCH parziale) e riallinea il dettaglio con la
//        risposta, che e' lo stesso payload di `/stato/`.
async function salvaTestata() {
  if (!testataDirty.value) return
  testataSaving.value = true
  try {
    const res = await execute(() => updateCommessaTestata(props.commessaId, {
      descrizione: (testataForm.value.descrizione || '').trim() || null,
      responsabile_risorsa_umana_id: testataForm.value.responsabile_risorsa_umana_id ?? null,
    }), { successMessage: t('vendite.commesse.testata_salvata') })
    if (res !== null) {
      stato.value = res ?? stato.value
      emit('saved')
    }
  } finally {
    testataSaving.value = false
  }
}

watch(
  () => [props.visible, props.commessaId],
  async ([visible]) => {
    if (!visible || !props.commessaId) return
    stato.value = null
    // Baseline del form di testata azzerata PRIMA che `stato` cambi: il
    // non-salvato di un'altra commessa non deve sopravvivere alla riapertura.
    resetTestata()
    lista.reset()
    // Il filtro torna al default del chiamante a ogni apertura: riaprendo la
    // stessa commessa da una card diversa deve valere la card nuova, non
    // quella di prima.
    filtroStatoEmissione.value = props.statoEmissione
    filtroTipoMovimento.value = null
    selected.value = []
    await reloadAll()
  },
  { immediate: true },
)

// Host del drawer documento (origine o fattura) aperto dal kebab di riga.
// ⚠️ Alla chiusura si ricarica: dal drawer della fattura o dell'ordine
// l'operatore può aver fatto avanzare il documento, e la riga che lo ha
// aperto sarebbe stantia.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumentoDrawer,
  onVisibleChange: onDocDrawerVisible,
} = useDocumentoDrawer(() => reloadAll())

// Ref alla lista configurabile (per il modale «personalizza», raggiungibile
// dal drawer tramite l'azione dedicata sotto).
const listaRef = ref(null)

// Azioni di lista (personalizza colonne + esporta): lo stesso BB delle 37 viste
// standard e dei tre cruscotti, cosi' questa lista non puo' divergere da loro.
// ⚠️ `useListaAzioni` e non `useListaConfigurabilePage`: quest'ultimo e'
// costruito su `useSearchTable` e pretende uno store con la forma «ricerca
// testuale + sort + limit». Qui le righe sono pilotate dal drawer (commessa,
// filtri di stato e movimento, paginazione propria), esattamente il caso per
// cui il BB e' stato estratto.
// ⭐ L'export riceve gli STESSI filtri e lo STESSO ordinamento della lista a
// video: il file E' la lista, non una seconda query che le somiglia.
const {
  dirty, exportDialogVisible, exportLoading, onExportConfirm, azioniLista,
} = useListaAzioni(() => listaRef.value, {
  exportFn: (params) => exportCommessaAttivita(props.commessaId, params),
  getExportParams: (formato) => ({
    formato,
    ...(filtroStatoEmissione.value ? { stato_emissione: filtroStatoEmissione.value } : {}),
    ...(filtroTipoMovimento.value ? { tipo_movimento: filtroTipoMovimento.value } : {}),
    ...(lista.sortField.value
      ? { order_by: lista.sortField.value, order_dir: lista.sortOrder.value === -1 ? 'desc' : 'asc' }
      : {}),
  }),
})

// Opzioni del filtro stato emissione: i tre valori del dominio + «tutte»
// (null). Derivate dalla costante, non riscritte a mano.
const opzioniStatoEmissione = computed(() => [
  { value: null, label: t('vendite.commesse.filtro_stato_tutte') },
  ...Object.values(STATO_EMISSIONE_ATTIVITA).map((v) => ({
    value: v,
    label: t(`vendite.commesse.stato_emissione_${v.toLowerCase()}`),
  })),
])

// Opzioni del filtro movimento: i tre valori del dominio + «tutti» (null).
// Derivate dalla costante, come le gemelle dello stato emissione.
const opzioniTipoMovimento = computed(() => [
  { value: null, label: t('vendite.commesse.filtro_movimento_tutti') },
  ...Object.values(TIPO_MOVIMENTO_ATTIVITA).map((v) => ({
    value: v,
    label: t(`vendite.commesse.tipo_movimento_${v.toLowerCase()}`),
  })),
])

// Scopo: cambio filtro stato → si riparte da pagina 1 (l'offset corrente
//        apparterrebbe a un insieme di righe diverso) e si azzera la
//        selezione, che potrebbe contenere righe ora fuori filtro.
function onFiltroStatoChange() {
  lista.page.value = 1
  selected.value = []
  lista.carica()
}

// ------------------------------------------------------------------ approva (A-1)
// Scopo: approvazione con conferma; righeIds null = tutte (fn idempotente).

// Scopo: il nome dello STATO di destinazione per la frase di conferma («Portare
//   il documento nello stato {stato}?»). La descrizione leggibile la sa solo il
//   database (`DRAFT` -> «Bozza», `ALLOCATO` -> «Allocato a magazzino»: non e'
//   derivabile dal codice), quindi arriva dalla capability come
//   `target_state_descrizione`. Finche' il DB non la espone si ripiega sulla
//   label dell'azione — comportamento invariato, nessun testo mancante.
function statoDestinazione(action) {
  return action.target_state_descrizione || t(action.label_key)
}

function approva(righeIds) {
  const n = righeIds ? righeIds.length : (stato.value?.total_non_approvate ?? 0)
  confirmAction({
    header: t('vendite.commesse.approva_header'),
    message: t('vendite.commesse.approva_conferma', { n }),
    onAccept: async () => {
      const res = await execute(() => approvaCommessaAttivita(props.commessaId, righeIds))
      if (res !== null) {
        notify.success(t('vendite.commesse.approva_esito', { n: res?.approvate ?? 0 }))
        await reloadAll()
        emit('saved')
      }
    },
  })
}

// ------------------------------------------------------------------ porta oneri
// Riga di puro valore sulla commessa (qta=1, causale+IVA dall'articolo-onere).
// Il presidio e' all'ingresso: senza `carica_voce_manuale` l'azione non compare
// (gate nativo di DrawerActionsBar via `action`), e il BE la rifiuta comunque.
const onereDialog = ref(false)
const onereArticoli = ref([])
const onereArticoliLoading = ref(false)
const onereForm = ref({
  articoloOnereId: null,
  importo: null,
  tipoDocFiscaleId: null,
  motivo: '',
  dataAttivita: null,
})

// Scopo: carica gli articoli-onere del catalogo (uno per causale: pochi, si
//        presentano come tendina e non come autocomplete).
async function loadArticoliOnere() {
  if (onereArticoli.value.length) return
  onereArticoliLoading.value = true
  try {
    const res = await lookupArticoli({ solo_oneri: true, limit: 50 })
    onereArticoli.value = res.data?.data?.results ?? []
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    onereArticoliLoading.value = false
  }
}

// Scopo: apre il dialog azzerando il form (mai residui del giro precedente).
async function apriOnere() {
  onereForm.value = {
    articoloOnereId: null,
    importo: null,
    tipoDocFiscaleId: null,
    motivo: '',
    dataAttivita: null,
  }
  onereDialog.value = true
  await loadArticoliOnere()
}

const onereValido = computed(() =>
  !!onereForm.value.articoloOnereId
  && onereForm.value.importo != null
  && onereForm.value.importo > 0
  && !!onereForm.value.tipoDocFiscaleId)

// Scopo: carica l'onere; la riga nasce APPROVATA e compare subito in lista.
async function salvaOnere() {
  const f = onereForm.value
  const res = await execute(() => aggiungiOnereCommessa(props.commessaId, {
    articoloOnereId: f.articoloOnereId,
    importo: f.importo,
    tipoDocFiscaleId: f.tipoDocFiscaleId,
    motivo: f.motivo,
    dataAttivita: f.dataAttivita ? toDateString(f.dataAttivita) : null,
  }))
  if (res !== null) {
    onereDialog.value = false
    notify.success(t('vendite.commesse.onere_esito'))
    await reloadAll()
    emit('saved')
  }
}

// ------------------------------------------------------------------ stato (capabilities)
// Azioni di stato utente dal blob capabilities (transizioni manuali).
// `permission`: chiudi/annulla portano la commessa in uno stato TERMINALE
// irreversibile (esce per sempre dal giro di fatturazione) → dal 2026-07-27
// l'endpoint esige `cambia_stato_commessa` e qui il gate FE nasconde i pulsanti
// a chi non ha l'azione, invece di farlo scoprire con un 403. Un solo codename
// per i tre verbi: il permesso gatta l'endpoint, non la singola transizione.
const stateActions = computed(() => mapAvailableActionsToDrawerActions({
  availableActions: capabilities.value.available_actions ?? [],
  t,
  te,
  readonly: isReadonly,
  permission: 'cambia_stato_commessa',
  onAction: (action) => {
    confirmAction({
      header: t('vendite.commesse.stato_header'),
      message: t('vendite.commesse.stato_conferma', { stato: statoDestinazione(action) }),
      onAccept: () => eseguiCambioStato(action.target_state),
    })
  },
}))

// ⭐ L'annullo e' un gesto CONFERMABILE (brief-db-annullo-a-valle-riapre-a-
//    monte D-2): con righe non ancora emesse il DB lo rifiuta
//    (`confirm_and_retry`) finche' chi conferma non dichiara quanti legami ha
//    visto — che cosa si riapre a monte (documenti, reso, consumi) e che cosa
//    si annulla (oneri) lo porta a video `DocumentoAnnulloLegamiDialog`, la
//    stessa finestra di bolla, ordine, preventivo e contratto. Le righe gia'
//    emesse lo vietano prima della domanda (azione spenta col motivo, e il
//    verbo rifiuta comunque). Le altre transizioni restano su `execute`.
const cambioStato = useForzaturaConfermata()
const { richiestaConferma: domandaAnnullo } = cambioStato
const commesseStore = useCommesseStore()

// Scopo: esegue l'azione di stato; l'annullo SEMPRE senza dichiarazione al
//        primo tentativo.
async function eseguiCambioStato(targetState) {
  const res = targetState === STATO_COMMESSA.ANNULLATA
    ? await cambioStato.esegui(
      (dichiarazione) => commesseStore.cambiaStato(props.commessaId, targetState, dichiarazione),
    )
    : await execute(() => commesseStore.cambiaStato(props.commessaId, targetState))
  if (res !== null) await dopoCambioStato()
}

// Scopo: l'operatore ha visto i legami e conferma l'annullo: si ripete la
//        chiamata DICHIARANDO quanti erano.
async function onConfermaAnnullo(dichiarazione) {
  const res = await cambioStato.conferma(dichiarazione)
  if (res !== null) await dopoCambioStato()
}

async function dopoCambioStato() {
  await reloadAll()
  emit('saved')
}

// ------------------------------------------------------------------ prezzi (N5/N7)
const variazioneDialog = ref(false)
const variazioneRiga = ref(null)
const variazionePrezzo = ref(null)
const variazioneMotivo = ref('')

// Sblocco (N7-sblocco): il BE esige motivo obbligatorio, quindi dialog (non
// più solo confirm) — stesso pattern della variazione.
const sbloccaDialog = ref(false)
const sbloccaRiga = ref(null)
const sbloccaMotivo = ref('')

// Scopo: kebab riga — array UNICO con i gate sulle singole voci; il guard vero
//        (riga fatturata, commessa non modificabile, riga non manuale) resta al
//        BE (fail-visible).
//
// ⚠️ Niente early-return sui permessi (G10 del brief annullamento): il
// preambolo `if (!canPrezzo) return []` rendeva l'intero kebab invisibile a chi
// ha `carica_voce_manuale` ma NON `prezzo_override_manuale` — cioe' esattamente
// il destinatario dell'annullamento riga. I gate stanno sulle voci, non sulla
// funzione: due permessi diversi non possono condividere una sola porta.
// Restano condizioni comuni solo quelle che valgono per QUALUNQUE azione di
// riga: ispezione pura e commessa non piu' modificabile.
// Scopo: le due azioni di NAVIGAZIONE della riga — «apri il documento da cui
//        arriva» e «apri la fattura in cui è finita». Separate da
//        `buildRowActions` perché non sono azioni di modifica: valgono anche
//        in sola lettura e su riga già fatturata, dove tutte le azioni prezzo
//        sono legittimamente spente. Guardare un documento non è un'azione di
//        governo.
//        Le tre colonne che le alimentano (dal 2026-10-21 `sorgente_apribile`
//        + `sorgente_codice_interno`, prima `sorgente_area`,
//        `sorgente_documento_id`, `fattura_id`) arrivano dalla lista dal
//        2026-08-16 (changeSet 20260816-04): prima si fermavano al database.
// ─────────────────────────────────────────────────────────────────────────
// REGISTRO DI RIGA: «perché questa riga è così».
// ⭐ Fino al 2026-08-28 la risposta esisteva solo nel database: sei tipi di
//    evento scritti su `commesse_attivita_log` e nessuna schermata che li
//    leggesse. Trovato in collaudo — una riga passata ad ANNULLATA da sé e
//    nessun modo di sapere perché.
// ⚠️ L'azione è di SOLA LETTURA e resta disponibile anche in readonly: sta in
//    `buildRowNavActions`, insieme alle altre due che navigano e non scrivono.
//    Metterla fra le azioni di modifica l'avrebbe nascosta proprio a chi guarda
//    una commessa che non può toccare — cioè nel caso in cui serve di più.
const registroVisible = ref(false)
const registroRigaId = ref(null)

function apriRegistroRiga(rigaId) {
  registroRigaId.value = rigaId
  registroVisible.value = true
}

function buildRowNavActions(row) {
  return [
    {
      key: 'registro',
      label: t('vendite.commesse.azione_registro'),
      icon: MANAGE_ICONS.GIORNALE,
      command: () => apriRegistroRiga(row.id),
    },
    // Documento di ORIGINE: stesso BB del Backlog fatturazione, stessa
    // meccanica area → drawer. L'azione si nasconde da sé quando l'id è
    // nullo, che copre due casi diversi e ugualmente corretti: la voce
    // manuale (nessun documento a monte) e il documento non visibile a chi
    // guarda (RLS) — in entrambi non c'è nulla da aprire.
    // ⭐ Il tipo è il codice IMMUTABILE della sorgente, e vale solo se il DB
    //    dice che il documento ha una pagina (`sorgente_apribile`, fattura e
    //    reso compresi): brief-db-grammatica-unica-documenti §13.6, 2026-10-21.
    //    Fino al 2026-10-20 era il plurale `sorgente_area`, ritirato.
    buildApriDocumentoAction({
      area: row.sorgente_apribile ? row.sorgente_codice_interno : null,
      documentoId: row.sorgente_documento_id,
      label: t('vendite.commesse.azione_apri_sorgente'),
      onApri: apriDocumentoDrawer,
    }),
    {
      key: 'apri_fattura',
      // L'etichetta porta il NUMERO quando c'è: una fattura non ancora
      // numerata non ne ha, e inventarne uno sarebbe peggio che ometterlo.
      label: row.fattura_numero
        ? t('vendite.commesse.azione_apri_fattura_numerata', { numero: row.fattura_numero })
        : t('vendite.commesse.azione_apri_fattura'),
      // Icona di NAVIGAZIONE delle fatture, la stessa del menu: chi la vede
      // sa già dove sta per andare. Non se ne inventa una nuova qui.
      icon: NAV_ICONS.FATTURE,
      // ⚠️ `fattura_id`, non `fatturata`: il flag resta true anche per chi non
      // vede la fattura (è calcolato su una tabella senza RLS), e proporre
      // un'apertura che non può funzionare è peggio che non proporla.
      visible: row.fattura_id != null,
      command: () => apriDocumentoDrawer(DOCUMENTO_DRAWER_TIPI.FATTURA, row.fattura_id),
    },
  ]
}

function buildRowActions(row) {
  if (isReadonly.value || !canEditRighe.value) return buildRowNavActions(row)
  // Riga fatturata: nessuna azione prezzo (le tre sono tutte rifiutate dal
  // guard BE `_assert_non_fatturata`). `fatturata` = EXISTS di un'AF con
  // fattura_riga_id valorizzato, esposta dalla lista (changeset 20260724-07):
  // specchio esatto del guard, non `stato_emissione` (che resta EMESSA anche
  // dopo un reset-lotto che ha reso il prezzo di nuovo modificabile).
  // ⭐ Il prezzo di una RETTIFICA e' immutabile: e' copiato dalla riga di fattura
  // che rettifica, e cambiarlo farebbe accreditare un importo diverso da quello
  // fatturato. Le tre azioni prezzo non si mostrano proprio.
  // ⚠️ `visible: false` e non `disabled`, per la regola di frontend-standards:
  // il permesso NASCONDE, lo stato DISABILITA col motivo — e questa non e' ne'
  // l'uno ne' l'altro. E' l'IDENTITA' della riga, che non cambiera' mai: una
  // voce grigia per sempre e' una promessa che non si mantiene, ed e' lo stesso
  // criterio del `sorgente_tipo_id === null` qui sotto.
  // ⛔ Il gate NON sostituisce le guardie vere: il presidio BE
  // (`_assert_prezzo_modificabile`) e soprattutto il trigger
  // `trgfn_commesse_attivita_guard_prezzo_rettifica` sulla tabella restano dove
  // sono. Qui si smette solo di proporre una porta chiusa.
  const eRettifica = row.tipo_movimento === TIPO_MOVIMENTO_ATTIVITA.RETTIFICA
  const prezzoOk = canPrezzo.value && !row.fatturata && !eRettifica
  return [
    {
      key: 'riallinea',
      label: t('vendite.commesse.azione_riallinea'),
      icon: MANAGE_ICONS.RIALLINEA,
      visible: prezzoOk && !row.prezzo_bloccato,
      command: () => riallinea(row, false),
    },
    {
      // DEC-3: la variazione eccezionale è vietata su prezzo bloccato — prima
      // si sblocca (con motivo). Specchio del guard BE E-BE-1.
      key: 'variazione',
      label: t('vendite.commesse.azione_variazione'),
      icon: MANAGE_ICONS.EDIT,
      visible: prezzoOk && !row.prezzo_bloccato,
      command: () => {
        variazioneRiga.value = row
        variazionePrezzo.value = null
        variazioneMotivo.value = ''
        variazioneDialog.value = true
      },
    },
    {
      // Icona-azione (chiave, `SBLOCCA`) distinta dalla spia-STATO della colonna
      // prezzo (`STATUS_ICONS.BLOCCATO`): il bottone inline icon-only non deve
      // leggersi come uno stato «aperto».
      key: 'sblocca',
      label: t('vendite.commesse.azione_sblocca'),
      icon: MANAGE_ICONS.SBLOCCA,
      visible: prezzoOk && row.prezzo_bloccato === true,
      command: () => sblocca(row),
    },
    {
      // Annullamento riga MANUALE: solo righe sourceless e non ancora emesse
      // (specchio esatto dei guard BE/DB). `sorgente_tipo_id === null` e' il
      // discriminante di «manuale» — non `segment_key LIKE 'MAN:%'` (i prefissi
      // sono una convenzione di leggibilita', non un contratto) ne'
      // `tipo_movimento = 'ONERE'` (natura, non origine: il CHECK ammette gia'
      // RETTIFICA). La label dice «voce manuale» e non «riga» per non
      // confondersi con «Annulla commessa» della barra azioni, a due centimetri
      // di distanza e di tutt'altra portata.
      key: 'annulla-riga',
      label: t('vendite.commesse.azione_annulla_riga'),
      icon: MANAGE_ICONS.ANNULLA,
      severity: 'danger',
      // ⚠️ `sourceless` NON basta piu' a dire «manuale»: dal cantiere note di
      // credito anche una RETTIFICA nasce senza sorgente (`fn_accredita_riga_
      // reso` la scrive con la coppia `sorgente_*` a NULL). Serve anche la
      // NATURA — specchio del perimetro della madre, changeSet 20260820-10,
      // che rifiuta con E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE.
      // ⭐ Una rettifica si disfa con «Annulla l'accredito» sulla riga del reso:
      // quella e' la strada, e questa azione non deve nemmeno somigliarle.
      visible: canVoceManuale.value
        && row.sorgente_tipo_id === null
        && row.tipo_movimento === TIPO_MOVIMENTO_ATTIVITA.ONERE
        && row.stato_emissione === STATO_EMISSIONE_ATTIVITA.NON_EMESSA,
      command: () => apriAnnullaRiga(row),
    },
    // Navigazione in coda: prima si governa la riga, poi si va a vedere da
    // dove viene e dove è finita.
    ...buildRowNavActions(row),
  ]
}

// Scopo: N5 — al primo giro senza conferma; se il BE segnala versione listino
//        cambiata (richiede_conferma) chiede conferma esplicita e ripete.
async function riallinea(row, conferma) {
  const res = await execute(() =>
    riallineaPrezzoAttivita(props.commessaId, row.id, { confermaVersioneDiversa: conferma }))
  if (res === null) return
  if (res.richiede_conferma && !conferma) {
    confirmAction({
      header: t('vendite.commesse.riallinea_header'),
      message: t('vendite.commesse.riallinea_versione_diversa'),
      onAccept: () => riallinea(row, true),
    })
    return
  }
  notify.success(t('vendite.commesse.riallinea_esito'))
  await reloadAll()
  emit('saved')
}

// Scopo: N7 — salva variazione eccezionale (prezzo+motivo obbligatori).
async function salvaVariazione() {
  const res = await execute(() =>
    variazionePrezzoAttivita(props.commessaId, variazioneRiga.value.id, {
      prezzo: variazionePrezzo.value,
      motivo: variazioneMotivo.value,
    }))
  if (res !== null) {
    variazioneDialog.value = false
    notify.success(t('vendite.commesse.variazione_esito'))
    await reloadAll()
    emit('saved')
  }
}

const variazioneValida = computed(() =>
  variazionePrezzo.value !== null && String(variazioneMotivo.value ?? '').trim().length > 0)

// Scopo: N7-sblocco — apre il dialog motivo (motivo obbligatorio lato BE).
function sblocca(row) {
  sbloccaRiga.value = row
  sbloccaMotivo.value = ''
  sbloccaDialog.value = true
}

const sbloccaValido = computed(() =>
  String(sbloccaMotivo.value ?? '').trim().length > 0)

// Scopo: N7-sblocco — rimuove il blocco e ricalcola dal resolver (motivo obbligatorio).
async function salvaSblocco() {
  const res = await execute(() =>
    sbloccaPrezzoAttivita(props.commessaId, sbloccaRiga.value.id, { motivo: sbloccaMotivo.value }))
  if (res !== null) {
    sbloccaDialog.value = false
    notify.success(t('vendite.commesse.sblocca_esito'))
    await reloadAll()
    emit('saved')
  }
}

// ------------------------------------------------------------------ annullamento riga manuale
// La riga non si cancella: passa ad ANNULLATA (tag rosso gia' mappato in
// STATO_EMISSIONE_ATTIVITA_MAP) e sparisce dalle porte verso fattura e cockpit.
// Dialog e non semplice conferma: il motivo e' obbligatorio (BE + madre DB) ed
// e' l'unica traccia del PERCHE' — stesso pattern della variazione prezzo.
const annullaRigaDialog = ref(false)
const annullaRigaRiga = ref(null)
const annullaRigaMotivo = ref('')

// Scopo: apre il dialog azzerando il motivo (mai residui del giro precedente).
function apriAnnullaRiga(row) {
  annullaRigaRiga.value = row
  annullaRigaMotivo.value = ''
  annullaRigaDialog.value = true
}

const annullaRigaValido = computed(() =>
  String(annullaRigaMotivo.value ?? '').trim().length > 0)

// Scopo: annulla la riga manuale; al successo ricarica testata (i contatori
//        escludono le annullate) e righe.
async function salvaAnnullaRiga() {
  const res = await execute(() =>
    annullaRigaCommessa(props.commessaId, annullaRigaRiga.value.id, {
      motivo: annullaRigaMotivo.value,
    }))
  if (res !== null) {
    annullaRigaDialog.value = false
    notify.success(t('vendite.commesse.annulla_riga_esito'))
    await reloadAll()
    emit('saved')
  }
}

const selectedIds = computed(() => selected.value.map((r) => r.id))

// Barra azioni del drawer: porta oneri + transizioni di stato. `action` fa da
// gate permesso e `hideWhenReadonly` da gate ispezione (logica in DrawerActionsBar,
// che applica anche `app-escape` — i pannelli-azione vivono in contenuto readonly).
const drawerActions = computed(() => [
  {
    key: 'aggiungi-onere',
    kind: 'primary',
    label: t('vendite.commesse.onere_azione'),
    icon: MANAGE_ICONS.ADD,
    tooltip: t('vendite.commesse.onere_tooltip'),
    action: 'carica_voce_manuale',
    hideWhenReadonly: true,
    command: apriOnere,
  },
  ...stateActions.value,
])

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoVariazione = useFotografiaDialog(() => ({ prezzo: variazionePrezzo.value, motivo: variazioneMotivo.value }), { visibile: () => variazioneDialog.value })

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoSblocca = useFotografiaDialog(() => ({ motivo: sbloccaMotivo.value }), { visibile: () => sbloccaDialog.value })

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoAnnullaRiga = useFotografiaDialog(() => ({ motivo: annullaRigaMotivo.value }), { visibile: () => annullaRigaDialog.value })

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoOnere = useFotografiaDialog(() => ({ ...onereForm.value }), { visibile: () => onereDialog.value })
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.commesse.gestione_titolo')"
    :icon="MANAGE_ICONS.COMMESSA"
    :width="DRAWER_WIDTH.XLARGE"
    :proteggi-corpo="false"
    :readonly="isReadonly"
    :modificato="testataDirty"
    :conferma-uscita="chiudiConConferma"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <DrawerEntityHeader v-if="stato">
      <!-- Codice COMMESSA (E-DB-4): correla il drawer alla lista, che mostra
           commessa_codice; fallback a #<PK> finché il dato non c'è. -->
      <Tag :value="stato.commessa_codice || `#${stato.commessa_id}`" severity="secondary" />
      <span v-if="stato.cliente_display" class="app-drawer-header-muted">
        {{ stato.cliente_display }}
      </span>
      <span v-if="stato.policy_fatturazione" class="app-text-muted">
        {{ stato.policy_fatturazione }}
      </span>
      <template #status>
        <Tag
          v-if="stato.stato_commessa"
          :value="stato.stato_commessa"
          :severity="statoCommessaSeverity(stato.stato_codice_interno)"
        />
      </template>
    </DrawerEntityHeader>

    <!-- Porta oneri + azioni di stato utente (capabilities data-driven).
         Il `v-if` include `stato_info_key`: senza azioni ma con la
         spiegazione, la barra deve comparire proprio per dirla (R3). -->
    <DrawerActionsBar
      v-if="drawerActions.length || capabilities.stato_info_key"
      :actions="drawerActions"
      :info-key="capabilities.stato_info_key || ''"
      :disabled="loading"
    />

    <!-- Collegamenti diretti (sorgenti a monte + fatture a valle): stessa
         riga di chip dei drawer documento, il grafo completo si apre dai
         chip in dialog. -->
    <DocumentoCollegamentiBar
      v-if="commessaId"
      base-path="/vendite/commesse"
      :versione="stato"
      :doc-id="commessaId"
      @documento-chiuso="reloadAll"
      :readonly="isReadonly" />

    <!-- La TESTATA LEGGIBILE (Blocco C): descrizione e responsabile si
         scrivono qui, la data di apertura si legge. Salva e' un gesto
         suo, acceso solo su una modifica vera: la testata non passa da
         nessun dialog perche' non e' un'azione di processo. -->
    <div v-if="stato" class="app-commessa-testata">
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('vendite.commesse.field_descrizione') }}</label>
          <InputText v-model="testataForm.descrizione" :maxlength="255" fluid
            :disabled="isReadonly"
            :invalid="campiErrati.includes('descrizione')" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.commesse.field_responsabile') }}</label>
          <Select v-model="testataForm.responsabile_risorsa_umana_id"
            :options="responsabiliOptions" option-label="display" option-value="id"
            :option-disabled="(o) => o.attivo === false"
            :loading="responsabiliLoading"
            :disabled="isReadonly" show-clear filter fluid
            :placeholder="t('vendite.commesse.select_responsabile')"
            :invalid="campiErrati.includes('responsabile_risorsa_umana_id')" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.commesse.field_data_apertura') }}</label>
          <!-- Sola lettura: la scrive il default (`fn_data_operativa`)
               alla nascita, e non e' fra i campi del PATCH. -->
          <InputText :model-value="displayDate(stato.data_apertura)" disabled fluid />
        </div>
      </div>
      <div v-if="!isReadonly" class="app-commessa-testata-azioni">
        <Button :label="t('vendite.commesse.testata_salva')" :icon="MANAGE_ICONS.CONFIRM" size="small"
          :loading="testataSaving" :disabled="!testataDirty || loading"
          @click="salvaTestata" />
      </div>
    </div>

    <!-- Contatori funnel testata. -->
    <div v-if="stato" class="app-commessa-contatori">
      <span v-for="c in contatori" :key="c.key" class="app-commessa-contatore">
        <Tag :value="String(c.value)" :severity="c.severity" />
        <small>{{ c.label }}</small>
      </span>
    </div>

    <!-- Righe attivita' + approvazione (A-1). -->
    <div class="app-page-toolbar" style="margin-top: 1rem;">
      <h4 style="margin: 0;">{{ t('vendite.commesse.righe_titolo') }}</h4>
      <!-- Filtro stato emissione: SEMPRE a video, anche quando arriva
           preimpostato dalla card di provenienza. E' il punto della
           funzione — l'utente deve vedere perche' la lista mostra meno
           righe del contatore di testata, e poterlo togliere. -->
      <Select
        v-model="filtroStatoEmissione"
        :options="opzioniStatoEmissione"
        option-label="label"
        option-value="value"
        :placeholder="t('vendite.commesse.filtro_stato_tutte')"
        size="small"
        :aria-label="t('vendite.commesse.filtro_stato_label')"
        v-tooltip.bottom="t('vendite.commesse.filtro_stato_label')"
        style="min-width: 12rem;"
        @change="onFiltroStatoChange"
      />
      <!-- Filtro movimento: gemello di quello sopra, stessa forma e stesso
           handler — cambiare un filtro riparte da pagina 1 e azzera la
           selezione, qualunque filtro sia. Serve a isolare le rettifiche,
           che su una commessa vera sono una manciata dentro centinaia. -->
      <Select
        v-model="filtroTipoMovimento"
        :options="opzioniTipoMovimento"
        option-label="label"
        option-value="value"
        :placeholder="t('vendite.commesse.filtro_movimento_tutti')"
        size="small"
        :aria-label="t('vendite.commesse.filtro_movimento_label')"
        v-tooltip.bottom="t('vendite.commesse.filtro_movimento_label')"
        style="min-width: 12rem;"
        @change="onFiltroStatoChange"
      />
      <!-- Personalizza colonne + Esporta: le stesse due azioni di ogni
           <ListaConfigurabile> dell'applicazione, dallo stesso BB. Il tag
           di stato dice quando la configurazione a video si discosta dal
           preset — senza, l'operatore non sa di star guardando una lista
           personalizzata. -->
      <PageActionsBar :actions="azioniLista">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
      <!-- Difetto D1 (§6-bis, corretto 2026-07-27): la visibilita' era sul
           SOLO permesso, quindi su una commessa gia' PRONTA_FATTURAZIONE i
           due verbi restavano a video disabilitati — rumore che suggerisce
           un'azione che non c'e' piu'. Ora compaiono solo se c'e'
           davvero qualcosa da approvare (il permesso resta condizione
           necessaria, e il BE resta la difesa vera). -->
      <div v-if="canApprova && (stato?.total_non_approvate ?? 0) > 0" style="display: flex; gap: 0.5rem;">
        <Button
          :label="t('vendite.commesse.approva_selezionate', { n: selectedIds.length })"
          :icon="MANAGE_ICONS.APPROVE"
          size="small"
          :disabled="loading || selectedIds.length === 0"
          @click="approva(selectedIds)"
        />
        <Button
          :label="t('vendite.commesse.approva_tutte')"
          :icon="MANAGE_ICONS.APPROVE"
          size="small"
          outlined
          :disabled="loading || (stato?.total_non_approvate ?? 0) === 0"
          @click="approva(null)"
        />
      </div>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.commesse_attivita"
      data-key="id"
      :rows="lista.righe.value"
      :total="lista.totale.value"
      :loading="lista.loading.value"
      :paginator-options="lista.paginatorOptions.value"
      :page="lista.page.value"
      :sort-field="lista.sortField.value"
      :sort-order="lista.sortOrder.value"
      @page="lista.onPage"
      @sort="lista.onSort"
      @config-loaded="lista.onConfigLoaded"
    >
      <!-- Checkbox custom (pattern useSelezioneToggle): solo approvabili.
           Colonna di CHROME del BB, non a catalogo. -->
      <template v-if="canApprova && righeApprovabili.length" #selection-header>
        <Checkbox
          :model-value="allSelected"
          binary
          :indeterminate="anySelected"
          @update:model-value="toggleAll"
        />
      </template>
      <template v-if="canApprova && righeApprovabili.length" #selection="{ data }">
        <Checkbox
          :model-value="isSelected(data)"
          binary
          :disabled="!isSelectable(data)"
          @update:model-value="toggleRow(data)"
        />
      </template>

      <!-- data_attivita e competenza_mese non hanno slot: il seed dichiara
           `date_short` e il formatter di serie le rende gia' cosi'. -->
      <template #cell-segment_key="{ data }">
        <span class="app-commessa-segment" :title="data.segment_key">{{ data.segment_key }}</span>
      </template>
      <template #cell-quantita="{ data }">
        {{ data.quantita ?? '—' }}
      </template>
      <template #cell-prezzo_snapshot="{ data }">
        <span>
          {{ data.prezzo_snapshot != null ? formatCurrency(Number(data.prezzo_snapshot)) : '—' }}
          <i
            v-if="data.prezzo_bloccato"
            :class="STATUS_ICONS.BLOCCATO"
            v-tooltip.bottom="t('vendite.commesse.prezzo_bloccato')"
          />
          <i
            v-if="data.prezzo_da_riallineare"
            :class="[STATUS_ICONS.ERRORE, 'app-dash-ritardo']"
            v-tooltip.bottom="t('vendite.commesse.prezzo_da_riallineare')"
          />
        </span>
      </template>
      <template #cell-stato_approvazione="{ data }">
        <Tag :value="data.stato_approvazione" :severity="statoApprovazioneAttivitaSeverity(data.stato_approvazione)" />
      </template>
      <template #cell-stato_emissione="{ data }">
        <Tag :value="data.stato_emissione" :severity="statoEmissioneAttivitaSeverity(data.stato_emissione)" />
      </template>

      <!-- La colonna azioni resta anche in sola lettura: dal 2026-08-16 il
           kebab porta due voci di NAVIGAZIONE (documento di origine,
           fattura) che non modificano nulla. Nasconderla in readonly
           toglierebbe la sola strada per arrivare al documento proprio a
           chi sta ispezionando. -->
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>


    <!-- Dialog N7 — variazione prezzo eccezionale (prezzo + motivo). -->
    <AppDialog
      :conferma-uscita="fotoVariazione.chiudiConConferma"
      v-model:visible="variazioneDialog"
      :header="t('vendite.commesse.variazione_header')"
      width="sm"
      :loading="loading"
      :save-disabled="!variazioneValida"
      @save="salvaVariazione"
      @cancel="variazioneDialog = false"
    >
      <div class="form-field">
        <label>{{ t('vendite.commesse.variazione_prezzo') }}</label>
        <InputNumber
          v-model="variazionePrezzo"
          mode="decimal"
          :min-fraction-digits="2"
          :max-fraction-digits="10"
          fluid
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.variazione_motivo') }}</label>
        <Textarea v-model="variazioneMotivo" rows="3" fluid />
      </div>
    </AppDialog>

    <!-- Dialog N7-sblocco — motivo obbligatorio (il BE lo esige). -->
    <AppDialog
      :conferma-uscita="fotoSblocca.chiudiConConferma"
      v-model:visible="sbloccaDialog"
      :header="t('vendite.commesse.sblocca_header')"
      width="sm"
      :loading="loading"
      :save-disabled="!sbloccaValido"
      :save-label="t('vendite.commesse.sblocca_salva')"
      @save="salvaSblocco"
      @cancel="sbloccaDialog = false"
    >
      <p class="app-text-muted" style="margin-top: 0;">
        {{ t('vendite.commesse.sblocca_conferma') }}
      </p>
      <div class="form-field">
        <label>{{ t('vendite.commesse.sblocca_motivo') }}</label>
        <Textarea v-model="sbloccaMotivo" rows="3" fluid />
      </div>
    </AppDialog>

    <!-- Dialog annullamento riga manuale — motivo obbligatorio (BE + DB). -->
    <AppDialog
      :conferma-uscita="fotoAnnullaRiga.chiudiConConferma"
      v-model:visible="annullaRigaDialog"
      :header="t('vendite.commesse.annulla_riga_header')"
      width="sm"
      :loading="loading"
      :save-disabled="!annullaRigaValido"
      :save-label="t('vendite.commesse.annulla_riga_salva')"
      save-severity="danger"
      @save="salvaAnnullaRiga"
      @cancel="annullaRigaDialog = false"
    >
      <p class="app-text-muted" style="margin-top: 0;">
        {{ t('vendite.commesse.annulla_riga_conferma') }}
      </p>
      <div class="form-field">
        <label>{{ t('vendite.commesse.annulla_riga_motivo') }}</label>
        <Textarea v-model="annullaRigaMotivo" rows="3" fluid />
      </div>
    </AppDialog>

    <!-- Dialog porta oneri — riga di valore (qta=1) sulla commessa. -->
    <AppDialog
      :conferma-uscita="fotoOnere.chiudiConConferma"
      v-model:visible="onereDialog"
      :header="t('vendite.commesse.onere_header')"
      width="md"
      :loading="loading"
      :save-disabled="!onereValido"
      :save-label="t('vendite.commesse.onere_salva')"
      @save="salvaOnere"
      @cancel="onereDialog = false"
    >
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_articolo') }}</label>
        <!-- Voce ricca: l'IVA e' propria di ogni onere (la penale e' fuori
             campo art.15), va vista al momento della scelta. -->
        <Select
          v-model="onereForm.articoloOnereId"
          :options="onereArticoli"
          option-label="descrizione"
          option-value="id"
          :loading="onereArticoliLoading"
          :placeholder="t('vendite.commesse.onere_articolo_placeholder')"
          fluid
        >
          <template #option="{ option }">
            <div class="app-lookup-option">
              <div class="app-lookup-option__primary">
                {{ option.descrizione }}
                <Tag v-if="option.iva_codice" :value="option.iva_codice" severity="secondary" />
              </div>
              <div class="app-lookup-option__secondary">{{ option.codice }}</div>
              <div class="app-lookup-option__meta">
                <span v-if="option.causale_onere_descrizione">
                  {{ option.causale_onere_descrizione }}
                </span>
                <span v-if="option.iva_descrizione">{{ option.iva_descrizione }}</span>
              </div>
            </div>
          </template>
        </Select>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_importo') }}</label>
        <InputNumber
          v-model="onereForm.importo"
          mode="decimal"
          :min="0"
          :min-fraction-digits="2"
          :max-fraction-digits="10"
          fluid
          :invalid="campiErrati.includes('importo')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_tipo_doc') }}</label>
        <LookupSelect
          v-model="onereForm.tipoDocFiscaleId"
          rel="config.tipi_doc_fiscale"
          :placeholder="t('vendite.commesse.onere_tipo_doc_placeholder')"
          show-code
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_data') }}</label>
        <DatePicker
          v-model="onereForm.dataAttivita"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          fluid
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_motivo') }}</label>
        <Textarea v-model="onereForm.motivo" rows="2" fluid
          :invalid="campiErrati.includes('motivo')" />
      </div>
    </AppDialog>

    <!-- Host del drawer documento aperto dal kebab di riga: documento di
         ORIGINE (tipo dal registry via `sorgente_codice_interno`) o FATTURA in cui la
         riga è finita. Stesso BB dei drill-down dei cruscotti. -->
    <DocumentoDrawerHost
      :visible="docDrawerVisible"
      :tipo-codice="docDrawerTipo"
      :doc-id="docDrawerId"
      @update:visible="onDocDrawerVisible" />

    <!-- La conferma dell'annullo di una commessa con righe non ancora emesse:
         aperta dalla domanda del DB, chiusa dalla conferma o dalla rinuncia. -->
    <DocumentoAnnulloLegamiDialog
      v-if="commessaId"
      :visible="domandaAnnullo !== null"
      base-path="/vendite/commesse"
      :doc-id="commessaId"
      :header="t('vendite.commesse.azione_annulla')"
      :domanda="domandaAnnullo"
      :loading="cambioStato.loading.value"
      :readonly="isReadonly"
      @conferma="onConfermaAnnullo"
      @cancel="cambioStato.annulla()"
    />

    <!-- Il REGISTRO della riga: sola lettura, quindi FUORI dai dialog di azione e
         senza `app-escape`. Si apre dal kebab, anche a commessa in readonly.
         (Montato nello slot della testata fino al 2026-10-03: AppDrawer non
         lo espone, e il dialog si apre solo da una riga gia' a video.) -->
    <CommessaRegistroDialog
      v-model:visible="registroVisible"
      :commessa-id="props.commessaId"
      :commessa-attivita-id="registroRigaId"
    />
  </AppDrawer>

  <!-- Scelta formato export (CSV/XLSX): il file copia la lista a video —
       filtri e ordinamento compresi — non una seconda query che le somiglia. -->
  <ExportDialog
    v-model:visible="exportDialogVisible"
    :loading="exportLoading"
    @export="onExportConfirm"
  />
</template>

<style scoped>
.app-commessa-testata {
  margin-top: 0.75rem;
}
.app-commessa-testata-azioni {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
}
.app-commessa-contatori {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.75rem;
}
.app-commessa-contatore {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
}
.app-commessa-segment {
  display: inline-block;
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
