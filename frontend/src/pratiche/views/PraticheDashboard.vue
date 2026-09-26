<script setup>
// Scopo: Dashboard pratiche master-detail (SearchTable + roadmap percorso).
// La coda lavoro ("Le mie attività") vive ora nella home (PraticheHome); qui
// resta la sola lista pratiche con il percorso della pratica selezionata.
// Adattabile ai piccoli schermi (niente larghezza fissa).
// Riusa: PraticheSearchTable, PraticaPercorso, PraticaDrawer, FlussoDrawer.
import { ref, shallowRef, computed, watch, onMounted, onActivated, onUnmounted, nextTick, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { provideTechnicalMode } from '../../core/composables/useTechnicalMode'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS, READONLY_DOMAINS, STATI_PRATICA_TERMINALI, STATO_FLUSSO } from '../../core/constants'
import { usePraticheStore } from '../stores/pratiche'
import PraticheSearchTable from '../components/PraticheSearchTable.vue'
import PraticaPercorso from '../components/PraticaPercorso.vue'
import PraticaDrawer from '../components/PraticaDrawer.vue'
import FlussoDrawer from '../components/FlussoDrawer.vue'
import { getUiActivity } from '../uiActivityRegistry'
import { getFlusso, getPraticaDiFlusso, createFlusso, cambiaStatoFlusso } from '../api/pratiche-api'

const { t } = useI18n()
const route = useRoute()
// Serve a ripulire il deep-link `?flusso_id=` dopo averlo applicato.
const router = useRouter()
const store = usePraticheStore()
const drawer = useDrawerState()

// Deep-link dalla home launcher (PraticheHome): la home non esegue azioni di
// business, apre la dashboard "in uno stato preimpostato" via query param.
// - tipo_prestazione_id → filtro tipo attivo; il valore 0 azzera la lente
//   ("Tutte le pratiche"); param assente = non toccare (navigazione da menu).
// - pratica_id (+flusso_id) → selezione pratica + percorso (stessa semantica
//   del click in coda).
// ⚠️ KeepAlive (AppLayout, key=$route.path): la dashboard viene messa in cache
// e ri-attivata senza remount — setup/onMounted girano UNA volta sola. I
// deep-link si applicano quindi in onActivated (fired anche al primo mount),
// in modo idempotente. Il filtro tipo e' pero' anticipato ANCHE nel setup:
// al primo mount la SearchTable figlia inizializza i Select da store.filters
// nel proprio setup (che gira dopo questo) e fa la fetch eager gia' filtrata.
function _queryId(name) {
  // vue-router: param ripetuto → array; prendi il primo. NaN/negativi → null.
  const raw = route.query[name]
  const v = Number(Array.isArray(raw) ? raw[0] : raw)
  return raw != null && Number.isInteger(v) && v >= 0 ? v : null
}

// Scopo: applica il deep-link del filtro tipo. `refetch` true quando la lista
// puo' essere gia' stata caricata (ri-attivazioni): la SearchTable in cache
// non rifetcha da sola.
function applyTipoDeepLink({ refetch }) {
  const tipoId = _queryId('tipo_prestazione_id')
  if (tipoId == null) return
  const next = tipoId > 0 ? tipoId : null // 0 = azzera la lente
  if (store.filters.tipo_prestazione_id === next) return
  store.filters.tipo_prestazione_id = next
  store.filters.offset = 0
  if (refetch) store.fetchList()
}

// Scopo: seleziona la pratica e assicura che il percorso sia caricato.
// ⚠️ I due rami NON sono equivalenti, e la differenza non si vede a occhio:
// cambiare `selectedPraticaId` fa partire un watch che carica il percorso, ma a
// PARITA' di pratica quel watch non scatta — e il carico va chiesto a mano,
// altrimenti un rientro sulla stessa pratica mostrerebbe un percorso stantio.
// Estratto alla 2a copia (regola del 2): lo usano i due deep-link qui sotto.
function selezionaPratica(praticaId) {
  if (store.selectedPraticaId !== praticaId) {
    store.selectedPraticaId = praticaId // il watch carica il percorso
  } else {
    loadPercorsoPratica(praticaId)
  }
}

