<script setup>
// Scopo: Componente permessi operatore riutilizzabile.
// Per AREA: il livello dell'area, i suoi oggetti e le sue azioni di processo.
// ℹ️ Lo scope emittenti fiscali NON sta qui: e' nella scheda Dati del drawer
//    operatore (Tid, 2026-10-06) — e' il perimetro dell'operatore, non una
//    regola su area, oggetto o azione.
// Vive nella scheda «Permessi» di OperatoreDrawer (il drawer dedicato dei soli
// permessi, aperto dal kebab della lista, e' stato ritirato il 2026-10-06).
// Reagisce automaticamente al cambio di authUserId.
//
// ⭐ RESTYLE PER AREA 2026-10-04 (brief-db-permessi-tetto-area §7, Tid) —
//    prima la scheda divideva per TIPO (tutte le aree, poi tutte le azioni,
//    poi tutti gli oggetti, ognuno col suo Salva): una pagina lunga, con le
//    informazioni di un'area sparse in tre tabelle. Ora elenco delle aree a
//    sinistra (livello, numero di override, modifiche non salvate, voci
//    limitate dall'area) e l'area scelta a destra. Una tab per area non
//    scalava (14 aree al 2026-09-25). UN SOLO Salva, nel footer del drawer
//    che ospita la scheda (`salva()` esposto): manda le sole sezioni
//    modificate. Il raggruppamento «Trasversali» del §7.2 NON c'e': il
//    catalogo non dice quali aree lo siano, e un elenco scritto qui sarebbe
//    una seconda sede.
//
// ⭐ RISTRUTTURAZIONE 2026-09-05 — le tre tabelle mostrano TUTTE le voci del
//    catalogo, non piu' i soli override. Prima un operatore appena creato
//    apriva tre tabelle VUOTE, da cui non si capiva cosa potesse fare: la
//    schermata mostrava le ECCEZIONI e non lo STATO, mentre il livello che
//    conta nasce da una catena di cinque passi di cui se ne vedeva uno.
//    E' il pattern slot/override gia' adottato sul tab Utilities degli
//    emittenti, qui incarnato dal BB `MatriceOverride`.
// ⛔ NESSUN CAMBIO DI FUNZIONALITA': la semantica dei permessi e' identica.
//    ✅ Il difetto che qui era annotato come aperto — un'area BLOCCATA che
//    non bloccava le sue azioni di processo (analisi-ui-permessi-operatore.md
//    §3) — e' CHIUSO dal 2026-10-04 (brief-db-permessi-tetto-area: il tetto
//    d'area, `script.fn_area_consente_azione`). Riga corretta il 2026-10-31:
//    era rimasta indietro e faceva ripetere il difetto come ancora aperto.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { STATUS_ICONS } from '../../core/constants'
import { listAreeFunzionali, listAzioniProcesso, getModelOverridesLookup } from '../api/amministrazione'
import { LIVELLO_ACCESSO, buildLivelloOptions, getLivelloLabel, getLivelloSeverity } from '../constants'
import { areaConsenteAzione, livelloConTettoArea } from '../tettoArea'
import { oggiAziendaleString } from '../../core/utils/date'
import MatriceOverride from '../../core/components/MatriceOverride.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import ElencoDettaglio from '../../core/components/ElencoDettaglio.vue'
import Select from 'primevue/select'
import Message from 'primevue/message'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'

const { t } = useI18n()
const store = useOperatoriStore()
const notify = useNotify()
const { execute } = useApiHandler()
// Readonly: i controlli di riga e il Salva si spengono con la sola lettura del
// drawer che ospita la scheda.
// ⛔ CUMULATIVA con la prop, e non solo iniettata: il drawer ospite espone una
//    prop `readonly` propria (standard drawer admin), e senza questo la prop
//    si fermerebbe al suo bordo — l'intestazione direbbe «sola lettura» e le
//    tendine dentro sarebbero premibili. Una guardia che sembra presente e non
//    lo è.
const injectedReadonly = useInjectReadonly()

// Lookup via useLookup (non piu' dallo store)
const areeFunzionali = useLookup(listAreeFunzionali, { immediate: true })
const azioniProcesso = useLookup(listAzioniProcesso, { immediate: true })
const modelOverrides = useLookup(getModelOverridesLookup, { immediate: true })

const props = defineProps({
  authUserId: { type: Number, required: true },
  readonly: { type: Boolean, default: false },
  // Visibilita' del drawer che ospita il tab: azzera le fotografie alla
  // chiusura. Default true: il contenuto dei drawer si smonta comunque a
  // drawer chiuso.
  visible: { type: Boolean, default: true }
})

// Multi-face auth: flag SUPER_ADMIN dal detail dell'operatore gestito
// (non dal user corrente auth). Se il detail non e' ancora caricato,
// loadAll() lo fetcha. Banner "admin ha accesso totale" guidato da qui.
// ⚠️ E' il flag SALVATO: toglierlo nei Dati senza salvare non sblocca.
const isSuperAdmin = computed(() => store.currentOperatore?.is_super_admin === true)

