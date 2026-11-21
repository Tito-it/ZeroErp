<script setup>
// Scopo: Drawer creazione/modifica soggetto PF/PG/ENTE.
// Compone i building block: SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm.
// Il payload unificato va al backend che scompone e crea in transazione.
// I trigger DEFERRED verificano al COMMIT (contatti, indirizzi, dati societari).

import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useSoggettiStore } from '../stores/soggetti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useSoggettoForm } from '../composables/useSoggettoForm'
import { useContattoForm } from '../composables/useContattoForm'
import { useIndirizzoSoggettoForm } from '../composables/useIndirizzoSoggettoForm'
import { collegaIndirizzoSoggettoForm } from '../composables/collegaIndirizzoSoggettoForm'
import { useDatiSocietariForm } from '../composables/useDatiSocietariForm'
import { raccogliFormInline } from '../composables/raccogliFormInline'
import { useLookup } from '../../core/composables/useLookup'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { lookupFormeGiuridiche } from '../../core/apiCore'
import { lookupProvince, getMotiviCambioNatura, deleteSoggettoDatiSocietari } from '../api/anagrafiche'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDebouncedAction } from '../../core/composables/useDebouncedAction'
import { motivoBloccoRiga, bloccoAttivo } from '../../core/utils/bloccoMotivo'
import { campiDaMotivi, fraseMotivo } from '../composables/cambioNatura'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { toDateString, parseIsoDate } from '../../core/utils/date'
import SoggettoForm from './SoggettoForm.vue'
import ContattoForm from './ContattoForm.vue'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'
import DatiSocietariForm from './DatiSocietariForm.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import IndirizziSoggettoDrawer from './IndirizziSoggettoDrawer.vue'
import IndirizziMancantiForm from './IndirizziMancantiForm.vue'
import ContattiSoggettoDrawer from './ContattiSoggettoDrawer.vue'
import ContiBancariDrawer from './ContiBancariDrawer.vue'
import TitoliIvaSoggettoDrawer from './TitoliIvaSoggettoDrawer.vue'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t, te } = useI18n()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()
const store = useSoggettiStore()
const { execute, loading, campiErrati } = useApiHandler()

// Building block composables
// In modifica il sesso non si propone: un privato senza sesso resta vuoto,
// e lo sceglie chi lo vede (lo pretende il guard del DB).
const soggetto = useSoggettoForm({ proponiSesso: () => props.mode !== 'edit' })
const contatto = useContattoForm()
const contattoErrors = ref([])
const indirizzo = useIndirizzoSoggettoForm()
const legameIndirizzo = collegaIndirizzoSoggettoForm(indirizzo)

// Opzioni S/N dei flag di regime fiscale (I0/D8, 2026-08-29).
// ⭐ Spostate qui da `ClienteDrawer.vue` insieme ai due campi: sono la stessa
//   coppia di sempre, non una seconda occorrenza — il consumatore precedente
//   e' morto nello stesso passo (regola del 2 non attivata).
const paOptions = computed(() => [
  { value: 'N', label: t('common.no') },
  { value: 'S', label: t('common.yes') },
])

// Lookup forme giuridiche (ricaricato al cambio tipo) — passato a useDatiSocietariForm
const formeGiuridicheLookup = ref([])
const formeGiuridicheCaricate = ref(false)
// La forma che il soggetto HA (dal dettaglio), con le sue policy REA/capitale.
const formaDelDettaglio = ref(null)
// ⭐ La forma salvata resta VISIBILE anche se la natura non la ammette (riga
//   fuori regola di prima del guard, o natura appena cambiata): marcata, in
//   coda. Fino al 2026-10-10 il Select non la trovava fra le opzioni e la
//   mostrava vuota — un dato illegale per la natura che nessuno diceva
//   (brief-db-dati-fiscali-e-societari-del-soggetto §3.1). Stessa idea di
//   `voceCorrente` di `LookupSelect`.
// ⚠️ Solo a elenco CARICATO: prima, l'elenco vuoto la farebbe dire «non
//    ammessa» a torto.
const formeGiuridicheOpzioni = computed(() => {
  const voce = formaDelDettaglio.value
  if (!voce || !formeGiuridicheCaricate.value
    || formeGiuridicheLookup.value.some(f => f.id === voce.id)) {
    return formeGiuridicheLookup.value
  }
  return [
    ...formeGiuridicheLookup.value,
    { ...voce, descrizione: `${voce.descrizione} — ${t('dati_societari.forma_non_ammessa')}` },
  ]
})
const datiSocietari = useDatiSocietariForm({ formeGiuridiche: formeGiuridicheOpzioni })
const provinceLookup = useLookup(() => lookupProvince())

// Restore ComuneAutocomplete in edit mode
const comuneNascitaItem = ref(null)

// Ruoli (edit mode, readonly)
const ruoliAssegnati = ref([])

// Fase 6 B3+B4: meta-info edit dal backend (tipi modificabili e campi
// immutabili). Niente piu' regole ricostruite client-side.
// Le nature proponibili in modifica, dal DB (K-3): `null` in creazione.
const natureProponibili = ref(null)
const nonEditableFields = ref(null)
// In modifica: la natura com'era all'apertura (la PATCH la manda solo se
// cambia) e se il soggetto ha gia' la riga dei dati societari.
const tipoCaricatoId = ref(null)
const haDatiSocietari = ref(false)
// La terna di «Elimina i dati societari» dal dettaglio (K-5, famiglia 1 di
// api.md §Capability di riga): `can_elimina_dati_societari` + motivo.
const capabilityElimina = ref({})
const PREFISSO_ELIMINA = 'can_elimina_dati_societari'
const capabilityEliminaDa = (data) => Object.fromEntries(
  ['', '_reason', '_reason_key', '_dettaglio'].map(s => [PREFISSO_ELIMINA + s, data?.[PREFISSO_ELIMINA + s] ?? null]),
)