// Scopo: applica il deep-link di selezione pratica (+flusso dalla coda home).
// La coda lavoro della home (PraticheHome) naviga qui con pratica_id [+flusso_id]:
// selezioniamo la pratica e ne carichiamo il percorso. Il flusso_id viene tenuto
// in `selectedFlussoId` (stato dashboard) per evidenziare lo step d'origine.
// Ricarica il percorso anche a parita' di pratica (freshness su ri-attivazione).
function applyPraticaDeepLink() {
  const praticaId = _queryId('pratica_id')
  if (!praticaId) return
  selectedFlussoId.value = _queryId('flusso_id') || null
  selezionaPratica(praticaId)
}

// Scopo: applica il deep-link quando arriva il SOLO `flusso_id`.
//
// ⭐ DEEP-LINK DAL SOLO `flusso_id`, senza la pratica (2026-08-24).
//
// La coda della home arriva sempre con `pratica_id` + `flusso_id`, perche' la
// riga li ha entrambi. Ma un flusso puo' essere nominato DA FUORI da chi ha in
// mano il solo id: il primo caso reale e' il BERSAGLIO di un errore
// (`E_FLUSSI_GIA_ASSEGNATO`, `E_FLUSSI_PRESA_CARICO_STATO_ERRATO`), dove il
// database scrive `FLUSSO:<id>` e nient'altro — la pratica non e' cio' di cui
// l'errore parla.
//
// ⚠️ Prima, `applyPraticaDeepLink` usciva subito (`if (!praticaId) return`) e un
// `?flusso_id=` da solo non faceva NIENTE, in silenzio: il modo peggiore di non
// funzionare. Qui si chiede al backend dove vive il flusso e si prosegue dalla
// porta di sempre.
//
// ⚠️ `silent`: se il flusso non esiste o la RLS lo nasconde, l'operatore resta
// dov'e' senza un toast che parla di un id che non ha mai visto. E' il degrado
// dichiarato del bersaglio — un'offerta, non una promessa.
async function applyFlussoDeepLink() {
  const flussoId = _queryId('flusso_id')
  if (!flussoId || _queryId('pratica_id')) return
  // ⚠️ IL PARAM SI RIPULISCE SUBITO, e prima della chiamata. Questa view sta
  //    sotto KeepAlive: `onActivated` scatta a OGNI rientro nel tab, e con il
  //    param ancora nell'URL si rifarebbe la risoluzione ogni volta — una
  //    chiamata per attivazione, per sempre. È la stessa disciplina dei
  //    deep-link `?open=` (contratti, lotti).
  //    ⭐ Qui sì e in `applyPraticaDeepLink` no, ed è voluto: quello ricarica il
  //    percorso a ogni rientro apposta (freschezza), questo risolverebbe di
  //    nuovo lo stesso id per ottenere la stessa risposta.
  const query = { ...route.query }
  delete query.flusso_id
  router.replace({ query })
  const res = await execute(() => getPraticaDiFlusso(flussoId), { silent: true })
  if (!res?.pratica_id) return
  selectedFlussoId.value = flussoId
  selezionaPratica(res.pratica_id)
}

applyTipoDeepLink({ refetch: false }) // primo mount: fetcha la SearchTable
const { execute } = useApiHandler()
const notify = useNotify()
useReadonlyMode(READONLY_DOMAINS.PRATICHE)

// Modalita' tecnica (diagnostica super-admin, B5): toggle opt-in che riespone
// il plumbing del motore (codici/sequenza/stati/rami) nelle viste runtime
// (PraticaPercorso, FlussoDrawer). Default spento; il toggle e' visibile solo
// agli ADMIN (auth.isSuperAdmin). Il flag e' fornito ai figli via provide.
const auth = useAuthStore()
const modalitaTecnica = ref(false)
provideTechnicalMode(modalitaTecnica)