// ⭐ Su un SUPER ADMIN il pannello e' in sola lettura (Tid, 2026-10-06): il
//    flag scavalca la catena dei permessi, quindi un override scritto li' non
//    ha effetto — e un pannello modificabile diceva il contrario (un admin ha
//    messo Anagrafiche a «Lettura» su un super admin, e non e' successo
//    niente). Per assegnargli permessi si toglie prima il flag.
const isReadonly = computed(() => props.readonly || injectedReadonly.value || isSuperAdmin.value)

const livelloOptions = buildLivelloOptions(t)

// Stato locale editabile (mantenuto separato dallo store per permettere undo
// logico tra un save e l'altro e per non mutare direttamente lo store).
//
// ⭐ MAPPE indicizzate per chiave, e non piu' array di righe: la lista a video
//    e' il CATALOGO (tutte le aree, tutte le azioni, tutti i model), mentre
//    questi sono i soli override SCRITTI. La presenza della chiave E'
//    l'override; l'assenza e' «vale l'ereditato».
// ⛔ E la distinzione non e' un dettaglio di struttura dati: un livello
//    BLOCCATO **scritto** non e' «nessun override» — batte il profilo del
//    reparto — quindi le due cose non possono collassare in un unico valore.
const overrideAree = ref({})
const overrideAzioni = ref({})
const overrideOggetti = ref({})

// Modifiche non salvate (BB useDrawerFormPreserve): UNA fotografia per
// sezione, perche' ogni sezione ha il SUO endpoint — il Salva unico (`salva`)
// manda solo le sezioni modificate, e un PUT che sostituisce la collezione
// non va mandato per niente. Il drawer padre legge `modificato`/`puoSalvare`,
// salva con `salva` e chiude con `chiudiConConferma` (defineExpose in fondo).
const _vis = { visibile: () => props.visible }
const sezioni = {
  aree: useDrawerFormPreserve(overrideAree, _vis),
  azioni: useDrawerFormPreserve(overrideAzioni, _vis),
  oggetti: useDrawerFormPreserve(overrideOggetti, _vis),
}
const modificato = computed(() => Object.values(sezioni).some(sz => sz.modificato.value))

// Scopo: chiude chiedendo conferma se una sezione ha modifiche (un solo dialog).
function chiudiConConferma(chiudi) {
  const sporca = Object.values(sezioni).find(sz => sz.modificato.value)
  if (sporca) sporca.chiudiConConferma(chiudi)
  else chiudi()
}

// Scopo: Carica tutto lo stato necessario per il componente.
//        Viene chiamato dal watch su authUserId (immediate) e garantisce
//        che currentOperatore e overrideAree/azioni/oggetti siano
//        coerenti con l'utente passato.
// ⛔ Fino al 2026-10-23 il `Promise.all` stava fuori da `execute`: una lettura
//    rifiutata finiva in una unhandled rejection, e il pannello restava vuoto
//    senza un motivo.
async function loadAll(userId) {
  if (!userId) return
  const needDetail = store.currentOperatore?.auth_user_id !== userId
  const esito = await execute(() => Promise.all([
    needDetail ? store.fetchDetail(userId) : Promise.resolve(),
    store.fetchOverrideAree(userId),
    store.fetchOverrideAzioni(userId),
    store.fetchOverrideOggetti(userId),
    // La colonna «ereditato»: senza, il pannello direbbe MENO di quello di
    // prima — mostrerebbe 59 righe senza dire da dove viene il loro valore.
    store.fetchPermessiEreditati(userId),
    // Il tetto d'area: quali voci vale il loro override e quali l'area ferma.
    store.fetchPermessiEffettivi(userId),
    // Il numero di override per area: la sede unica a DB (D-4 del brief
    // riepilogo-permessi), la stessa della lista operatori.
    store.fetchRiepilogoAree(userId),
  ]))
  if (esito === null) return
  syncLocal()
  Object.values(sezioni).forEach(sz => sz.fissa())
}

watch(() => props.authUserId, loadAll, { immediate: true })

// Chiave di un oggetto override: `app_label.model_name`. ⛔ SEDE UNICA, e va
// usata anche dal template: la stessa stringa indicizza la mappa degli
// override, il lookup dei model riservati e la riga del catalogo. Tre posti che
// la ricostruiscono a mano sono tre posti in cui può divergere — e una chiave
// che non combacia non dà nessun errore: la riga risulta «senza override» e il
// salvataggio la lascia dov'è.
const chiaveOggetto = (o) => `${o.app_label}.${o.model_name}`

function syncLocal() {
  overrideAree.value = Object.fromEntries(
    store.overrideAree.map(a => [a.area_id, { ...a }])
  )
  overrideAzioni.value = Object.fromEntries(
    store.overrideAzioni.map(a => [a.azione_id, { ...a }])
  )
  overrideOggetti.value = Object.fromEntries(
    store.overrideOggetti.map(o => [chiaveOggetto(o), { ...o }])
  )
}

