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
import { useDatiSocietariForm } from '../composables/useDatiSocietariForm'
import { raccogliFormInline } from '../composables/raccogliFormInline'
import { useLookup } from '../../core/composables/useLookup'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { lookupFormeGiuridiche } from '../../core/apiCore'
import { lookupProvince } from '../api/anagrafiche'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { toDateString, parseIsoDate } from '../../core/utils/date'
import SoggettoForm from './SoggettoForm.vue'
import ContattoForm from './ContattoForm.vue'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'
import DatiSocietariForm from './DatiSocietariForm.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import IndirizziSoggettoDrawer from './IndirizziSoggettoDrawer.vue'
import ContattiSoggettoDrawer from './ContattiSoggettoDrawer.vue'
import ContiBancariDrawer from './ContiBancariDrawer.vue'
import TitoliIvaSoggettoDrawer from './TitoliIvaSoggettoDrawer.vue'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
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
// Sentinel null = "non popolato" (create mode); array = popolato dal
// backend sul detail (anche [] valido). Distinzione necessaria per il
// fallback compat in SoggettoForm.
const tipiModificabiliIds = ref(null)
const nonEditableFields = ref(null)
// In modifica: la natura com'era all'apertura (la PATCH la manda solo se
// cambia) e se il soggetto ha gia' la riga dei dati societari.
const tipoCaricatoId = ref(null)
const haDatiSocietari = ref(false)

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
  tipiModificabiliIds.value = data.tipi_modificabili_ids ?? null
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
  if (!val) { fgFv.invalidate(); return }

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
    // Reset sentinel a null in create — fallback compat in SoggettoForm
    tipiModificabiliIds.value = null
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
    // ⭐ Un flag che la natura NON ammette (campo nascosto) parte 'N': e' la
    //    regola del DB (A-3, «chi cambia natura porta il flag a N nella stessa
    //    scrittura»), non un valore inventato. Un 'S' rimasto da prima del
    //    guard verrebbe altrimenti rifiutato su un campo che non si vede.
    if (f.split_payment) payload.split_payment = soggetto.showSplitPayment.value ? f.split_payment : 'N'
    if (f.cliente_pa) payload.cliente_pa = soggetto.showClientePa.value ? f.cliente_pa : 'N'
    // La natura, solo se cambiata: i guard la confrontano con flag, forma e
    // titoli IVA (brief-db-dati-fiscali-e-societari-del-soggetto §8.3).
    if (f.tipo_soggetto_dettaglio_id !== tipoCaricatoId.value) {
      payload.tipo_soggetto_dettaglio_id = f.tipo_soggetto_dettaglio_id
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
      :campi-errati="campiErrati"
      :tipi-soggetto="soggetto.tipiSoggetto"
      :is-p-f="soggetto.isPF.value"
      :show-sesso="soggetto.showSesso.value"
      :require-sesso="soggetto.requireSesso.value"
      :show-partita-iva="soggetto.showPartitaIva.value"
      :is-edit="isEdit"
      :disabled="false"
      :tipi-ammessi-ids="tipiAmmessiIds"
      :tipi-modificabili-ids="tipiModificabiliIds"
      :non-editable-fields="nonEditableFields"
      :comune-nascita-item="comuneNascitaItem"
    />

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
        :form="indirizzo.form"
        :is-libera="indirizzo.isLibera.value"
        @update:is-libera="v => indirizzo.isLibera.value = v"
        :tipi-stato="indirizzo.tipiStato.value"
        :stati-lookup="indirizzo.statiLookup"
        :cap-options="indirizzo.capOptions.value"
        :loading-cap="indirizzo.loadingCap.value"
        :auto-clone="indirizzo.autoClone.value"
        @update:auto-clone="v => indirizzo.autoClone.value = v"
        @switch-tipo="indirizzo.switchTipo"
        :indirizzo-warnings="indirizzo.indirizzoWarnings.value"
        :address-not-found="indirizzo.addressNotFound.value"
        :disabled="false"
      />
    </template>

    <!-- Sezione: Dati societari (condizionale) — subito dopo anagrafica/P.IVA -->
    <template v-if="soggetto.showDatiSocietari.value">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_dati_societari') }}</h4>
      </div>
      <DatiSocietariForm
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
    <template v-if="isEdit && (soggetto.showClientePa.value || soggetto.showSplitPayment.value)">
      <div class="app-drawer-section">
        <h4>{{ t('anagrafiche.soggetti.section_dati_fiscali') }}</h4>
      </div>
      <div class="form-grid-2col">
        <div v-if="soggetto.showClientePa.value" class="form-field">
          <label>{{ t('anagrafiche.soggetti.field_cliente_pa') }}</label>
          <Select v-model="soggetto.form.cliente_pa" :options="paOptions"
            option-label="label" option-value="value"
            :invalid="campiErrati.includes('cliente_pa')"
            :disabled="isReadonly" />
        </div>
        <div v-if="soggetto.showSplitPayment.value" class="form-field">
          <label>{{ t('anagrafiche.soggetti.field_split_payment') }}</label>
          <Select v-model="soggetto.form.split_payment" :options="paOptions"
            option-label="label" option-value="value"
            :invalid="campiErrati.includes('split_payment')"
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
    :tipo-soggetto-dettaglio-id="soggetto.form.tipo_soggetto_dettaglio_id"
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