// Percorso a comparsa (master-detail sotto la lista): visibile solo con una
// pratica selezionata; collassabile per ridare spazio alla lista.
const percorsoCollapsed = ref(false)

// --- Coda lavoro + deep-link (KeepAlive-aware) ---
onMounted(() => {
  // Remount dopo eviction dalla cache KeepAlive: selectedPraticaId persiste
  // nello store ma il percorso (ref locale) riparte vuoto e il watch scatta
  // solo sul CAMBIO di id → ricarica esplicita (il deep-link, se presente,
  // e' gestito da onActivated subito dopo).
  if (store.selectedPraticaId && !_queryId('pratica_id')) {
    loadPercorsoPratica(store.selectedPraticaId)
  }
})

// onActivated scatta al primo mount E ad ogni ri-attivazione dalla cache:
// unico punto affidabile per applicare i deep-link (idempotenti).
onActivated(() => {
  applyTipoDeepLink({ refetch: true })
  applyPraticaDeepLink()
  // ⚠️ Dopo l'altro e non al suo posto: i due sono esclusivi (questo esce se
  //    `pratica_id` c'e'), ma l'ordine rende esplicito quale vince.
  applyFlussoDeepLink()
})

// --- Percorso (roadmap) della pratica selezionata ---
const percorso = ref([])
const percorsoLoading = ref(false)
// Flusso arrivato dal deep-link della coda home (flusso_id): trasportato nello
// stato dashboard per l'evidenziazione dello step d'origine nel percorso.
const selectedFlussoId = ref(null)

async function loadPercorsoPratica(praticaId) {
  if (!praticaId) { percorso.value = []; return }
  percorsoLoading.value = true
  try {
    percorso.value = await store.loadPercorso(praticaId)
  } finally {
    percorsoLoading.value = false
  }
}

// Quando cambia la pratica selezionata nella SearchTable
function onRowClick(data) {
  store.selectedPraticaId = data.id
  // Selezione dalla tabella: nessun flusso della coda evidenziato.
  selectedFlussoId.value = null
  loadPercorsoPratica(data.id)
}

// Apre la scheda pratica (drawer edit) sulla pratica selezionata: e' qui che
// vivono le azioni di stato (Apri/Sospendi/Chiudi/Annulla). Il row-click resta
// dedicato alla selezione per la roadmap percorso; la scheda si apre da qui.
// Passiamo solo l'id: il drawer rifa' la fetchDetail, indipendentemente dal
// fatto che la riga provenga dalla SearchTable o dalla coda lavoro.
function onApriScheda() {
  if (!store.selectedPraticaId) return
  drawer.editRow({ id: store.selectedPraticaId }, 'id')
}

// Riga della pratica selezionata in `store.items` (ricerca). Fonte unica per i
// derivati sotto (codice / terminale / contesto cliente), evita di ripetere il
// find su selectedPraticaId.
const selectedItem = computed(
  () => (store.selectedPraticaId
    ? store.items.find(i => i.id === store.selectedPraticaId)
    : null) || null,
)

// Codice della pratica selezionata (per barra contesto sopra flussi).
// Fallback `#id`: una pratica deep-linkata puo' non essere nella lista
// filtrata corrente (data_da/tipo) → niente riga in store.items, ma il
// percorso funziona lo stesso e la barra non deve restare senza riferimento.
// (Per la stessa ragione selectedPraticaReadonly puo' non vedere lo stato
// terminale: la difesa autoritativa restano i guard DB con errore parlante.)
const selectedPraticaCodice = computed(
  () => selectedItem.value?.codice
    || (store.selectedPraticaId ? `#${store.selectedPraticaId}` : null),
)