// ── I motivi del cambio di natura (K-4/K-7 di brief-db-cambio-natura-soggetto)
// ⭐ TUTTI i motivi per cui la natura scelta non passerebbe, coi valori che il
//    form sta per mandare: l'endpoint chiama la stessa check del guard. Il
//    rifiuto del PATCH ne porta solo il primo (l'elenco non viaggia
//    nell'eccezione del DB), quindi l'elenco si chiede qui.
// ⚠️ Si chiede solo in modifica e solo se la natura e' cambiata: con la natura
//    di partenza la check non ha niente da dire.
const motiviCambio = ref([])
// ⚠️ La richiesta dei motivi e' fallita: l'elenco vuoto NON vuol dire «il
//    cambio passa», e lo si dice (decisione di Tid, 2026-11-15). Il guard al
//    salvataggio resta la difesa: rifiuta col primo motivo.
const motiviNonVerificati = ref(false)
// Gli indirizzi che la natura scelta chiede e che il soggetto o i suoi ruoli
// non hanno (R-7 di brief-db-fornitore-privato-indirizzi §13.4): arrivano con i
// motivi, dalla stessa sede dei guard degli obbligatori, e si mandano nello
// stesso PATCH del cambio. Senza, il salvataggio e' rifiutato al commit.
const indirizziMancanti = ref([])
const motiviFv = useFetchVersion()
async function caricaMotiviCambio() {
  const f = soggetto.form
  if (!isEdit.value || !props.itemId || !f.tipo_soggetto_dettaglio_id
    || f.tipo_soggetto_dettaglio_id === tipoCaricatoId.value) {
    motiviFv.invalidate()
    motiviCambio.value = []
    indirizziMancanti.value = []
    motiviNonVerificati.value = false
    return
  }
  const mia = motiviFv.tag()
  const corpo = {
    tipo_soggetto_dettaglio_id: f.tipo_soggetto_dettaglio_id,
    partita_iva: f.partita_iva?.trim() || null,
  }
  // I flag solo se valorizzati, come nel PATCH: assenti = il valore salvato.
  if (f.cliente_pa) corpo.cliente_pa = f.cliente_pa
  if (f.split_payment) corpo.split_payment = f.split_payment
  try {
    const res = await getMotiviCambioNatura(props.itemId, corpo)
    if (!motiviFv.isCurrent(mia)) return
    motiviCambio.value = res?.data?.data?.motivi ?? []
    indirizziMancanti.value = res?.data?.data?.indirizzi_mancanti ?? []
    motiviNonVerificati.value = false
  } catch {
    if (!motiviFv.isCurrent(mia)) return
    motiviCambio.value = []
    indirizziMancanti.value = []
    motiviNonVerificati.value = true
  }
}
const { run: caricaMotiviPresto, flush: caricaMotiviOra, cancel: annullaMotivi } =
  useDebouncedAction(caricaMotiviCambio, { detailed: true })
const frasiMotivi = computed(() => motiviCambio.value.map(m => fraseMotivo(t, te, m)))
// I mancanti per titolare: prima il soggetto (`soggetto_ruolo_id` null), poi
// ogni ruolo, nell'ordine della lettura. Un form per gruppo.
const gruppiMancanti = computed(() => {
  const gruppi = new Map()
  for (const m of indirizziMancanti.value) {
    const chiave = m.soggetto_ruolo_id ?? 'soggetto'
    if (!gruppi.has(chiave)) {
      gruppi.set(chiave, {
        chiave,
        soggettoRuoloId: m.soggetto_ruolo_id ?? null,
        titolo: m.soggetto_ruolo_id == null
          ? t('anagrafiche.soggetti.cambio_natura_indirizzi_soggetto')
          : t('anagrafiche.soggetti.cambio_natura_indirizzi_ruolo', { ruolo: m.ruolo_descrizione }),
        mancanti: [],
      })
    }
    gruppi.get(chiave).mancanti.push(m)
  }
  return [...gruppi.values()]
})
// I form montati, per chiave del gruppo: al salvataggio ne raccolgo i payload.
const formMancanti = new Map()
function registraFormMancanti(chiave, el) {
  if (el) formMancanti.set(chiave, el)
  else formMancanti.delete(chiave)
}
// I campi della riga che i motivi chiedono di correggere: si mostrano e si
// accendono anche se la natura scelta non li prevede (K-6: niente piu' flag
// portato a `N` di nascosto, lo porta l'operatore).
const campiMotivi = computed(() => campiDaMotivi(motiviCambio.value))
const mostraClientePa = computed(() =>
  soggetto.showClientePa.value || campiMotivi.value.has('cliente_pa'))
const mostraSplitPayment = computed(() =>
  soggetto.showSplitPayment.value || campiMotivi.value.has('split_payment'))
// ⚠️ Anche la P.IVA: verso una natura senza P.IVA il campo sparirebbe
//    (`piva_obbligatoria`), mentre il motivo chiede proprio di svuotarlo — e il
//    PATCH rimanderebbe il valore che non si vede.
const mostraPartitaIva = computed(() =>
  soggetto.showPartitaIva.value || campiMotivi.value.has('partita_iva'))
// La P.IVA indicata da un motivo si accende nel form come un campo errato.
const campiErratiForm = computed(() => [...campiErrati.value, ...campiMotivi.value])
const campoInvalido = (campo) => campiErrati.value.includes(campo) || campiMotivi.value.has(campo)