// ═══ L'EREDITATO — cosa l'operatore ha GIA' dal profilo ════════════════════
// ⚠️ Voce assente = nessun profilo la copre ⇒ vale il DEFAULT (BLOCCATO per le
//    aree, azione negata). Il `?? ` qui sotto e' quel default, non un ripiego
//    difensivo: e' la quinta regola della catena di risoluzione.
const ereditatoAree = computed(() =>
  Object.fromEntries((store.permessiEreditati.aree || []).map(a => [a.area_id, a]))
)
const ereditatoAzioni = computed(() =>
  Object.fromEntries((store.permessiEreditati.azioni || []).map(a => [a.azione_id, a]))
)

const livelloEreditatoArea = (areaId) =>
  ereditatoAree.value[areaId]?.livello ?? LIVELLO_ACCESSO.BLOCCATO
const abilitataEreditataAzione = (azioneId) =>
  ereditatoAzioni.value[azioneId]?.abilitata ?? false

// Da dove viene il valore ereditato: il nome del profilo, o «default» quando
// nessun profilo copre la voce. ⭐ Distinguere le due cose e' la ragione per
// cui la colonna esiste: «bloccato perche' qualcuno l'ha deciso» e «bloccato
// perche' nessuno ha detto niente» hanno rimedi diversi.
const fonteArea = (areaId) =>
  ereditatoAree.value[areaId]?.profilo_nome ?? t('amministrazione.ereditato_default')
const fonteAzione = (azioneId) =>
  ereditatoAzioni.value[azioneId]?.profilo_nome ?? t('amministrazione.ereditato_default')

// ⚠️ Per un OGGETTO l'ereditato e' il livello della sua AREA, non un livello di
//    profilo: `config.profili_accesso_oggetti` non esiste. La catena e'
//    override oggetto → override area → profilo dell'area → BLOCCATO, quindi
//    qui si guarda prima un eventuale override d'area e poi il suo ereditato.
const livelloEreditatoOggetto = (voce) =>
  overrideAree.value[voce.area_id]?.livello ?? livelloEreditatoArea(voce.area_id)
const fonteOggetto = (voce) =>
  overrideAree.value[voce.area_id]
    ? t('amministrazione.ereditato_da_override_area')
    : t('amministrazione.ereditato_da_area', { area: voce.area_descrizione })

// ═══ IL TETTO D'AREA — cosa l'area ferma (brief-db-permessi-tetto-area) ════
// Un permesso specifico puo' solo restringere quello della sua area: un
// override che abilita un'azione, o allarga un oggetto, sotto un'area che non
// lo consente resta scritto e DORMIENTE (D-3) — torna valido se l'area si
// riapre. Senza l'etichetta il pannello mostrerebbe «abilitata» su un'azione
// che il DB nega.
//
// ⭐ DUE SORGENTI, e la regola per sceglierle e' una sola:
//    • voce senza modifiche non salvate (ne' sua ne' della sua area) → il DB,
//      `permessiEffettivi` (`fn_get_permessi_effettivi_*`, la catena dei
//      resolver). Lo store lo ricarica dopo ogni salvataggio;
//    • voce con modifiche non salvate → ANTEPRIMA (§7.3, Tid 2026-10-04):
//      i valori a video passati alle copie FE delle due regole pure
//      (`tettoArea.js`), e l'etichetta lo dichiara. Ogni pezzo che a video
//      non e' cambiato si prende comunque dal DB.
// ⛔ Niente anteprima per un super admin o per un operatore senza veste
//    attiva: li' il DB risponde prima del tetto (bypass / tutto BLOCCATO), e
//    una ricostruzione a video direbbe il falso. Vale il DB.
const effettiviAzioni = computed(() =>
  Object.fromEntries((store.permessiEffettivi.azioni || []).map(a => [a.azione_id, a]))
)
const effettiviOggetti = computed(() =>
  Object.fromEntries((store.permessiEffettivi.oggetti || []).map(o => [chiaveOggetto(o), o]))
)
// Gli override SALVATI, per sapere cosa a video e' cambiato.
const salvatiAree = computed(() =>
  Object.fromEntries(store.overrideAree.map(a => [a.area_id, a]))
)
const salvateAzioni = computed(() =>
  Object.fromEntries(store.overrideAzioni.map(a => [a.azione_id, a]))
)
const salvatiOggetti = computed(() =>
  Object.fromEntries(store.overrideOggetti.map(o => [chiaveOggetto(o), o]))
)

const senzaAnteprima = computed(() =>
  isSuperAdmin.value || store.currentOperatore?.veste_attiva === false
)

// Un override conta oggi solo dentro la sua validita' (come `validita @>
// CURRENT_DATE` a DB). Le date arrivano `YYYY-MM-DD`: il confronto fra
// stringhe e' quello fra date.
function _validoOggi(o) {
  const oggi = oggiAziendaleString()
  return (!o.valido_dal || o.valido_dal <= oggi) && (!o.valido_al || o.valido_al >= oggi)
}