// Pratica selezionata in stato terminale (CHIUSA/ANNULLATA) → percorso e flussi
// in sola lettura: niente nuovi step, flussi esistenti consultabili ma non
// modificabili. La scheda pratica (PraticaDrawer) si auto-protegge dal proprio
// dettaglio, qui copriamo percorso + drawer flusso che vivono nella dashboard.
// Lo stato si legge dalla riga in `store.items` (ricerca). La coda lavoro
// esclude le pratiche terminali (fn_coda_lavoro_operatore) quindi non puo'
// selezionare una terminale non presente in `store.items`; oltre alla difesa
// DB (guard che rifiuta le operazioni su pratica terminale).
const selectedPraticaReadonly = computed(() => {
  const item = selectedItem.value
  return item ? STATI_PRATICA_TERMINALI.includes(item.stato_codice_interno) : false
})

// --- FlussoDrawer ---
const flussoDrawerVisible = ref(false)
const flussoSelezionato = ref(null)

// Azione roadmap in corso: blocca i click (anti doppia creazione).
const percorsoBusy = ref(false)

// Apre un flusso esistente dalla roadmap (per id → carica il dettaglio).
async function onOpenFlussoById(flussoId) {
  percorsoBusy.value = true
  try {
    const res = await execute(() => getFlusso(store.selectedPraticaId, flussoId))
    if (res !== null) {
      flussoSelezionato.value = res
      flussoDrawerVisible.value = true
    }
  } finally {
    percorsoBusy.value = false
  }
}

// Crea uno step della roadmap (template-bound) e lo apre. Il guard prerequisiti
// DB (esito-aware, BEFORE INSERT) rifiuta con errore parlante se non abilitato.
async function onCreateFlusso(templateFlussoId) {
  percorsoBusy.value = true
  try {
    const res = await execute(
      () => createFlusso(store.selectedPraticaId, { template_flusso_id: templateFlussoId }),
      { successMessage: t('pratiche.flusso_creato') }
    )
    if (res !== null) {
      await loadPercorsoPratica(store.selectedPraticaId)
      flussoSelezionato.value = await execute(() => getFlusso(store.selectedPraticaId, res.flusso_id))
      if (flussoSelezionato.value !== null) flussoDrawerVisible.value = true
    }
  } finally {
    percorsoBusy.value = false
  }
}

async function onFlussoSaved() {
  flussoDrawerVisible.value = false
  if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
  // Il completamento di un flusso puo' aver auto-chiuso la pratica (APERTA →
  // CHIUSA, trgfn_flussi_autochiusura_pratica): rinfresca la lista — senza
  // resettare la pagina — cosi' lo stato in tabella e il readonly derivato
  // (selectedPraticaReadonly) si aggiornano.
  if (store.hasSearched) await store.fetchList()
}

// Contesto cliente della pratica selezionata (BA derivato + istanza), esposti
// dalla lista (_PRATICA_SELECT). Alimenta l'affordance "apri documento" sul
// percorso: gating cliente-attivo + eredità nel drawer (stesso payload del flusso).
const selectedPraticaContext = computed(() => ({
  billingAccountId: selectedItem.value?.billing_account_id ?? null,
  istanzaUtilityId: selectedItem.value?.istanza_utility_id ?? null,
}))

// --- Attività UI di dominio aperte da un flusso (data-driven, registry) ---
// L'azione "apri documento" sul flusso (azione_ui_key) è risolta dal registry
// Registro delle attivita' UI (uiActivityRegistry, iscritto dai domini): nessun drawer hardcoded qui. Il componente è dinamico,
// le props e il gancio post-save arrivano dalla voce di registry.
const activityVisible = ref(false)
const activityComponent = shallowRef(null)
const activityProps = ref({})
const activityEntry = ref(null)
const activityCtx = ref(null)
// Flag anti-richiamo: l'aggancio ROOT documento↔pratica va fatto una volta
// (l'auto-save bozza emette `saved` più volte). L'aggancio BE è comunque idempotente.
const activityLinked = ref(false)

