<script setup>
// Scopo: pagina lista operatori configurabile
//        (`<ListaConfigurabile codice="anagrafiche.operatori">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente.
// Click riga -> apre OperatoreDrawer in modalita' modifica.
// Button Nuovo -> apre OperatoreDrawer in modalita' crea.
// Nessun export: il dominio non ha endpoint (lo scaffolding omette l'azione da
// se', non ricevendo `exportFn`).
// ⭐ «Mostra permessi» (2026-10-06, brief riepilogo-permessi): sotto ogni riga
//    le aree come chip — livello effettivo, override scritti, triangolo del
//    tetto. Sostituisce la vecchia pagina «Riepilogo permessi» (una matrice
//    operatori × aree che con 14 aree non entrava piu').
// ℹ️ Niente kebab di riga (Tid, 2026-10-06): la sua sola voce apriva un drawer
//    dei soli permessi, cioe' la scheda «Permessi» del drawer operatore che si
//    apre gia' cliccando la riga — due strade per lo stesso pannello.
import { onMounted, onActivated, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useLookup } from '../../core/composables/useLookup'
import { listUnitaOrganizzative, getPermessiRiepilogo } from '../api/amministrazione'
import { useSetupStatus } from '../composables/useSetupStatus'
import { buildFilterSuperAdminOptions, getLivelloLabel, getLivelloSeverity } from '../constants'
import { buildAttivoOptions } from '../../core/utils/options'
import { READONLY_DOMAINS, TAB_ENTITIES, STATUS_ICONS } from '../../core/constants'
import OperatoreDrawer from '../components/OperatoreDrawer.vue'
import OperatoriNonAssegnatiBanner from '../components/OperatoriNonAssegnatiBanner.vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import FiltriLista from '../../core/components/FiltriLista.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { etichettaRuoloApplicativo } from '../../core/utils/i18nLabel'

const { t, te } = useI18n()
const store = useOperatoriStore()
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const drawer = useDrawerState()
const { isBlocked } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
// Destruct: Vue auto-unwrap i ref destrutturati nel template, non nel
// reactive object proxy. Pattern idiomatic.
const { status: setupStatusData, load: loadSetupStatus, hasOperatoriNonAssegnati } = useSetupStatus()

useTabFreshness(store, TAB_ENTITIES.OPERATORE)

// Filtri locali (extra rispetto a search).
// Multi-face auth Stage B: il vecchio filtro ruolo_sistema (ADMIN/OPERATIVO/
// DISABILITATO) e' scomposto in:
//   - superAdminFilter: toggle Sì/No/Tutti sul binding SUPER_ADMIN
//   - activeFilter: stato attivo identita' (ex "DISABILITATO")

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.nuovo_operatore',
  onNew: () => drawer.openCreate(),
  // Allineato al preset del seed (`soggetto_cognome asc`).
  searchTableOptions: { defaultSortField: 'soggetto_cognome' },
})

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect, bindToggle } = useStoreFilterBindings(store, applyFilters)
const { value: superAdminFilter, onChange: onSuperAdminChange } = bindSelect('is_super_admin')
const { value: uoFilter, onChange: onUoChange } = bindSelect('unita_organizzativa_id')
const { value: activeFilter, onChange: onActiveChange } = bindSelect('is_active')
// Gli utenti di prova (provisioning di sviluppo): spento = nascosti, il default.
// Acceso ALLARGA la lista, ed e' quello che il segno dei filtri conta.
const { value: mostraDiProva, onChange: onMostraDiProvaChange } = bindToggle('includi_di_prova', {
  on: true, off: null,
})

const superAdminOptions = buildFilterSuperAdminOptions(t)
// ⭐ Dal BB di core (regola del 2, ok Tid 2026-09-23): `buildFilterStatoOptions`
//    era la quinta copia della stessa terna, ed e' stata ritirata.
const activeOptions = buildAttivoOptions(t)

// La LISTA al mount: il rientro sotto `<KeepAlive>` lo rinfresca gia' lo
// scaffolding (`useListaConfigurabilePage` → `useSearchTable`, che salta la
// prima attivazione apposta per non raddoppiare questo fetch).
onMounted(() => {
  store.fetchList()
})

// ⚠️ Il BANNER, invece, non lo rinfresca nessuno: `onActivated` copre il primo
//    montaggio E ogni rientro, quindi il caricamento sta qui e NON in
//    `onMounted` — tenerlo in tutti e due lo chiamerebbe due volte all'apertura.
// ⛔ E `true` non e' pignoleria: `useSetupStatus.load(force = false)` esce
//    subito se ha gia' caricato (`if (loaded.value && !force) return`), e quella
//    cache vive nell'istanza, che KeepAlive tiene in vita. Senza il `force` il
//    rientro non rileggerebbe NIENTE e il banner «operatori non assegnati»
//    resterebbe quello della prima apertura — cioe' la correzione sembrerebbe
//    fatta e non farebbe nulla.
onActivated(() => {
  loadSetupStatus(true)
})