// Il livello dell'area per il tetto: quello del DB, salvo un override d'area
// cambiato a video. `{ livello, modificato }`.
function _areaPerTetto(areaId, livelloAreaDb) {
  const o = overrideAree.value[areaId]
  if (o?.livello === salvatiAree.value[areaId]?.livello) {
    return { livello: livelloAreaDb, modificato: false }
  }
  const livello = o && _validoOggi(o) ? o.livello : livelloEreditatoArea(areaId)
  return { livello, modificato: true }
}

// Scopo: Stato del tetto di un'azione: `{ limitata, anteprima }` o null.
function statoTettoAzione(azioneId) {
  const e = effettiviAzioni.value[azioneId]
  if (!e) return null
  if (senzaAnteprima.value) return { limitata: e.limitata_da_area, anteprima: false }
  const area = _areaPerTetto(e.area_id, e.livello_area)
  const o = overrideAzioni.value[azioneId]
  const azioneModificata = o?.abilitata !== salvateAzioni.value[azioneId]?.abilitata
  if (!area.modificato && !azioneModificata) {
    return { limitata: e.limitata_da_area, anteprima: false }
  }
  let specifica = e.abilitata_specifica
  if (azioneModificata) {
    specifica = o && _validoOggi(o) ? o.abilitata : abilitataEreditataAzione(azioneId)
  }
  return {
    limitata: specifica && !areaConsenteAzione(area.livello, e.livello_minimo_area),
    anteprima: true,
    livelloArea: area.livello,
  }
}

// Scopo: Stato del tetto di un oggetto: `{ limitato, livello, anteprima }` o null.
function statoTettoOggetto(voce) {
  const k = chiaveOggetto(voce)
  const e = effettiviOggetti.value[k]
  if (!e) return null
  if (senzaAnteprima.value) return { limitato: e.limitato_da_area, livello: e.livello, anteprima: false }
  const area = _areaPerTetto(voce.area_id, e.livello_area)
  const o = overrideOggetti.value[k]
  const oggettoModificato = o?.livello !== salvatiOggetti.value[k]?.livello
  if (!area.modificato && !oggettoModificato) {
    return { limitato: e.limitato_da_area, livello: e.livello, anteprima: false }
  }
  let override = e.livello_override
  if (oggettoModificato) override = o && _validoOggi(o) ? o.livello : null
  const livello = livelloConTettoArea(override, area.livello)
  return { limitato: livello !== (override ?? area.livello), livello, anteprima: true }
}

const _suffissoAnteprima = (stato) =>
  stato.anteprima ? ` ${t('amministrazione.tetto_anteprima')}` : ''

const tettoAzione = (azioneId) => {
  const stato = statoTettoAzione(azioneId)
  if (!stato?.limitata) return null
  const e = effettiviAzioni.value[azioneId]
  return t('amministrazione.limitata_da_area_azione', {
    minimo: getLivelloLabel(t, e.livello_minimo_area),
    area: getLivelloLabel(t, stato.livelloArea ?? e.livello_area),
  }) + _suffissoAnteprima(stato)
}
const tettoOggetto = (voce) => {
  const stato = statoTettoOggetto(voce)
  if (!stato?.limitato) return null
  return t('amministrazione.limitato_da_area_oggetto', { livello: getLivelloLabel(t, stato.livello) })
    + _suffissoAnteprima(stato)
}

// ⛔ IL SALVATAGGIO MANDA SOLO LE RIGHE CON OVERRIDE VERO, e i mapper partono
//    dai VALORI delle mappe — mai dalle voci del catalogo.
//    Il `PUT` sostituisce l'intera collezione (`DELETE WHERE auth_user_id` +
//    reinsert): mandare tutte le voci a video materializzerebbe 59 override
//    reali e cambierebbe il comportamento di ogni utente con un profilo, cioe'
//    farebbe per sbaglio il cambio di funzionalita' che questa ristrutturazione
//    esclude. Un BLOCCATO scritto non e' «nessun override»: batte il profilo.
const _toAreaItem = (a) => ({
  area_id: a.area_id,
  livello: a.livello,
  motivo: a.motivo || null,
  valido_dal: a.valido_dal || null,
  valido_al: a.valido_al || null,
})

const _toAzioneItem = (a) => ({
  azione_id: a.azione_id,
  abilitata: a.abilitata,
  motivo: a.motivo || null,
  valido_dal: a.valido_dal || null,
  valido_al: a.valido_al || null,
})

const _toOggettoItem = (o) => ({
  app_label: o.app_label,
  model_name: o.model_name,
  livello: o.livello,
  motivo: o.motivo || null,
  valido_dal: o.valido_dal || null,
  valido_al: o.valido_al || null,
})