// Apertura da FlussoDrawer: risolve l'attività dal registry e apre il drawer.
// Carica il componente (lazy) PRIMA di montarlo, poi attiva `visible` al tick
// successivo: il drawer monta con visible=false e il suo watch(visible) — che
// NON è immediate — scatta sulla transizione false→true (resetForm/pre-fill).
// Aggancio per-flusso: il documento si lega al flusso d'origine, che quindi DEVE
// esistere ed essere IN_CORSO quando si apre. Garantiamo l'invariante: crea il
// flusso se lo step non e' istanziato, lo avvia se DA_ESEGUIRE. Ritorna il
// flusso_id effettivo, o null se l'utente/guard interrompe (non si apre).
async function ensureFlussoInCorso(payload) {
  let flussoId = payload.flussoId
  if (!flussoId) {
    const created = await execute(
      () => createFlusso(store.selectedPraticaId, { template_flusso_id: payload.templateFlussoId }),
      { successMessage: t('pratiche.flusso_creato') }
    )
    if (created === null) return null
    flussoId = created.flusso_id
  }
  // Stato AUTOREVOLE dal BE, non da payload: il percorso puo' essere stantio (il
  // flusso e' avanzato in un'altra sessione) e un flusso appena creato potrebbe
  // non essere DA_ESEGUIRE se il template lo avvia da se'. Avviamo solo se lo
  // stato reale e' DA_ESEGUIRE: IN_CORSO si usa com'e'; COMPLETATO/ANNULLATO
  // riapre in sola lettura il documento gia' agganciato (niente avvio, niente
  // transizione invalida che abortirebbe l'apertura).
  const flusso = await execute(() => getFlusso(store.selectedPraticaId, flussoId))
  if (flusso === null) return null
  if (flusso.stato_codice_interno === STATO_FLUSSO.DA_ESEGUIRE) {
    const avviato = await execute(
      () => cambiaStatoFlusso(store.selectedPraticaId, flussoId, { nuovo_stato: STATO_FLUSSO.IN_CORSO }),
    )
    if (avviato === null) return null
  }
  return flussoId
}

async function onOpenAttivita(payload) {
  const entry = getUiActivity(payload?.key)
  if (!entry) return
  if (percorsoBusy.value) return
  percorsoBusy.value = true
  try {
    const mod = await entry.loadComponent()
    // Garantiamo il flusso d'origine IN_CORSO prima di aprire il documento.
    const flussoId = await ensureFlussoInCorso(payload)
    if (flussoId == null) return
    const ctx = { ...payload, flussoId }
    // Riapertura: se QUESTO flusso ha gia' un documento ROOT, lo apriamo in EDIT
    // invece di crearne uno nuovo (il lucchetto unico per-flusso a DB impedisce
    // comunque il doppione). Resolver opzionale e best-effort.
    const existingId = entry.resolveExisting ? await entry.resolveExisting(ctx) : null
    // Step a valle (es. SMISTAMENTO): il documento DEVE gia' esistere. Niente
    // fallback in create (eviterebbe un documento orfano): errore parlante e stop.
    if (entry.requiresExisting && existingId == null) {
      notify.error(t('pratiche.attivita_documento_mancante'))
      return
    }
    activityEntry.value = entry
    activityCtx.value = ctx
    activityProps.value = entry.buildProps(ctx, existingId)
    // Documento gia' agganciato → niente re-aggancio (onSaved e' comunque
    // idempotente, ma cosi' evitiamo il toast "collegato" a ogni salvataggio).
    activityLinked.value = existingId != null
    activityComponent.value = markRaw(mod.default)
    activityVisible.value = false
    await nextTick()
    activityVisible.value = true
  } finally {
    percorsoBusy.value = false
  }
  // La roadmap riflette il flusso ora avviato/creato.
  if (store.selectedPraticaId) loadPercorsoPratica(store.selectedPraticaId)
}