// Drawer indirizzi, contatti e conti bancari (edit mode)
const indirizziDrawerVisible = ref(false)
const indirizziRiepilogo = ref([])
const contattiDrawerVisible = ref(false)
const contattiRiepilogo = ref([])
const contiBancariDrawerVisible = ref(false)
const titoliIvaDrawerVisible = ref(false)
const titoliIvaRiepilogo = ref([])
const contiBancariRiepilogo = ref([])

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  itemId: { type: String, default: null },
  // Props opzionali per uso da SoggettoResolver
  tipoDefaultId: { type: Number, default: null },
  tipiAmmessiIds: { type: Array, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'saved-with-data'])

// Modifiche non salvate (BB useDrawerFormPreserve) sul form del soggetto, che
// vive nel composable, e in creazione su cio' che il Salva manda con lui:
// contatto, indirizzo e (se la sezione e' visibile) dati societari inline.
// ⚠️ `props.mode` e non `isEdit`: `isEdit` e' dichiarato piu' sotto, e il BB
//    puo' leggere il computed gia' alla sua creazione (TDZ).
const formSoggetto = computed(() => (props.mode === 'edit'
  ? soggetto.form
  : {
      ...soggetto.form,
      ...raccogliFormInline({
        contatto,
        indirizzo,
        datiSocietari: soggetto.showDatiSocietari.value ? datiSocietari : null,
      }),
    }))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSoggetto, { visibile: () => props.visible })

const isEdit = computed(() => props.mode === 'edit')

// Carica forme giuridiche filtrate al cambio tipo soggetto.
// Versione per evitare race condition: se il tipo cambia durante il fetch,
// la risposta della richiesta precedente viene scartata.
const fgFv = useFetchVersion()
watch(() => soggetto.form.tipo_soggetto_dettaglio_id, async (tipoId) => {
  formeGiuridicheCaricate.value = false
  if (!tipoId || !soggetto.showDatiSocietari.value) {
    formeGiuridicheLookup.value = []
    return
  }
  const v = fgFv.tag()
  try {
    const res = await lookupFormeGiuridiche(tipoId)
    if (fgFv.isCurrent(v)) {
      formeGiuridicheLookup.value = res.data.data.results
      formeGiuridicheCaricate.value = true
    }
  } catch {
    if (fgFv.isCurrent(v)) formeGiuridicheLookup.value = []
  }
})

// === Smart defaults (solo in create mode) ===

// Auto-fill nominativo contatto da cognome+nome (PF) o ragione_sociale (PG).
// Sovrascrive solo se l'utente non ha modificato manualmente il nominativo.
let nominativoManuale = false
watch(() => contatto.form.nominativo, (val, old) => {
  // Se il cambio non viene dal watcher sotto, l'utente sta digitando manualmente
  if (isEdit.value) return
  const autoNome = _buildNominativo()
  if (val !== autoNome && old === autoNome) nominativoManuale = true
})

function _buildNominativo() {
  if (soggetto.isPF.value) {
    const parts = [soggetto.form.cognome.trim(), soggetto.form.nome.trim()].filter(Boolean)
    return parts.join(' ')
  }
  return soggetto.form.ragione_sociale.trim()
}

watch(
  () => soggetto.isPF.value
    ? `${soggetto.form.cognome}|${soggetto.form.nome}`
    : soggetto.form.ragione_sociale,
  () => {
    if (isEdit.value || nominativoManuale) return
    contatto.form.nominativo = _buildNominativo()
  }
)

// Imposta matrice indirizzi nel composable quando cambia tipo soggetto
watch(() => soggetto.matriceIndirizzi.value, (matrice) => {
  if (isEdit.value) return
  indirizzo.setMatrice(matrice)
})

// Carica province quando servono dati societari
watch(() => soggetto.showDatiSocietari.value, (show) => {
  if (show && !provinceLookup.loaded.value) {
    provinceLookup.load()
  }
})