// ═══ IL SALVA UNICO ═══════════════════════════════════════════════════════
// Una modifica in un'area tocca spesso piu' di un endpoint (livello, oggetti,
// azioni): con un Salva per sezione l'admin doveva sapere quali premere. Qui
// si manda ogni sezione MODIFICATA, nell'ordine, e ognuna si fissa appena il
// suo PUT riesce: se la seconda fallisce, la prima resta salvata e la seconda
// resta da salvare — lo dice il pannello, sezione per sezione.
// ⛔ Fino al 2026-10-23 il giro stava in un try/catch col `catch` vuoto,
//    «gestito dall'interceptor axios globale»: l'interceptor di `core/api.js`
//    non mostra toast, e un PUT rifiutato restava muto. Ora il giro intero passa
//    da `execute` (che accetta anche le azioni di uno store): la sezione che
//    fallisce dice il motivo, quelle gia' riuscite restano fissate.
// ⭐ Effettivi e riepilogo si rileggono DOPO il giro, una volta sola, e anche
//    se una sezione e' fallita: quelle salvate prima li hanno cambiati. Una
//    rilettura che fallisce lo dice da se' e non tocca l'esito del Salva.
const salvando = ref(false)

function aggiornaDerivati(userId) {
  return execute(() => Promise.all([
    store.fetchPermessiEffettivi(userId),
    store.fetchRiepilogoAree(userId),
  ]))
}

const puoSalvare = computed(() => !isReadonly.value && modificato.value)

// Scopo: Salva le sezioni modificate; `true` se tutte riescono.
async function salva() {
  if (!puoSalvare.value || salvando.value) return false
  salvando.value = true
  const id = props.authUserId
  let salvate = 0
  try {
    const esito = await execute(async () => {
      if (sezioni.aree.modificato.value) {
        await store.saveOverrideAree(id, Object.values(overrideAree.value).map(_toAreaItem))
        sezioni.aree.fissa()
        salvate++
      }
      if (sezioni.azioni.modificato.value) {
        await store.saveOverrideAzioni(id, Object.values(overrideAzioni.value).map(_toAzioneItem))
        sezioni.azioni.fissa()
        salvate++
      }
      if (sezioni.oggetti.modificato.value) {
        await store.saveOverrideOggetti(id, Object.values(overrideOggetti.value).map(_toOggettoItem))
        sezioni.oggetti.fissa()
        salvate++
      }
      return true
    })
    // ⚠️ Prima del `return` sul fallimento: una sezione salvata prima di quella
    //    rifiutata ha gia' cambiato effettivi e riepilogo.
    if (salvate > 0) await aggiornaDerivati(id)
    if (esito === null) return false
    notify.success(t('notifications.save_success'))
    return true
  } finally {
    salvando.value = false
  }
}

// ═══ I DUE VERBI ══════════════════════════════════════════════════════════
// `set` scrive l'override sulla riga; `reset` lo TOGLIE e la riga torna a
// seguire l'ereditato. ⭐ Non sono la stessa cosa scritta in due modi: un
// override che ripete il valore ereditato CONGELA la riga — da quel momento
// non segue piu' il profilo, quindi il giorno che il reparto cambia livello
// quell'utente resta indietro, e nessuno lo segnala.
// Rimozione per chiave, con riassegnazione dell'oggetto: mutare in-place con
// `delete` non e' reattivo su un `ref` di oggetto semplice.
function _senzaChiave(mappa, chiave) {
  return Object.fromEntries(
    Object.entries(mappa).filter(([k]) => String(k) !== String(chiave))
  )
}

const resetArea = (areaId) => { overrideAree.value = _senzaChiave(overrideAree.value, areaId) }
const resetAzione = (azioneId) => { overrideAzioni.value = _senzaChiave(overrideAzioni.value, azioneId) }
const resetOggetto = (chiave) => { overrideOggetti.value = _senzaChiave(overrideOggetti.value, chiave) }

// ⚠️ Un valore NULLO non si scrive: significa «nessuna scelta», ed è il
//    ritorno al valore ereditato — cioè un `reset`, non un override con dentro
//    `null`. Senza questa guardia una `Select` svuotata manderebbe al backend
//    un livello nullo, che è un errore là dove qui era solo un click di troppo.
function setOverrideArea(areaId, livello) {
  if (livello == null) return resetArea(areaId)
  overrideAree.value = {
    ...overrideAree.value,
    [areaId]: { ...overrideAree.value[areaId], area_id: areaId, livello },
  }
}

function setOverrideAzione(azioneId, abilitata) {
  if (abilitata == null) return resetAzione(azioneId)
  overrideAzioni.value = {
    ...overrideAzioni.value,
    [azioneId]: { ...overrideAzioni.value[azioneId], azione_id: azioneId, abilitata },
  }
}

function setOverrideOggetto(voce, livello) {
  const k = chiaveOggetto(voce)
  if (livello == null) return resetOggetto(k)
  overrideOggetti.value = {
    ...overrideOggetti.value,
    [k]: {
      ...overrideOggetti.value[k],
      app_label: voce.app_label,
      model_name: voce.model_name,
      livello,
    },
  }
}