// Salvataggio del documento: gancio post-save del registry (es. collega ROOT),
// una sola volta, poi rinfresca il percorso (riflette M2/handler a valle).
async function onActivitySaved(result) {
  const entry = activityEntry.value
  // Id robusto: l'evento 'saved' del drawer ha forme diverse (update/emissione/
  // create) → il registry sa estrarlo (savedId). Senza, il collegamento saltava
  // sul ramo update (result.id assente → solo preventivo_id).
  const savedId = entry?.savedId ? entry.savedId(result) : result?.id
  if (entry?.onSaved && savedId && !activityLinked.value) {
    const ok = await execute(
      () => entry.onSaved(savedId, activityCtx.value),
      { successMessage: t(entry.linkedMessage || 'pratiche.preventivo_collegato') }
    )
    if (ok !== null) activityLinked.value = true
  }
  if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
  // Salvataggio/emissione concludono l'interazione col documento → chiudi il
  // drawer attivita' (mirror dello standalone, dove il parent chiude su @saved).
  // Riapribile dall'affordance del percorso (riprende il ROOT agganciato).
  activityVisible.value = false
}

// --- PraticaDrawer ---
async function onDrawerSaved() {
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
  drawer.close()
}

// Watch selectedPraticaId per caricare flussi (copre anche cambio da altri componenti)
watch(() => store.selectedPraticaId, (id, oldId) => {
  if (id && id !== oldId) loadPercorsoPratica(id)
  else if (!id) percorso.value = []
})

// Ricalcola layout DataTable quando hasSearched cambia (sidebar/flussi appaiono/scompaiono).
// ResizeObserver sul container: deterministico, senza setTimeout.
const dashboardRef = ref(null)
let resizeObserver = null