// Popola il drawer con i dati del soggetto in edit mode.
function populateFromDetail(data) {
  soggetto.form.tipo_soggetto_dettaglio_id = data.tipo_soggetto_dettaglio_id
  soggetto.form.cognome = data.cognome || ''
  soggetto.form.nome = data.nome || ''
  soggetto.form.ragione_sociale = data.ragione_sociale || ''
  soggetto.form.codice_fiscale = data.codice_fiscale || ''
  soggetto.form.partita_iva = data.partita_iva || ''
  // ⛔ Mai `|| 'M'`: un sesso che il DB non ha non si inventa a video.
  soggetto.form.sesso = data.sesso?.trim() || ''
  // ⚠️ `parseIsoDate` e non `new Date('YYYY-MM-DD')` (mezzanotte UTC): nei
  //    fusi negativi la data di nascita si mostrava — e si risalvava — un
  //    giorno prima (fino al 2026-10-09).
  soggetto.form.data_nascita = parseIsoDate(data.data_nascita)
  soggetto.form.comune_nascita_id = data.comune_nascita_id || null
  // ⚠️ `.trim()`: la colonna e' `character(1)` — PostgreSQL restituisce il
  //    valore paddato, e un confronto `=== 'S'` su ' ' fallirebbe in silenzio.
  // ⚠️ `?? null` e NON `|| 'N'`: se la risposta non porta il flag, il form deve
  //    dire «non lo so», non «no». Con il default 'N' il salvataggio sotto
  //    SPEGNEREBBE uno split payment attivo — un errore fiscale silenzioso,
  //    nella direzione peggiore (la stessa che il travaso a DB ha risolto con
  //    `bool_or`, facendo vincere 'S').
  // Niente `.trim()` (dal 2026-10-10): sono `character(1)` NOT NULL con CHECK
  //    ('S','N'), cioe' a lunghezza esatta — il padding non c'e'
  //    (brief-db-character-n-spazi-di-riempimento §2.2).
  soggetto.form.split_payment = data.split_payment ?? null
  soggetto.form.cliente_pa = data.cliente_pa ?? null
  tipoCaricatoId.value = data.tipo_soggetto_dettaglio_id ?? null
  // Oggetto completo per restore ComuneAutocomplete
  comuneNascitaItem.value = data.comune_nascita_id
    ? { id: data.comune_nascita_id, descrizione: data.comune_nascita_descrizione || '', provincia_sigla: data.comune_nascita_provincia_sigla || '' }
    : null
  if (data.contatti?.length > 0) {
    contatto.populate(data.contatti[0])
  }
  haDatiSocietari.value = !!data.dati_societari
  formaDelDettaglio.value = data.dati_societari?.forma_giuridica_id
    ? {
        id: data.dati_societari.forma_giuridica_id,
        descrizione: data.dati_societari.forma_giuridica_descrizione,
        rea_policy: data.dati_societari.rea_policy,
        capitale_sociale_policy: data.dati_societari.capitale_sociale_policy,
      }
    : null
  if (data.dati_societari) {
    datiSocietari.populate(data.dati_societari)
  }
  // Ruoli
  ruoliAssegnati.value = data.ruoli || []
  // Meta-info edit (Fase 6 B3+B4): sempre array dopo populate (anche
  // []), distingue dal sentinel null usato in create mode.
  natureProponibili.value = data.nature_proponibili ?? []
  capabilityElimina.value = capabilityEliminaDa(data)
  motiviCambio.value = []
  indirizziMancanti.value = []
  motiviNonVerificati.value = false
  nonEditableFields.value = data.non_editable_fields ?? []
  titoliIvaRiepilogo.value = data.titoli_iva || []
  // Indirizzi, contatti e conti bancari riepilogo
  indirizziRiepilogo.value = data.indirizzi || []
  contattiRiepilogo.value = data.contatti || []
  contiBancariRiepilogo.value = data.conti_bancari || []
}

// Callback quando i drawer indirizzi/contatti salvano — ricarica il riepilogo.
async function onContattiSaved() {
  if (!props.itemId) return
  try {
    const data = await store.fetchDetail(props.itemId)
    contattiRiepilogo.value = data.contatti || []
  } catch { /* silent */ }
}

async function onIndirizziSaved() {
  if (!props.itemId) return
  try {
    const data = await store.fetchDetail(props.itemId)
    indirizziRiepilogo.value = data.indirizzi || []
  } catch { /* silent */ }
}

// ⭐ I titoli IVA arrivano gia' dentro il dettaglio del soggetto (come conti e
//   contatti): il riepilogo non costa un round-trip in piu'.
async function onTitoliIvaSaved() {
  if (!props.itemId) return
  try {
    const data = await store.fetchDetail(props.itemId)
    titoliIvaRiepilogo.value = data.titoli_iva || []
  } catch { /* silent */ }
}

async function onContiBancariSaved() {
  if (!props.itemId) return
  try {
    const data = await store.fetchDetail(props.itemId)
    contiBancariRiepilogo.value = data.conti_bancari || []
  } catch { /* silent */ }
}

// Carica dati quando il drawer si apre.
// Quando si chiude, invalida versioni async per scartare risposte in volo.
watch(() => props.visible, async (val) => {
  if (!val) { fgFv.invalidate(); motiviFv.invalidate(); annullaMotivi(); return }

  if (isEdit.value && props.itemId) {
    try {
      const data = await store.fetchDetail(props.itemId)
      populateFromDetail(data)
    } catch {
      emit('update:visible', false)
      return
    }
  } else {
    soggetto.reset()
    contatto.reset()
    contattoErrors.value = []
    indirizzo.reset()
    datiSocietari.reset()
    comuneNascitaItem.value = null
    ruoliAssegnati.value = []
    natureProponibili.value = null
    capabilityElimina.value = {}
    motiviCambio.value = []
    indirizziMancanti.value = []
    motiviNonVerificati.value = false
    nonEditableFields.value = null
    tipoCaricatoId.value = null
    haDatiSocietari.value = false
    formaDelDettaglio.value = null
    nominativoManuale = false
    // Pre-imposta tipo soggetto se indicato dal chiamante (es. SoggettoResolver)
    if (props.tipoDefaultId) {
      soggetto.form.tipo_soggetto_dettaglio_id = props.tipoDefaultId
    }
  }
  // Lookup contatto e, in creazione, il tipo di default (il primo della lista,
  // tipicamente «Principale»). ⚠️ PRIMA della fotografia: e' un valore del
  // codice, non dell'operatore — scritto dopo, il drawer nasceva «modificato».
  // E a ogni apertura: il lookup e' in cache, e un watch sulla lista non
  // scattava piu' dalla seconda creazione in poi.
  try { await contatto.tipiContatto.load() } catch { /* best-effort: resta da scegliere */ }
  const tipi = contatto.tipiContatto.items.value
  if (!isEdit.value && !contatto.form.tipo_contatto_id && tipi.length > 0) {
    contatto.form.tipo_contatto_id = tipi[0].id
  }
  // Dopo il nextTick: i watch del form (nominativo, matrice indirizzi) hanno
  // gia' scritto le loro derivazioni, e la fotografia le include.
  await nextTick()
  fissa()
})