// ═══ L'AVVISO: un override che ripete l'ereditato ═════════════════════════
// Non serve a niente e congela la riga. E' il guadagno vero della colonna
// «ereditato»: si vede confrontando due valori che ora sono entrambi in pagina.
const avvisoArea = (area) => {
  const o = overrideAree.value[area.id]
  return o && o.livello === livelloEreditatoArea(area.id)
    ? t('amministrazione.override_ridondante')
    : null
}
const avvisoAzione = (az) => {
  const o = overrideAzioni.value[az.id]
  return o && o.abilitata === abilitataEreditataAzione(az.id)
    ? t('amministrazione.override_ridondante')
    : null
}
const avvisoOggetto = (voce) => {
  const o = overrideOggetti.value[chiaveOggetto(voce)]
  return o && o.livello === livelloEreditatoOggetto(voce)
    ? t('amministrazione.override_ridondante')
    : null
}

// Le VOCI della matrice oggetti: i model configurabili
// (`can_override === true`), piu' quelli che hanno GIA' un override.
// ⛔ Il secondo insieme non e' un di piu': un model diventato riservato dopo
//    che qualcuno gli aveva messo un override sparirebbe dalla vista mentre la
//    sua riga resta scritta e viene RISALVATA a ogni salvataggio — invisibile e
//    viva. Mostrandolo (con il controllo disabilitato e il motivo a tooltip)
//    resta almeno rimovibile.
const vociOggetti = computed(() => {
  const conOverride = new Set(Object.keys(overrideOggetti.value))
  return modelOverrides.items.value
    .filter(m => m.can_override === true || conOverride.has(chiaveOggetto(m)))
    .map(m => ({
      ...m,
      label: chiaveOggetto(m)
    }))
})

// Scopo: Mappa indicizzata `(app_label, model_name) -> {can_override, reason}`
//        per evitare scansioni lineari nelle template cells. Ricomputata
//        solo quando l'array di model cambia.
const modelOverrideIndex = computed(() => {
  const m = new Map()
  for (const row of modelOverrides.items.value) {
    m.set(chiaveOggetto(row), row)
  }
  return m
})

// Scopo: Per le righe pre-esistenti che puntano a un model diventato
//        riservato (drift dati storico), risolve la chiave i18n del motivo
//        per mostrarla come tooltip sul Select disabilitato. Lookup O(1)
//        via la mappa indicizzata.
function modelOverrideReason(row) {
  if (!row.app_label || !row.model_name) return null
  const entry = modelOverrideIndex.value.get(chiaveOggetto(row))
  if (!entry || entry.can_override === true) return null
  return entry.reason ? t(entry.reason) : null
}

// Le tre opzioni di override di un'azione. ⚠️ Un `ToggleSwitch` qui NON basta:
// avrebbe due stati per una realta' che ne ha tre — «abilitata», «negata» e
// «non impostata, vale il profilo» — e il terzo e' quello che si perde.
const azioneOptions = computed(() => [
  { label: t('amministrazione.azione_abilitata'), value: true },
  { label: t('amministrazione.azione_negata'), value: false },
])

// ═══ LA NAVIGAZIONE PER AREA ══════════════════════════════════════════════
// ⭐ Azioni e oggetti APPARTENGONO a un'area (`azioni_processo.area_id`,
//    `area_model_overrides.area_id`): raggrupparli e' rendere visibile una
//    relazione del modello, e da quando l'area e' un tetto (§3 della guida di
//    architettura) e' anche la gerarchia che il DB applica.
// ⛔ Ricerca e filtro restringono la VISTA, mai il modello: il Salva parte
//    dalle mappe degli override, non dalle voci a video.

// La vista si azzera a ogni apertura e a ogni cambio di operatore.
const areaScelta = ref(null)
const termine = ref('')
const soloOverride = ref(false)

watch(() => [props.visible, props.authUserId], ([visibile]) => {
  if (!visibile) return
  areaScelta.value = null
  termine.value = ''
  soloOverride.value = false
})

const azioniPerArea = computed(() => {
  const m = {}
  for (const az of azioniProcesso.items.value) (m[az.area_id] ||= []).push(az)
  return m
})
const oggettiPerArea = computed(() => {
  const m = {}
  for (const o of vociOggetti.value) (m[o.area_id] ||= []).push(o)
  return m
})

const _diversa = (a, b, campo) => a?.[campo] !== b?.[campo]
const azioneModificata = (az) =>
  _diversa(overrideAzioni.value[az.id], salvateAzioni.value[az.id], 'abilitata')
const oggettoModificato = (o) =>
  _diversa(overrideOggetti.value[chiaveOggetto(o)], salvatiOggetti.value[chiaveOggetto(o)], 'livello')

// Il livello dell'area A VIDEO: l'override se c'e', altrimenti l'ereditato.
const livelloAreaVideo = (areaId) =>
  overrideAree.value[areaId]?.livello ?? livelloEreditatoArea(areaId)

// Scopo: Riassunto di un'area per l'elenco a sinistra.
// Il numero di override per area SALVATI: da `fn_get_permessi_riepilogo_aree`
// (sede unica, la legge anche la lista operatori), ricaricato a ogni Salva.
const overrideSalvatiPerArea = computed(() =>
  Object.fromEntries(store.riepilogoAree.map(r => [r.area_id, r.override_count]))
)