// Refresh setup status quando si chiude il drawer (assignment puo' essere
// cambiato dall'admin nel drawer operatore).
function onDrawerSavedWithStatus() {
  drawer.close()
  store.fetchList()
  loadSetupStatus(true)
}

function activeBadgeSeverity(active) {
  return active ? 'success' : 'danger'
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { drawer.editRow(data, 'auth_user_id') }

// Scopo: Il badge del ruolo applicativo (BB `etichettaRuoloApplicativo`);
//        senza ruolo il trattino.
function ruoloAppLabel(ruoloApp) {
  return etichettaRuoloApplicativo(t, te, ruoloApp) || '—'
}

// ═══ MOSTRA PERMESSI — le aree di ogni operatore, sotto la sua riga ═════════
// L'espansione e' PILOTATA qui: con l'interruttore acceso e' aperta per tutte
// le righe a ogni caricamento (pagina, ordinamento, filtri); spento, si apre
// riga per riga col chevron, e «Espandi/Comprimi tutte» restano le azioni di
// testata della lista.
const permessiAperti = ref(false)
const expandedRows = ref({})

// Le chip per operatore: `{ [auth_user_id]: righe di fn_get_permessi_riepilogo_aree }`,
// `false` se la lettura e' fallita (si riprova richiudendo e riaprendo la riga).
// ⚠️ Si chiedono per le righe APERTE della pagina, in una chiamata sola, e si
//    scartano a ogni nuovo caricamento della lista: dopo un salvataggio i
//    numeri sono cambiati, e una cache sopravvissuta li direbbe vecchi.
const riepilogo = ref({})
let richiesti = new Set()
let generazione = 0

function apriTutte() {
  expandedRows.value = Object.fromEntries(store.items.map(r => [r.auth_user_id, true]))
}

// Scopo: carica il riepilogo delle righe aperte che non lo hanno ancora.
async function caricaRiepilogo() {
  const presenti = new Set(store.items.map(r => r.auth_user_id))
  const ids = Object.keys(expandedRows.value || {})
    .filter(k => expandedRows.value[k])
    .map(Number)
    .filter(id => presenti.has(id) && !richiesti.has(id))
  if (!ids.length) return
  ids.forEach(id => richiesti.add(id))
  const mia = generazione
  try {
    const res = await getPermessiRiepilogo(ids)
    if (mia !== generazione) return // la lista e' cambiata nel frattempo
    const perOperatore = Object.fromEntries(ids.map(id => [id, []]))
    for (const r of res.data.data.results) (perOperatore[r.auth_user_id] ||= []).push(r)
    riepilogo.value = { ...riepilogo.value, ...perOperatore }
  } catch {
    // Errore gia' notificato dall'interceptor. La riga dice che la lettura e'
    // fallita (non «caricamento» per sempre), e si potra' richiedere.
    if (mia !== generazione) return
    ids.forEach(id => richiesti.delete(id))
    riepilogo.value = { ...riepilogo.value, ...Object.fromEntries(ids.map(id => [id, false])) }
  }
}

watch(() => store.items, () => {
  generazione++
  riepilogo.value = {}
  richiesti = new Set()
  if (permessiAperti.value) apriTutte()
  caricaRiepilogo()
})
watch(expandedRows, caricaRiepilogo)

function onPermessiAperti(acceso) {
  if (acceso) apriTutte()
  else expandedRows.value = {}
}

// Dopo un Salva nel pannello permessi le chip si rinfrescano da sole: lo
// store emette `OPERATORE` cambiato, `useTabFreshness` ricarica la lista e il
// `watch` su `store.items` scarta e richiede il riepilogo.
</script>

<template>
  <div class="app-page">
    <OperatoriNonAssegnatiBanner
      v-if="hasOperatoriNonAssegnati"
      :count="setupStatusData.operatori_non_assegnati"
    />

    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('amministrazione.search_placeholder')"
          />
        </template>
        <Select
          v-model="superAdminFilter"
          class="app-filter-w-sm"
          :options="superAdminOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.filter_super_admin')"
          @change="onSuperAdminChange"
        />
        <Select
          v-model="uoFilter"
          class="app-filter-w-md"
          :options="[{ descrizione: t('amministrazione.reparto_all'), id: null }, ...unitaOrg.items.value]"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('amministrazione.filter_reparto')"
          @change="onUoChange"
        />
        <Select
          v-model="activeFilter"
          class="app-filter-w-sm"
          :options="activeOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.filter_stato')"
          @change="onActiveChange"
        />
        <FiltroToggle
          v-model="mostraDiProva"
          :label="t('amministrazione.mostra_di_prova')"
          :hint="t('amministrazione.mostra_di_prova_hint')"
          @change="onMostraDiProvaChange"
        />
      </FiltriLista>
      <!-- Non e' un filtro: cambia cosa si vede di ogni riga, non quali righe. -->
      <FiltroToggle
        v-model="permessiAperti"
        :label="t('amministrazione.mostra_permessi')"
        :hint="t('amministrazione.mostra_permessi_hint')"
        @change="onPermessiAperti"
      />
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <!-- `data-key`: la lista operatori e' chiavata su `auth_user_id`, non su
         `id` (default della BB). Senza, selezione ed espansione perdono la riga. -->
    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.operatori"
      v-model:expanded-rows="expandedRows"
      data-key="auth_user_id"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-soggetto_cognome="{ data }">
        {{ data.soggetto_cognome }} {{ data.soggetto_nome }}
      </template>
      <!-- Colonna calcolata: nel catalogo non ha `campo_sorgente` (i due badge
           nascono da `is_super_admin` + `ruolo_applicativo`), quindi lo slot
           e' l'unico modo di renderla. -->
      <template #cell-ruolo="{ data }">
        <div class="operatore-ruolo-badges">
          <Badge v-if="data.is_super_admin"
            :value="t('amministrazione.is_super_admin.badge')" severity="warn" />
          <!-- ⭐ Spenta, la veste TIENE il tipo (R-DB-1, 2026-10-02): il
               «disabilitato» si legge da `veste_attiva`, non dal ruolo. -->
          <Badge v-if="data.veste_attiva === false"
            :value="t('amministrazione.permessi_stato_disabilitato')" severity="danger" />
          <Badge v-else :value="ruoloAppLabel(data.ruolo_applicativo)" severity="info" />
          <!-- Le ALTRE vesti attive della credenziale (D-6, 2026-10-02): solo
               un'informazione — «e' anche cliente dello shop» —, si governano
               dal drawer del cliente o del fornitore, non da qui. -->
          <Badge v-for="veste in data.altre_vesti || []" :key="veste"
            :value="ruoloAppLabel(veste)" severity="secondary"
            v-tooltip.top="t('amministrazione.riuso_vesti')" />
          <!-- L'etichetta del provisioning di sviluppo: un segno, non una
               categoria (l'utente di prova resta un operatore in tutto). -->
          <Badge v-if="data.di_prova"
            :value="t('amministrazione.di_prova_badge')" severity="secondary"
            v-tooltip.top="t('amministrazione.di_prova_tooltip')" />
        </div>
      </template>
      <template #cell-is_active="{ data }">
        <Badge
          :value="data.is_active ? t('amministrazione.stato_attivo') : t('amministrazione.stato_inattivo')"
          :severity="activeBadgeSeverity(data.is_active)"
        />
      </template>

      <!-- Le aree dell'operatore: livello effettivo, override scritti, tetto.
           Stessa lettura dell'elenco aree del pannello permessi, dalla stessa
           sede a DB (`fn_get_permessi_riepilogo_aree`). -->
      <template #row-expansion="{ data }">
        <div v-if="riepilogo[data.auth_user_id]" class="operatore-permessi-aree">
          <span v-for="area in riepilogo[data.auth_user_id]" :key="area.area_id" class="operatore-permessi-area">
            <span class="operatore-permessi-area-nome">{{ area.area_descrizione }}</span>
            <Tag :value="getLivelloLabel(t, area.livello)" :severity="getLivelloSeverity(area.livello)" />
            <Badge
              v-if="area.override_count"
              v-tooltip.top="t('amministrazione.permessi_area_override')"
              :value="area.override_count"
              severity="info"
            />
            <i
              v-if="area.voci_limitate"
              v-tooltip.top="t('amministrazione.permessi_area_limitate', { n: area.voci_limitate })"
              :class="[STATUS_ICONS.ERRORE, 'app-permessi-tetto-icona']"
            />
          </span>
        </div>
        <span v-else-if="riepilogo[data.auth_user_id] === false" class="app-text-muted">{{ t('common.error_loading') }}</span>
        <span v-else class="app-text-muted">{{ t('common.loading') }}</span>
      </template>
    </ListaConfigurabile>
    </template>

    <OperatoreDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :auth-user-id="drawer.state.itemId"
      @saved="onDrawerSavedWithStatus"
      @cancelled="drawer.close"
    />
  </div>
</template>

<style scoped>
.operatore-ruolo-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
/* Le chip delle aree: vanno a capo, e ognuna tiene insieme nome, livello,
   numero e triangolo — una chip spezzata a meta' non si legge.
   ⛔ `contain: inline-size` non e' un dettaglio: la tabella delle liste e'
   larga quanto il suo contenuto (`.app-datatable`, `width: max-content`), e
   per quel calcolo un flex che va a capo vale come se stesse su UNA riga — le
   14 chip allargavano la tabella e accendevano lo scroll orizzontale invece di
   andare a capo (2026-10-06). Contenuto, il blocco prende la larghezza della
   riga e non la detta. */
.operatore-permessi-aree {
  contain: inline-size;
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem 0.75rem;
  padding: 0.25rem 0;
}
.operatore-permessi-area {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
}
.operatore-permessi-area-nome {
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}
</style>