// I motivi seguono cio' che la check legge: natura, P.IVA e flag del form.
watch(
  () => [
    soggetto.form.tipo_soggetto_dettaglio_id, soggetto.form.partita_iva,
    soggetto.form.cliente_pa, soggetto.form.split_payment,
  ],
  () => { if (props.visible && isEdit.value) caricaMotiviPresto() },
)

// ── «Elimina i dati societari» (K-5/K-8): la strada per una natura che non li
//    prevede, separata dal cambio. Spenta col motivo quando la natura attuale
//    li richiede; la riga eliminata resta nello storico.
const eliminaSpenta = computed(() =>
  bloccoAttivo(capabilityElimina.value, PREFISSO_ELIMINA, PREFISSO_ELIMINA))
const motivoElimina = computed(() =>
  motivoBloccoRiga(t, te, capabilityElimina.value, PREFISSO_ELIMINA))
// ⚠️ La sezione si mostra anche quando la natura SCELTA non prevede i dati
//    societari ma il soggetto li ha: e' proprio lì che servono da togliere.
const mostraSezioneDatiSocietari = computed(() =>
  soggetto.showDatiSocietari.value || (isEdit.value && haDatiSocietari.value))

function chiediEliminaDatiSocietari() {
  confirmAction({
    header: t('anagrafiche.soggetti.elimina_dati_societari'),
    message: t('anagrafiche.soggetti.elimina_dati_societari_conferma'),
    danger: true,
    onAccept: eliminaDatiSocietari,
  })
}

async function eliminaDatiSocietari() {
  if (!props.itemId) return
  const result = await execute(
    () => deleteSoggettoDatiSocietari(props.itemId),
    { successMessage: t('anagrafiche.soggetti.dati_societari_eliminati') },
  )
  if (result === null) return
  // Si rilegge il dettaglio: la sezione, la sua capability e le nature
  // proponibili cambiano tutte insieme. ⚠️ Niente populate: perderebbe le
  // modifiche non salvate del form (la natura scelta compresa), e qui si
  // aggiornano solo i pezzi che l'eliminazione cambia.
  // L'eliminazione e' gia' salvata: se il form non aveva altre modifiche, la
  // sezione svuotata non deve farlo sembrare «modificato» alla chiusura.
  const eraModificato = modificato.value
  try {
    const data = await store.fetchDetail(props.itemId)
    haDatiSocietari.value = !!data.dati_societari
    if (!data.dati_societari) {
      datiSocietari.reset()
      formaDelDettaglio.value = null
    }
    natureProponibili.value = data.nature_proponibili ?? []
    capabilityElimina.value = capabilityEliminaDa(data)
    if (!eraModificato) {
      await nextTick()
      fissa()
    }
  } catch { /* il dettaglio si rilegge alla prossima apertura */ }
  emit('saved')
  caricaMotiviOra()
}

// Scopo: Validazione aggregata di tutti i building block.
const canSave = computed(() => {
  if (isEdit.value) return true
  const sogValid = soggetto.validate().length === 0
  const conValid = contatto.validate().length === 0
  // Blocca se indirizzo duplicato (warning attivo) o non trovato (senza "crea nuovo")
  const hasIndirizzoBlock = indirizzo.indirizzoWarnings.value.length > 0
    || indirizzo.addressNotFound.value
  return sogValid && conValid && !hasIndirizzoBlock
})