// ⭐ DUE SORGENTI per il numero, con la regola del tetto: un'area senza
//    modifiche non salvate legge il DB; un'area modificata conta a video gli
//    override che il Salva scriverebbe — e' l'ANTEPRIMA, e come quella del
//    tetto vale solo finche' non si salva. Fino al 2026-10-06 il numero era
//    sempre contato a video: una seconda sede della regola, che la lista
//    operatori non vedeva.
function riassuntoArea(area) {
  const azioni = azioniPerArea.value[area.id] || []
  const oggetti = oggettiPerArea.value[area.id] || []
  const modificata = _diversa(overrideAree.value[area.id], salvatiAree.value[area.id], 'livello')
    || azioni.some(azioneModificata)
    || oggetti.some(oggettoModificato)
  const conOverride = modificata
    ? (overrideAree.value[area.id] ? 1 : 0)
      + azioni.filter(az => overrideAzioni.value[az.id]).length
      + oggetti.filter(o => overrideOggetti.value[chiaveOggetto(o)]).length
    : (overrideSalvatiPerArea.value[area.id] ?? 0)
  const limitate = azioni.filter(az => statoTettoAzione(az.id)?.limitata).length
    + oggetti.filter(o => statoTettoOggetto(o)?.limitato).length
  return { conOverride, modificata, limitate }
}
const riassunti = computed(() =>
  Object.fromEntries(areeFunzionali.items.value.map(a => [a.id, riassuntoArea(a)]))
)

const _q = computed(() => termine.value.trim().toLowerCase())
const _corrisponde = (...testi) =>
  testi.some(x => typeof x === 'string' && x.toLowerCase().includes(_q.value))
const _areaCorrisponde = (area) => _corrisponde(area.descrizione, area.codice)
const _azioneCorrisponde = (az) => _corrisponde(az.descrizione, az.permission_codename)
const _oggettoCorrisponde = (o) => _corrisponde(o.label, o.model_name, o.app_label)

// Scopo: Le voci di un'area che la vista mostra (ricerca + «solo con override»).
//        Se la ricerca colpisce l'area, si mostrano tutte le sue voci.
function vociVisibili(area, voci, corrisponde, haOverride, modificata) {
  let out = voci
  if (_q.value && !_areaCorrisponde(area)) out = out.filter(corrisponde)
  // ⚠️ Una voce modificata e non salvata resta a vista anche col filtro: un
  //    reset la farebbe sparire sotto le mani di chi la sta cambiando.
  if (soloOverride.value) out = out.filter(v => haOverride(v) || modificata(v))
  return out
}
const azioniVisibili = (area) => vociVisibili(
  area, azioniPerArea.value[area.id] || [], _azioneCorrisponde,
  az => !!overrideAzioni.value[az.id], azioneModificata,
)
const oggettiVisibili = (area) => vociVisibili(
  area, oggettiPerArea.value[area.id] || [], _oggettoCorrisponde,
  o => !!overrideOggetti.value[chiaveOggetto(o)], oggettoModificato,
)

const areeVisibili = computed(() =>
  areeFunzionali.items.value.filter(area => {
    const r = riassunti.value[area.id]
    if (soloOverride.value && !r.conOverride && !r.modificata) return false
    if (!_q.value) return true
    return _areaCorrisponde(area)
      || azioniVisibili(area).length > 0
      || oggettiVisibili(area).length > 0
  })
)

// L'area mostrata (la scelta se ancora a vista, altrimenti la prima a vista)
// la decide `ElencoDettaglio`: qui resta solo la SCELTA, che si azzera sopra.

defineExpose({ modificato, chiudiConConferma, salva, puoSalvare, salvando })
</script>