onMounted(() => {
  if (dashboardRef.value) {
    resizeObserver = new ResizeObserver(() => {
      window.dispatchEvent(new Event('resize'))
    })
    resizeObserver.observe(dashboardRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<template>
  <div ref="dashboardRef" class="app-page pratiche-dashboard">

    <!-- Area principale -->
    <main class="dashboard-main">

      <!-- SearchTable pratiche (sempre visibile — contiene filtri e placeholder) -->
      <div class="dashboard-table">
        <PraticheSearchTable
          @new="drawer.openCreate"
          @row-click="onRowClick"
        />
      </div>

      <!-- Percorso della pratica selezionata (master-detail a comparsa): appare
           solo con una pratica selezionata, collassabile per ridare spazio alla
           lista. -->
      <div
        v-if="store.selectedPraticaId"
        class="dashboard-flussi-wrapper"
        :class="{ 'is-collapsed': percorsoCollapsed }"
      >
        <div class="dashboard-flussi-context">
          <span class="flussi-context-label">
            <i class="pi pi-folder-open" />
            {{ t('pratiche.visualizzazione_pratica', { codice: selectedPraticaCodice }) }}
            <Button
              :label="t('pratiche.apri_scheda')"
              icon="pi pi-external-link"
              text
              size="small"
              class="app-escape"
              @click="onApriScheda"
            />
          </span>
          <!-- Toggle modalità tecnica (super-admin): riespone il plumbing del
               motore nelle viste runtime. Opt-in, mai il default operatore. -->
          <Button
            v-if="auth.isSuperAdmin"
            :label="t('pratiche.modalita_tecnica')"
            :icon="modalitaTecnica ? 'pi pi-eye-slash' : 'pi pi-wrench'"
            text
            size="small"
            class="tecnico-toggle"
            :aria-pressed="modalitaTecnica"
            @click="modalitaTecnica = !modalitaTecnica"
          />
          <button
            type="button"
            class="app-collapse-toggle"
            :aria-label="t(percorsoCollapsed ? 'pratiche.percorso_espandi' : 'pratiche.percorso_comprimi')"
            :aria-expanded="!percorsoCollapsed"
            @click="percorsoCollapsed = !percorsoCollapsed"
          >
            <i :class="percorsoCollapsed ? MANAGE_ICONS.EXPAND : MANAGE_ICONS.COLLAPSE" />
          </button>
        </div>
        <div v-show="!percorsoCollapsed" class="dashboard-flussi">
          <PraticaPercorso
            :percorso="percorso"
            :loading="percorsoLoading"
            :pratica-id="store.selectedPraticaId"
            :pratica-context="selectedPraticaContext"
            :busy="percorsoBusy"
            :readonly="selectedPraticaReadonly"
            :selected-flusso-id="selectedFlussoId"
            @open-flusso="onOpenFlussoById"
            @create-flusso="onCreateFlusso"
            @open-attivita="onOpenAttivita"
          />
        </div>
      </div>

    </main>

    <!-- Drawer: Creazione/Dettaglio pratica -->
    <!-- Preset B6: "Nuova pratica" col filtro tipo attivo parte gia' su quel
         tipo (default visibile e modificabile, non un lock). -->
    <PraticaDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :pratica-id="drawer.state.itemId"
      :preset-tipo-prestazione-id="store.filters.tipo_prestazione_id"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <!-- Drawer: Esecuzione flusso -->
    <FlussoDrawer
      :visible="flussoDrawerVisible"
      @update:visible="v => flussoDrawerVisible = v"
      :flusso="flussoSelezionato"
      :pratica-id="store.selectedPraticaId"
      :readonly="selectedPraticaReadonly"
      @saved="onFlussoSaved"
      @open-attivita="onOpenAttivita"
    />

    <!-- Drawer documento collegato (data-driven): componente risolto dal registry
         registro delle attivita' UI in base all'azione_ui_key del flusso. Per il
         preventivo, praticaId+praticaContext (da buildProps) nascondono l'azione
         accetta e pre-compilano/bloccano cliente+istanza; l'accettazione passa
         dal flusso M2. -->
    <component
      :is="activityComponent"
      v-if="activityComponent"
      v-bind="activityProps"
      :visible="activityVisible"
      @update:visible="v => activityVisible = v"
      @saved="onActivitySaved"
    />

  </div>
</template>

<style scoped>
.pratiche-dashboard {
  display: flex;
  flex-direction: row;
  height: 100%;
  overflow: hidden;
  gap: 0;
}

.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* Tabella: occupa lo spazio restante, overflow gestito internamente da DataTable */
.dashboard-table {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* Percorso: master-detail sotto la lista, altezza generosa e collassabile. */
.dashboard-flussi-wrapper {
  flex: 0 0 auto;
  height: 42vh;
  min-height: 170px;
  max-height: 65vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.dashboard-flussi-wrapper.is-collapsed {
  height: auto;
  min-height: 0;
  max-height: none;
}

/* Barra contesto pratica sopra il separatore */
.dashboard-flussi-context {
  display: flex;
  align-items: center;
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  background: var(--app-content-bg);
  border-top: 2px solid var(--app-severity-info);
  flex: 0 0 auto;
}

/* La label occupa lo spazio libero → i pulsanti (tecnico, collassa) vanno a destra. */
.flussi-context-label {
  color: var(--app-severity-info);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex: 1 1 auto;
  min-width: 0;
}

.tecnico-toggle {
  flex: 0 0 auto;
}

/* Toggle collassa/espandi percorso: classe condivisa .app-collapse-toggle (main.css). */

.dashboard-flussi {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* Tablet/mobile: la dashboard impila (rail sopra) e scrolla per intero */
@media (max-width: 1279.98px) {
  .pratiche-dashboard {
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .dashboard-main {
    overflow: visible;
    flex: 0 0 auto;
  }
  .dashboard-table {
    overflow: visible;
    flex: 0 0 auto;
    min-height: 55vh;
  }
  .dashboard-flussi-wrapper {
    height: auto;
    max-height: none;
  }
}
</style>