// Scopo: Salvataggio — costruisce payload unificato per il backend.
async function handleSave() {
  // Validazione contatto (solo in create, dove il form e' inline)
  if (!isEdit.value) {
    contattoErrors.value = contatto.validate()
    if (contattoErrors.value.length > 0) return
  }

  if (isEdit.value) {
    const payload = {}
    const f = soggetto.form
    if (soggetto.isPF.value) {
      payload.cognome = f.cognome
      payload.nome = f.nome
      // Vuoto -> NULL: per la ditta individuale e' un valore ammesso.
      if (soggetto.showSesso.value) payload.sesso = f.sesso || null
      payload.data_nascita = toDateString(f.data_nascita)
      payload.comune_nascita_id = f.comune_nascita_id
    } else {
      payload.ragione_sociale = f.ragione_sociale
    }
    payload.codice_fiscale = f.codice_fiscale?.trim() || null
    payload.partita_iva = f.partita_iva?.trim() || null
    // Regime fiscale (I0/D8). Solo in EDIT: alla creazione il DB applica il
    // default 'N', che e' la direzione sicura — un soggetto di cui nessuno ha
    // detto nulla non e' in scissione dei pagamenti.
    // ⛔ Si spediscono SOLO se valorizzati: un flag che il dettaglio non ha
    //    portato resta `null`, e mandarlo scriverebbe un valore che nessuno ha
    //    letto ne' scelto. Chiave assente = colonna non toccata.
    // ⛔ Il valore che l'operatore vede, mai uno scelto di nascosto (K-6 di
    //    brief-db-cambio-natura-soggetto, 2026-11-15). Fino a quel giorno un
    //    flag che la natura non ammette partiva 'N' in silenzio: era la
    //    «pulizia» che il modello non fa piu'. Se il DB rifiuta col motivo del
    //    flag, il campo si mostra (`mostraClientePa`) e lo porta a No lui.
    if (f.split_payment) payload.split_payment = f.split_payment
    if (f.cliente_pa) payload.cliente_pa = f.cliente_pa
    // La natura, solo se cambiata: i guard la confrontano con flag, forma e
    // titoli IVA (brief-db-dati-fiscali-e-societari-del-soggetto §8.3).
    if (f.tipo_soggetto_dettaglio_id !== tipoCaricatoId.value) {
      payload.tipo_soggetto_dettaglio_id = f.tipo_soggetto_dettaglio_id
      // Gli indirizzi che la natura nuova chiede, nello stesso salvataggio: il
      // backend li scrive dopo la natura (R-7). Un gruppo lasciato vuoto non
      // parte, e il rifiuto del guard dice che cosa manca.
      for (const g of gruppiMancanti.value) {
        const indirizzi = formMancanti.get(g.chiave)?.toPayloadArray() ?? []
        if (!indirizzi.length) continue
        if (g.soggettoRuoloId == null) {
          payload.indirizzi = indirizzi
        } else {
          (payload.indirizzi_ruoli ??= []).push({ soggetto_ruolo_id: g.soggettoRuoloId, indirizzi })
        }
      }
    }
    // Dati societari col verbo DB, STATO INTERO, come in creazione (parte B).
    // ⚠️ Solo se la riga c'e' gia' o l'operatore ha scelto una forma: con la
    //    natura OPTIONAL e la sezione lasciata vuota non c'e' niente da creare,
    //    e una riga senza forma il DB la rifiuta (forma NOT NULL, C-2).
    // ⭐ Il backend scrive PRIMA la natura e POI i dati societari, nella stessa
    //    transazione: natura e forma si cambiano nello stesso salvataggio.
    if (soggetto.showDatiSocietari.value
      && (haDatiSocietari.value || datiSocietari.form.forma_giuridica_id)) {
      payload.dati_societari = datiSocietari.toPayload()
    }

    const result = await execute(
      () => store.update(props.itemId, payload),
      { successMessage: t('anagrafiche.soggetti.soggetto_salvato') }
    )
    if (result !== null) {
      emit('saved')
      emit('update:visible', false)
    } else if (payload.tipo_soggetto_dettaglio_id != null) {
      // Il rifiuto porta il primo motivo: l'elenco intero si rilegge subito.
      caricaMotiviOra()
    }
  } else {
    const payload = {
      tipo_soggetto_dettaglio_id: soggetto.form.tipo_soggetto_dettaglio_id,
      cognome: soggetto.form.cognome,
      nome: soggetto.form.nome,
      ragione_sociale: soggetto.form.ragione_sociale,
      codice_fiscale: soggetto.form.codice_fiscale,
      partita_iva: soggetto.form.partita_iva,
      sesso: soggetto.showSesso.value ? (soggetto.form.sesso || null) : null,
      data_nascita: toDateString(soggetto.form.data_nascita),
      comune_nascita_id: soggetto.form.comune_nascita_id,
      contatto: { ...contatto.form },
    }

    // Indirizzi — auto-clone gestito dal backend
    if (indirizzo.hasIndirizzi.value) {
      payload.indirizzi = indirizzo.toPayloadArray()
      payload.auto_clone = indirizzo.autoClone.value
    }

    // Dati societari (solo se visibili)
    if (soggetto.showDatiSocietari.value) {
      payload.dati_societari = datiSocietari.toPayload()
    }

    const result = await execute(
      () => store.create(payload),
      { successMessage: t('anagrafiche.soggetti.soggetto_creato') }
    )
    if (result !== null) {
      // result e' gia' unwrapped da useApiHandler (body.data)
      const id = result?.id ?? result?.soggetto_id ?? null
      const data = {
        id,
        ragione_sociale: soggetto.form.cognome
          ? `${soggetto.form.cognome} ${soggetto.form.nome}`.trim()
          : soggetto.form.ragione_sociale,
        cf: soggetto.form.codice_fiscale,
        piva: soggetto.form.partita_iva,
        email: contatto.form.email || null
      }
      emit('saved')
      emit('saved-with-data', data)
      emit('update:visible', false)
      store.fetchList()
    }
  }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('anagrafiche.soggetti.soggetto')"
    :icon="NAV_ICONS.ANAGRAFICHE"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="handleSave"
  >
    <!-- Sezione: Dati soggetto -->
    <SoggettoForm
      :form="soggetto.form"
      :campi-errati="campiErratiForm"
      :tipi-soggetto="soggetto.tipiSoggetto"
      :is-p-f="soggetto.isPF.value"
      :show-sesso="soggetto.showSesso.value"
      :require-sesso="soggetto.requireSesso.value"
      :show-partita-iva="mostraPartitaIva"
      :is-edit="isEdit"
      :disabled="false"
      :tipi-ammessi-ids="tipiAmmessiIds"
      :nature-proponibili="natureProponibili"
      :non-editable-fields="nonEditableFields"
      :comune-nascita-item="comuneNascitaItem"
    />

    <!-- I motivi del cambio di natura, TUTTI (K-7): la stessa check del guard,
         coi valori del form. Si tolgono a mano; quelli su un campo della riga
         lo accendono qui sotto. -->
    <Message v-if="isEdit && motiviNonVerificati" severity="warn" :closable="false">
      {{ t('anagrafiche.soggetti.cambio_natura_motivi_non_verificati') }}
    </Message>
    <Message v-else-if="isEdit && frasiMotivi.length" severity="warn" :closable="false">
      <div>{{ t('anagrafiche.soggetti.cambio_natura_motivi_titolo') }}</div>
      <ul class="mt-025">
        <li v-for="(frase, i) in frasiMotivi" :key="i">{{ frase }}</li>
      </ul>
    </Message>

    <!-- Gli indirizzi che la natura scelta chiede (R-7): un form per titolare,
         salvati col cambio di natura. -->
    <template v-if="isEdit && gruppiMancanti.length">
      <Message severity="info" :closable="false">
        {{ t('anagrafiche.soggetti.cambio_natura_indirizzi_titolo') }}
      </Message>
      <IndirizziMancantiForm
        v-for="g in gruppiMancanti"
        :key="g.chiave"
        :ref="el => registraFormMancanti(g.chiave, el)"
        :titolo="g.titolo"
        :mancanti="g.mancanti"
        :campi-errati="campiErrati"
      />
    </template>

    <!-- Sezione: Contatto inline (create) o riepilogo (edit) -->
    <template v-if="!isEdit">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_contatto') }}</h4>
      </div>
      <ContattoForm
        :campi-errati="campiErrati"
        :form="contatto.form"
        :tipi-contatto="contatto.tipiContatto"
        :unita-organizzative="contatto.unitaOrganizzative"
        :errors="contattoErrors"
        :show-u-o="false"
        :disabled="false"
      />
    </template>
    <template v-else>
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_contatto') }}</h4>
      </div>
      <div class="app-riepilogo-section">
        <div v-if="contattiRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="c in contattiRiepilogo" :key="c.id" class="app-riepilogo-item">
            <strong>{{ c.nominativo }}</strong>
            <span v-if="c.email" class="app-riepilogo-detail">{{ c.email }}</span>
            <span v-if="c.telefono" class="app-riepilogo-detail">{{ c.telefono }}</span>
          </div>
        </div>
        <div v-else style="color: var(--app-text-muted); font-size: 0.85rem;">
          {{ t('anagrafiche.contatto.nessun_contatto') }}
        </div>
        <Button
          :label="t('anagrafiche.contatto.gestisci_contatti')"
          :icon="MANAGE_ICONS.CONTATTI"
          text
          size="small"
          class="app-action-btn app-escape mt-025"
          @click="contattiDrawerVisible = true"
        />
      </div>
    </template>

    <!-- Separatore: Indirizzo (solo in create mode) -->
    <template v-if="!isEdit">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_indirizzo') }}</h4>
      </div>
      <IndirizzoSoggettoForm
        v-bind="legameIndirizzo"
        :campi-errati="campiErrati"
      />
    </template>

    <!-- Sezione: Dati societari (condizionale) — subito dopo anagrafica/P.IVA -->
    <template v-if="mostraSezioneDatiSocietari">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_dati_societari') }}</h4>
      </div>
      <!-- La natura scelta non li prevede, ma il soggetto li ha: si dice, e
           si offre di eliminarli (il cambio non li toglie da solo). -->
      <div v-if="!soggetto.showDatiSocietari.value" class="app-text-muted">
        {{ t('anagrafiche.soggetti.dati_societari_non_previsti') }}
      </div>
      <DatiSocietariForm
        v-else
        :form="datiSocietari.form"
        :campi-errati="campiErrati"
        :forme-giuridiche="formeGiuridicheOpzioni"
        :province-lookup="provinceLookup"
        :show-rea="datiSocietari.showRea.value"
        :require-rea="datiSocietari.requireRea.value"
        :show-capitale-sociale="datiSocietari.showCapitaleSociale.value"
        :require-capitale-sociale="datiSocietari.requireCapitaleSociale.value"
        :required="soggetto.requireDatiSocietari.value"
        :disabled="false"
      />
      <div v-if="isEdit && haDatiSocietari && !isReadonly">
        <Button
          :label="t('anagrafiche.soggetti.elimina_dati_societari')"
          :icon="MANAGE_ICONS.DELETE"
          text
          size="small"
          severity="danger"
          class="app-escape mt-025"
          :disabled="eliminaSpenta || loading"
          @click="chiediEliminaDatiSocietari"
        />
        <small v-if="eliminaSpenta" class="app-field-hint">{{ motivoElimina }}</small>
      </div>
    </template>

    <!-- Sezione: Dati fiscali (edit mode) — regime della controparte.
         I0/D8: i due flag sono saliti da `anagrafiche.clienti`, dove stavano
         su una riga PER FORNITURA e ammettevano valori opposti per la stessa
         partita IVA. Stanno accanto a CF/P.IVA perche' e' da li' che
         discendono. ⚠️ NON sono un codice IVA e non entrano nel risolutore
         (D4): non cambiano l'aliquota, cambiano CHI VERSA l'imposta. -->
    <!-- ⭐ Dal 2026-10-10 i due campi seguono la natura (`cliente_pa_ammesso`,
         `split_payment_ammesso`): la sezione c'e' solo se ne resta almeno uno
         (un privato o una ditta individuale non ne hanno nessuno). -->
    <!-- ⚠️ Dal 2026-11-15 un campo si mostra anche quando la natura non lo
         prevede ma un motivo del cambio lo indica (K-6): e' l'operatore a
         portarlo a No, non il drawer di nascosto. -->
    <template v-if="isEdit && (mostraClientePa || mostraSplitPayment)">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_dati_fiscali') }}</h4>
      </div>
      <div class="form-grid-2col">
        <div v-if="mostraClientePa" class="form-field">
          <label>{{ t('anagrafiche.soggetti.field_cliente_pa') }}</label>
          <Select v-model="soggetto.form.cliente_pa" :options="paOptions"
            option-label="label" option-value="value"
            :invalid="campoInvalido('cliente_pa')"
            :disabled="isReadonly" />
        </div>
        <div v-if="mostraSplitPayment" class="form-field">
          <label>{{ t('anagrafiche.soggetti.field_split_payment') }}</label>
          <Select v-model="soggetto.form.split_payment" :options="paOptions"
            option-label="label" option-value="value"
            :invalid="campoInvalido('split_payment')"
            :disabled="isReadonly" />
        </div>
      </div>
    </template>

    <!-- Sezione: Indirizzi riepilogo (edit mode) + pulsante Gestisci -->
    <template v-if="isEdit">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_indirizzo') }}</h4>
      </div>
      <div>
        <div v-if="indirizziRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="ind in indirizziRiepilogo" :key="ind.id" class="app-riepilogo-item">
            <Tag :value="ind.tipo_indirizzo_descrizione" severity="info" />
            <span>{{ ind.indirizzo_display }}</span>
          </div>
        </div>
        <div v-else style="color: var(--app-text-muted); font-size: 0.85rem;">
          {{ t('anagrafiche.indirizzo_soggetto.nessun_indirizzo') }}
        </div>
        <Button
          :label="t('anagrafiche.indirizzo_soggetto.gestisci_indirizzi')"
          :icon="MANAGE_ICONS.INDIRIZZI"
          text
          size="small"
          class="app-action-btn app-escape mt-025"
          @click="indirizziDrawerVisible = true"
        />
      </div>
    </template>

    <!-- Sezione: Conti bancari riepilogo (edit mode) -->
    <template v-if="isEdit">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.conti_bancari.titolo') }}</h4>
      </div>
      <div class="app-riepilogo-section">
        <div v-if="contiBancariRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="cb in contiBancariRiepilogo" :key="cb.id" class="app-riepilogo-item">
            <Tag :value="cb.uso" severity="info" />
            <span class="app-riepilogo-detail app-mono">{{ cb.iban }}</span>
            <span v-if="cb.filiale_nome" class="app-riepilogo-detail">{{ cb.filiale_nome }}</span>
          </div>
        </div>
        <div v-else style="color: var(--app-text-muted); font-size: 0.85rem;">
          {{ t('anagrafiche.conti_bancari.nessun_conto') }}
        </div>
        <Button
          :label="t('anagrafiche.conti_bancari.gestisci_conti')"
          :icon="MANAGE_ICONS.CONTI_BANCARI"
          text
          size="small"
          class="app-action-btn app-escape mt-025"
          @click="contiBancariDrawerVisible = true"
        />
      </div>
    </template>

    <!-- Sezione: Titoli IVA (edit mode) — I7/D10.
         ⭐ E' la sede che realizza D7: l'influenza del soggetto sull'IVA passa
         SEMPRE da un titolo registrato, datato e con una prova documentale —
         mai da una colonna di default appesa all'anagrafica. E' la ragione per
         cui `clienti.iva_id` e' stata tolta e non sostituita. -->
    <template v-if="isEdit">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.titoli_iva.titolo_lista') }}</h4>
      </div>
      <div class="app-riepilogo-section">
        <div v-if="titoliIvaRiepilogo.length > 0" class="app-riepilogo-list">
          <div v-for="ti in titoliIvaRiepilogo" :key="ti.id" class="app-riepilogo-item">
            <Tag :value="ti.tipo_descrizione" :severity="ti.attivo ? 'info' : 'secondary'" />
            <span class="app-riepilogo-detail">{{ ti.emittente_ragione_sociale }}</span>
            <span v-if="ti.residuo != null" class="app-riepilogo-detail">
              {{ t('anagrafiche.titoli_iva.col_residuo') }}: {{ ti.residuo }}
            </span>
          </div>
        </div>
        <div v-else style="color: var(--app-text-muted); font-size: 0.85rem;">
          {{ t('anagrafiche.titoli_iva.lista_vuota') }}
        </div>
        <Button
          :label="t('anagrafiche.titoli_iva.gestisci_titoli')"
          :icon="MANAGE_ICONS.TITOLI_IVA"
          text
          size="small"
          class="app-action-btn app-escape mt-025"
          @click="titoliIvaDrawerVisible = true"
        />
      </div>
    </template>

    <!-- Sezione: Ruoli (solo edit mode, readonly) -->
    <template v-if="isEdit">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_ruoli') }}</h4>
      </div>
      <div v-if="ruoliAssegnati.length > 0" class="ruoli-tags">
        <Tag v-for="r in ruoliAssegnati" :key="r.tipo_ruolo_id"
             :value="r.ruolo_descrizione" severity="info" />
      </div>
      <div v-else style="color: var(--app-text-muted); font-size: 0.85rem;">
        {{ t('anagrafiche.soggetti.nessun_ruolo') }}
      </div>
    </template>
  </AppDrawer>

  <!-- Drawer indirizzi soggetto (edit mode) -->
  <IndirizziSoggettoDrawer
    :visible="indirizziDrawerVisible"
    @update:visible="v => indirizziDrawerVisible = v"
    :soggetto-id="props.itemId"
    @saved="onIndirizziSaved"
  />

  <!-- Drawer contatti soggetto (edit mode) -->
  <ContattiSoggettoDrawer
    :visible="contattiDrawerVisible"
    @update:visible="v => contattiDrawerVisible = v"
    :soggetto-id="props.itemId"
    @saved="onContattiSaved"
  />

  <!-- Drawer titoli IVA soggetto (edit mode) -->
  <TitoliIvaSoggettoDrawer
    :visible="titoliIvaDrawerVisible"
    @update:visible="v => titoliIvaDrawerVisible = v"
    :soggetto-id="props.itemId"
    :soggetto-nome="_buildNominativo()"
    @saved="onTitoliIvaSaved"
  />

  <!-- Drawer conti bancari soggetto (edit mode) -->
  <ContiBancariDrawer
    :visible="contiBancariDrawerVisible"
    @update:visible="v => contiBancariDrawerVisible = v"
    :owner-id="props.itemId"
    :owner-name="_buildNominativo()"
    @saved="onContiBancariSaved"
  />
</template>

<style scoped>
.ruoli-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