<template>
  <div class="permessi-tab">
    <Message v-if="isSuperAdmin" severity="info" :closable="false">
      {{ t('amministrazione.admin_full_access') }}
    </Message>

    <p class="app-permessi-nota">{{ t('amministrazione.permessi_nota') }}</p>

    <!-- Per AREA (`ElencoDettaglio`): l'elenco delle aree a sinistra, il colpo
         d'occhio che prima era la prima tabella, e l'area scelta a destra —
         il suo livello, i suoi oggetti, le sue azioni. -->
    <ElencoDettaglio
      v-model="areaScelta"
      :voci="areeVisibili"
      :chiave="a => a.id"
      :etichetta="a => a.descrizione"
      :modificata="a => riassunti[a.id].modificata"
      :testo-vuoto="t('amministrazione.permessi_nessuna_area')"
    >
      <template #filtri>
        <InputText
          v-model="termine"
          :placeholder="t('amministrazione.permessi_cerca')"
        />
        <FiltroToggle
          v-model="soloOverride"
          :label="t('amministrazione.permessi_solo_override')"
        />
      </template>

      <template #segni="{ voce: area }">
        <i
          v-if="riassunti[area.id].limitate"
          v-tooltip.top="t('amministrazione.permessi_area_limitate', { n: riassunti[area.id].limitate })"
          :class="[STATUS_ICONS.ERRORE, 'app-permessi-tetto-icona']"
        />
        <Badge
          v-if="riassunti[area.id].conOverride"
          v-tooltip.top="t('amministrazione.permessi_area_override')"
          :value="riassunti[area.id].conOverride"
          severity="info"
        />
        <Tag
          :value="getLivelloLabel(t, livelloAreaVideo(area.id))"
          :severity="getLivelloSeverity(livelloAreaVideo(area.id))"
        />
      </template>

      <template #dettaglio="{ voce: area }">
          <h4>{{ area.descrizione }}</h4>

          <MatriceOverride
            :voci="[area]"
            :readonly="isReadonly"
            :chiave="a => a.id"
            :overrides="overrideAree"
            :label-voce="t('amministrazione.permessi_livello_area')"
            :avviso="avvisoArea"
            @reset="resetArea"
          >
            <template #voce>{{ t('amministrazione.permessi_livello_area') }}</template>
            <template #ereditato="{ voce }">
              {{ getLivelloLabel(t, livelloEreditatoArea(voce.id)) }}
              <small class="app-permessi-fonte">{{ fonteArea(voce.id) }}</small>
            </template>
            <template #override="{ voce, valore }">
              <Select
                :model-value="valore?.livello ?? null"
                :options="livelloOptions"
                option-label="label"
                option-value="value"
                :placeholder="t('amministrazione.override_non_impostato')"
                :disabled="isReadonly"
                @update:model-value="v => setOverrideArea(voce.id, v)"
              />
            </template>
          </MatriceOverride>

          <template v-if="oggettiVisibili(area).length">
            <h5>{{ t('amministrazione.permessi_oggetti_area') }}</h5>
            <MatriceOverride
              :voci="oggettiVisibili(area)"
              :readonly="isReadonly"
              :chiave="chiaveOggetto"
              :overrides="overrideOggetti"
              :label-voce="t('amministrazione.col_model')"
              :avviso="avvisoOggetto"
              @reset="resetOggetto"
            >
              <template #voce="{ voce }">{{ voce.label }}</template>
              <template #ereditato="{ voce }">
                {{ getLivelloLabel(t, livelloEreditatoOggetto(voce)) }}
                <small class="app-permessi-fonte">{{ fonteOggetto(voce) }}</small>
              </template>
              <template #override="{ voce, valore }">
                <span v-tooltip.top="modelOverrideReason(voce)">
                  <Select
                    :model-value="valore?.livello ?? null"
                    :options="livelloOptions"
                    option-label="label"
                    option-value="value"
                    :placeholder="t('amministrazione.override_non_impostato')"
                    :disabled="isReadonly || !!modelOverrideReason(voce)"
                    @update:model-value="v => setOverrideOggetto(voce, v)"
                  />
                </span>
                <small v-if="tettoOggetto(voce)" class="app-permessi-tetto">{{ tettoOggetto(voce) }}</small>
              </template>
            </MatriceOverride>
          </template>

          <template v-if="azioniVisibili(area).length">
            <h5>{{ t('amministrazione.permessi_azioni_area') }}</h5>
            <MatriceOverride
              :voci="azioniVisibili(area)"
              :readonly="isReadonly"
              :chiave="a => a.id"
              :overrides="overrideAzioni"
              :label-voce="t('amministrazione.col_azione')"
              :avviso="avvisoAzione"
              @reset="resetAzione"
            >
              <template #voce="{ voce }">{{ voce.descrizione }}</template>
              <template #ereditato="{ voce }">
                {{ abilitataEreditataAzione(voce.id) ? t('amministrazione.azione_abilitata') : t('amministrazione.azione_negata') }}
                <small class="app-permessi-fonte">{{ fonteAzione(voce.id) }}</small>
              </template>
              <template #override="{ voce, valore, haOverride }">
                <Select
                  :model-value="haOverride ? valore.abilitata : null"
                  :options="azioneOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('amministrazione.override_non_impostato')"
                  :disabled="isReadonly"
                  @update:model-value="v => setOverrideAzione(voce.id, v)"
                />
                <small v-if="tettoAzione(voce.id)" class="app-permessi-tetto">{{ tettoAzione(voce.id) }}</small>
              </template>
            </MatriceOverride>
          </template>

          <p
            v-if="!(oggettiPerArea[area.id] || []).length && !(azioniPerArea[area.id] || []).length"
            class="app-permessi-nota"
          >
            {{ t('amministrazione.permessi_area_senza_voci') }}
          </p>
      </template>
    </ElencoDettaglio>
  </div>
</template>

<style scoped>
.permessi-tab {
  padding: 0.5rem 0;
}
h4 {
  margin: 0 0 0.5rem;
}
h5 {
  margin: 1rem 0 0.5rem;
}
.app-permessi-nota {
  font-size: 0.85rem;
  color: var(--app-text-muted);
  margin-bottom: 0.75rem;
}
/* La fonte del valore ereditato: sta sotto il livello, non accanto — la
   domanda «quanto» viene prima della domanda «da dove». */
.app-permessi-fonte {
  display: block;
  color: var(--app-text-muted);
}
/* `.app-permessi-tetto` (la frase del tetto sotto la tendina) e' globale in
   main.css dal 2026-10-31: la usa anche il profilo del reparto. */
</style>
