<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Coda di lavoro resi (righe reso CONFERMATE), promossa a lista
//        configurabile standard. Due varianti via prop `coda`: 'accreditare'
//        (righe a credito, predisposizione slice nota di credito) e
//        'riconsegnare' (righe per ri-consegna con copertura pendente, colonne
//        resa/ri-consegnata/residua + stato derivato).
//
//        Migrata da DataTable raw a <ListaConfigurabile> (config DB
//        `vendite.resi_da_accreditare` / `vendite.resi_da_riconsegnare`, id
//        10/11): personalizzazione colonne + export CSV/XLSX + paginatore in
//        alto, allineata al pattern lista standard (memoria
//        feedback_lista_pattern_standard). Scaffolding via
//        useListaConfigurabilePage (search/sort/page + export dialog +
//        pageActions). Grana RIGA: dataKey=`resi_riga_id`; l'azione "apri reso"
//        usa `reso_id` (diverso dal PK di riga). Le due code sono code di
//        lavoro: nessun default temporale (lo store carica sempre il pendente).
//        Click riga / azione -> apre il reso nel drawer.
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import AccreditoEsitoDialog from './AccreditoEsitoDialog.vue'
import AccreditoAnnullaDialog from './dialogs/AccreditoAnnullaDialog.vue'
import { useActionPermission } from '../../../core/composables/useActionPermission'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { useSelezioneToggle } from '../../../core/composables/useSelezioneToggle'
import { MANAGE_ICONS } from '../../../core/constants'
import { formatNumber } from '../../../core/utils/format'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import {
  etichettaAccreditoSeverity,
  statoRiconsegnaSeverity,
} from '../../../core/utils/severity'
import { paramsOrdinamento } from '../../../core/utils/listParams'
import { AZIONE_ACCREDITA_RESO, ESITO_ACCREDITO, ETICHETTA_ACCREDITO } from '../constants'
import { accreditaRighe, exportDaAccreditare, exportDaRiconsegnare } from '../api/resiApi'
import {
  useResiCodaAccreditareStore,
  useResiCodaRiconsegnareStore,
} from '../stores/resiCoda'
import FiltroPeriodo from '../../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../../core/components/FiltriLista.vue'

const props = defineProps({
  coda: {
    type: String,
    required: true,
    validator: (v) => ['accreditare', 'riconsegnare'].includes(v),
  },
})
const emit = defineEmits(['apri-reso'])

const { t, te } = useI18n()
const isBlocked = useInjectBlocked()

// Risoluzione statica per variante (la prop `coda` e' fissa per istanza:
// ResiView monta un componente per tab).
const isRiconsegna = props.coda === 'riconsegnare'
const store = isRiconsegna
  ? useResiCodaRiconsegnareStore()
  : useResiCodaAccreditareStore()
const listaCodice = isRiconsegna
  ? 'vendite.resi_da_riconsegnare'
  : 'vendite.resi_da_accreditare'
const exportFn = isRiconsegna ? exportDaRiconsegnare : exportDaAccreditare

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn,
  getExportParams: (fmt) => buildExportParams(fmt),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
  // Closure lazy: legge `selezione`/`canAccreditare`, definiti sotto.
  extraActions: () => azioniAccredito(),
})

// Le code non hanno "Nuovo" (il reso nasce dal DDT consegnato): lo
// scaffolding omette l'azione da sé, non ricevendo `onNew`.

// --- Filtri custom (toolbar caller): date opzionali, NESSUN default (coda). ---
const { bindSelect, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

// Filtro etichetta accredito (solo coda accrediti, forma contatore): DOVUTA =
// lavoro arretrato, FACOLTATIVA = opzione dell'operatore (DL-26 — la scelta
// "emetto una nota?" si esercita da qui, quindi le facoltative devono restare
// visibili, non solo filtrate via).
// ⚠️ Le ETICHETTE a schermo dicono «Accredito dovuto / facoltativo», non «NC»
// (allineamento 2026-08-09): DL-24 impone di nominare il FATTO e non il
// rimedio, perche' lo strumento — nota di credito o altro — non e' ancora
// definito e l'etichetta non deve pre-deciderlo. I CODICI restano
// DOVUTA/FACOLTATIVA: sono colonna della vista DB `vw_resi_da_accreditare`.
const { value: etichettaFilter, onChange: onEtichettaChange } = bindSelect('etichetta')
const etichettaOptions = computed(() => [
  { value: null, label: t('vendite.resi.coda_etichetta_tutte') },
  ...Object.values(ETICHETTA_ACCREDITO).map((et) => ({
    value: et,
    label: etichettaLabel(et),
  })),
])

// Decodifica fail-visible (pattern labelOrCode): un'etichetta futura fuori
// vocabolario mostra il codice grezzo, mai la chiave i18n letterale.
function etichettaLabel(et) {
  return labelOrCode(t, te, `vendite.resi.coda_etichetta.${et}`, et)
}

// ══════════════════════════════════════════════════════════
//  IL VERBO — accredita (nota di credito sui resi)
// ══════════════════════════════════════════════════════════
// ⭐ Il verbo NON emette la nota di credito: registra l'accredito (le righe di
// RETTIFICA in commessa) e lo mette nel giro di fatturazione. Il documento
// nasce dopo, al prossimo giro. Ogni testo a video deve dire questo — una
// conferma che promette «emetti nota di credito» promette un documento che
// l'operatore poi non trova.
const { isAllowed: canAccreditare } = useActionPermission(AZIONE_ACCREDITA_RESO)
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

// Selezione multipla della coda accrediti. ⚠️ PrimeVue 4 non ha piu' il
// predicato per-riga sul selectionMode: la checkbox e' custom per forza, e la
// colonna e' chrome di <ListaConfigurabile> (slot `selection`) — non e' di
// catalogo, non si esporta, non si personalizza.
const selezione = ref([])

// Selezionabili = le righe che il DATABASE dichiara lavorabili. Il gate si fa
// sui codici che la riga porta (`blocco_codice`), mai su una capability per
// riga (§12.7): una capability per riga sarebbe una chiamata per riga.
const righeSelezionabili = computed(() =>
  isRiconsegna
    ? []
    : store.items.filter((r) => !r.blocco_codice && Number(r.accredito_dovuto) > 0),
)

const {
  isSelectable: isRigaAccreditabile,
  isSelected: isRigaSelezionata,
  toggleRow: toggleRiga,
  // ⛔ La terna «in pagina», non `toggleAll`/`anySelected`: questa coda e'
  //    PAGINATA e la selezione vive attraverso le pagine. Fino al 2026-08-27
  //    qui c'era `toggleAll`, che SOSTITUISCE la selezione con la pagina
  //    corrente: spuntare «tutte» a pagina 2 buttava via quanto spuntato a
  //    pagina 1, in silenzio — se ne vedeva solo il contatore del pulsante
  //    calare. Vedi il blocco in fondo a `useSelezioneToggle`.
  allInPagina: tutteSelezionate,
  anyInPagina: alcuneSelezionate,
  toggleAllInPagina: toggleTutte,
} = useSelezioneToggle({
  selected: selezione,
  selezionabili: righeSelezionabili,
  rowKey: 'resi_riga_id',
})

// Prune dopo ogni ricarica: una riga accreditata ESCE dalla coda (l'accredito
// e' registrato al verbo, non alla fattura), e una riga puo' diventare
// bloccata sotto i piedi. Senza il prune resterebbe spuntata con la checkbox
// disabilitata — il guard del BB rende il de-toggle un no-op — quindi non
// rimovibile, contata nel pulsante e ri-sottomessa a ogni giro.
watch(() => store.items, () => {
  if (!selezione.value.length) return
  selezione.value = selezione.value.filter((r) => isRigaAccreditabile(r))
})

// Azione massiva: una sola, con il conteggio nell'etichetta. Sparisce a chi non
// ha l'azione di processo — il 403 del backend resta la difesa vera, questo e'
// solo il modo di non offrire una porta chiusa.
function azioniAccredito() {
  if (isRiconsegna || !canAccreditare.value) return []
  return [{
    key: 'accredita-selezione',
    label: t('vendite.resi.accredito_azione', { n: selezione.value.length }),
    icon: MANAGE_ICONS.CONFIRM,
    severity: 'primary',
    disabled: selezione.value.length === 0,
    command: () => chiediConferma(selezione.value),
  }]
}

// Esito del fan-out (F2): il parziale si LEGGE. «19 su 20» che non dice QUALI
// non e' interpretabile — l'operatore non sa cosa riprovare.
const esitoVisible = ref(false)
const esito = ref(null)

// Scopo: la conferma. Dice quante righe, e soprattutto dice COSA SUCCEDE —
//        che il documento non nasce adesso.
function chiediConferma(righe) {
  const ids = righe.map((r) => r.resi_riga_id)
  confirmAction({
    header: t('vendite.resi.accredito_conferma_titolo'),
    message: t('vendite.resi.accredito_conferma_messaggio', { n: ids.length }),
    acceptLabel: t('vendite.resi.accredito_conferma_accetta'),
    onAccept: () => eseguiAccredito(ids),
  })
}

async function eseguiAccredito(ids) {
  // ⚠️ `execute` SCARTA GIA' l'envelope `{data: …}`: `res` E' il report, non la
  //    response axios. Leggerlo come `res.data.data` darebbe `undefined` — e a
  //    video un «0 su 0» perfettamente silenzioso.
  const res = await execute(() => accreditaRighe(ids))
  if (res === null) return
  const dati = res ?? {}
  selezione.value = []
  await store.fetchList()

  const nOk = dati.ok ?? 0
  if (dati.esito === ESITO_ACCREDITO.COMPLETATO) {
    notify.success(t('vendite.resi.accredito_esito_completato', { n: nOk }))
    return
  }
  // PARZIALE ed ERRORE mostrano l'ELENCO: il toast dice il conto, il dialog
  // dice quali righe e perche'. Il vocabolario dei tre esiti e' quello del
  // backend (`run_fan_out`), non se ne inventa un quarto.
  esito.value = dati
  esitoVisible.value = true
  const msg = t('vendite.resi.accredito_esito_parziale', {
    ok: nOk, totale: dati.totale ?? 0,
  })
  if (dati.esito === ESITO_ACCREDITO.PARZIALE) notify.warn(msg)
  else notify.error(t('vendite.resi.accredito_esito_errore', { n: dati.totale ?? 0 }))
}

// Annullo dell'accredito: il dialog (con il motivo obbligatorio e la
// distinzione fra annullare l'ACCREDITO e resettare il lotto) e' condiviso con
// il drawer del reso — una sola copia del testo, che e' la parte che conta.
// ⚠️ Da QUI si raggiunge solo se il conto della merce ha riportato la riga in
//    coda: dopo il verbo la riga ne esce. La sede principale e' il drawer del
//    reso (§30.2 del brief).
const annulloDialog = ref(false)
const annulloRiga = ref(null)

function apriAnnullo(riga) {
  annulloRiga.value = riga
  annulloDialog.value = true
}

// Params export: filtri da store.filters + search dal ref immediato + sort
// corrente. Il BE rispetta colonne visibili/ordine/permessi (DEF-1).
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.etichetta) p.etichetta = store.filters.etichetta
  // L'export segue l'ordinamento a video, nella stessa forma della fetch
  // (`paramsOrdinamento`, ripiego `desc` come lo store).
  return { ...p, ...paramsOrdinamento(store.filters) }
}

// `<ListaConfigurabile>` emette `data` direttamente. Apertura reso via reso_id
// (grana RIGA: il PK di riga e' resi_riga_id, il target azione e' reso_id).
function onRowClick(data) { emit('apri-reso', data.reso_id) }

function buildRowActions(data) {
  const azioni = [
    {
      key: 'apri-reso',
      label: t('vendite.resi.coda_apri_reso'),
      icon: MANAGE_ICONS.INSPECT,
      severity: 'primary',
      command: () => emit('apri-reso', data.reso_id),
    },
  ]
  if (isRiconsegna || !canAccreditare.value) return azioni

  // Accredito della singola riga: e' la stessa porta del massivo (una lista di
  // uno), non una seconda strada. ⚠️ Disabilitata invece che nascosta quando la
  // riga porta un `blocco_codice`: il motivo si RENDE (RowActionsMenu lo mostra
  // sotto la label), perche' il rimedio non e' dell'operatore — sta sul
  // documento di origine, e un click che restituisce un errore irrisolvibile e'
  // peggio di un'azione spenta che dice perche'.
  azioni.push({
    key: 'accredita',
    label: t('vendite.resi.accredito_azione_riga'),
    icon: MANAGE_ICONS.CONFIRM,
    disabled: !isRigaAccreditabile(data),
    // ⛔ ERA `motivo:`, E NON LO LEGGEVA NESSUNO (corretto 2026-08-26). Il
    //    campo del contratto di `RowActionsMenu` e' `tooltip`: e' da li' che il
    //    BB ricava la riga del popup (`actionMotivo`) e il tooltip inline.
    //    `action.motivo` non e' letto in nessun punto — quindi il motivo del
    //    bottone spento non e' MAI stato reso, ne' su desktop ne' su touch.
    //    Un campo dichiarato e non letto e' peggio della sua assenza: sembra
    //    presidiato. Stessa specie di `#cell-azioni` al posto di `#actions` e
    //    del campo `action` ignorato dal BB fino al 2026-08-17.
    tooltip: data.blocco_codice ? bloccoLabel(data.blocco_codice) : undefined,
    command: () => chiediConferma([data]),
  })

  // L'annullo compare solo se questa riga ha gia' un accredito registrato...
  if (Number(data.gia_accreditato) > 0) {
    // ...ed e' SPENTO col motivo quando la madre lo rifiuterebbe. Il codice
    // arriva dal DB (`vw_resi_da_accreditare.annullo_blocco_codice`, che nasce
    // da `script.fn_check_accredito_annullabile` — la stessa sede che la madre
    // chiama), mai da una regola ricalcolata qui.
    // ⚠️ Su questa superficie il caso e' RARO e va saputo: una riga esce dalla
    //    coda AL VERBO (§N9), quindi qui restano solo gli accrediti PARZIALI.
    //    La sede principale del gate e' il drawer del reso (`ResoRigheTable`).
    const blocco = data.annullo_blocco_codice || null
    azioni.push({
      key: 'annulla-accredito',
      label: t('vendite.resi.annullo_azione'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      disabled: blocco != null,
      tooltip: blocco ? annulloBloccoLabel(blocco) : undefined,
      command: () => apriAnnullo(data),
    })
  }
  return azioni
}

// Decodifica fail-visible del motivo di blocco: un codice nuovo mostra il
// codice grezzo, mai la chiave i18n letterale.
function bloccoLabel(codice) {
  return labelOrCode(t, te, `vendite.resi.coda_blocco.${codice}`, codice)
}

// Gemella della precedente per il verbo OPPOSTO. ⛔ I due blocchi NON si
// confondono: `blocco_codice` dice «non posso accreditare» e il suo unico
// valore (`GIA_ACCREDITATO`) e' esattamente la condizione che ABILITA
// l'annullo. Stessa colonna per i due avrebbe spento il bottone sbagliato.
function annulloBloccoLabel(codice) {
  return labelOrCode(t, te, `vendite.resi.annullo_blocco.${String(codice).toLowerCase()}`, codice)
}

// Etichetta del filtro documento (deep-link dal pannello situazione merce).
// Sta nello store, non solo nella query: la coda lo deve DICHIARARE.
const filtroDocumento = computed(() => {
  if (store.filters.ddt_id != null) {
    return t('vendite.resi.coda_filtro_ddt', { id: store.filters.ddt_id })
  }
  if (store.filters.ordine_id != null) {
    return t('vendite.resi.coda_filtro_ordine', { id: store.filters.ordine_id })
  }
  return null
})

function rimuoviFiltroDocumento() {
  store.filters.ddt_id = null
  store.filters.ordine_id = null
}

// Il filtro documento arriva da FUORI (deep-link della vista) oppure dal chip
// qui sopra: in entrambi i casi la ricarica la decide QUESTO componente, che e'
// l'unico a sapere di essere montato.
// ⚠️ Prima la vista provava a indovinarlo da `store.hasSearched`, che e' il
//    proxy sbagliato: e' vero anche quando la coda e' stata aperta in una
//    sessione precedente e il pannello non e' ancora montato — due fetch. Qui
//    non c'e' niente da indovinare.
watch(
  [() => store.filters.ddt_id, () => store.filters.ordine_id],
  () => {
    store.filters.offset = 0
    store.fetchList()
  },
)

// La colonna di selezione compare solo dove c'e' un verbo da esercitare: sulla
// coda ri-consegne non esiste, e a chi non ha l'azione non serve una colonna di
// checkbox che non porta da nessuna parte.
const mostraSelezione = computed(() => !isRiconsegna && canAccreditare.value)

const searchPlaceholder = computed(() =>
  isRiconsegna
    ? t('vendite.resi.coda_search_riconsegnare')
    : t('vendite.resi.coda_search_accreditare'),
)

onMounted(() => store.fetchList())

// Scopo: ricaricare la coda su richiesta di CHI STA SOPRA — serve a ResiView
//        quando il drawer reso, aperto da questa stessa scheda, ha cambiato la
//        materia della coda (accredito emesso, ri-consegna generata).
//
// ⭐ Si espone un metodo invece di lasciare che la vista chiami `fetchList` sullo
//    store: e' la stessa regola gia' scritta in `ResiView.applicaDeepLinkCoda`
//    — *«la fetch la decide il pannello della coda, che e' l'unico a sapere se
//    e' montato; provare a indovinarlo da fuori produceva una doppia
//    chiamata»*. Qui il **ref e' il test di montaggio**: i TabPanel sono
//    `lazy`, quindi la coda non attiva non esiste, il ref e' `null` e non
//    succede niente — e al suo mount fara' da se'.
function reload() {
  return store.fetchList()
}

defineExpose({ reload })
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="searchPlaceholder"  />
          </template>
          <FiltroPeriodo :periodo="periodo" />
          <Select
            v-if="!isRiconsegna"
            v-model="etichettaFilter"
            class="app-filter-w-md"
            :options="etichettaOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('vendite.resi.coda_etichetta_tutte')"
            @change="onEtichettaChange"
          />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <!-- ⚠️ La coda DEVE dire che è filtrata su un documento: un elenco corto
           senza spiegazione si legge come «non c'è quasi niente da fare», ed è
           il modo più silenzioso di far sbagliare il conto. Il chip toglie il
           filtro e ricarica. -->
      <Message
        v-if="filtroDocumento"
        severity="info"
        :closable="false"
        size="small"
      >
        {{ filtroDocumento }}
        <Button
          link
          size="small"
          :label="t('vendite.resi.coda_filtro_documento_rimuovi')"
          @click="rimuoviFiltroDocumento"
        />
      </Message>

      <ListaConfigurabile
        ref="listaRef"
        :codice="listaCodice"
        data-key="resi_riga_id"
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
        <!-- Selezione dell'accredito massivo: chrome della lista (slot
             dedicato), NON colonna di catalogo — non si esporta e non si
             personalizza. PrimeVue 4 non ha piu' il predicato per-riga sul
             selectionMode: la checkbox e' custom per forza (BB
             useSelezioneToggle, che tiene fuori dalla selezione le righe
             bloccate anche se il template dimenticasse il :disabled). -->
        <template v-if="mostraSelezione" #selection-header>
          <!-- Pagina senza righe accreditabili: il toggle sarebbe un no-op
               silenzioso — meglio spento che un click che «sembra non fare
               nulla». -->
          <Checkbox
            binary
            :model-value="tutteSelezionate"
            :indeterminate="alcuneSelezionate"
            :disabled="!righeSelezionabili.length"
            @update:model-value="toggleTutte"
          />
        </template>
        <template v-if="mostraSelezione" #selection="{ data }">
          <Checkbox
            binary
            :model-value="isRigaSelezionata(data)"
            :disabled="!isRigaAccreditabile(data)"
            @update:model-value="toggleRiga(data)"
          />
        </template>

        <template #cell-reso_numero="{ data }">
          {{ data.reso_numero || '—' }}
        </template>

        <!-- Coda accrediti: quantita' (formato numerico centralizzato). -->
        <template #cell-qta_operativa="{ data }">
          {{ formatNumber(data.qta_operativa) }}
        </template>
        <template #cell-quantita="{ data }">
          {{ formatNumber(data.quantita) }}
        </template>

        <!-- Coda accrediti, forma contatore: il conto della partita
             (tenuti/fatturati) e l'accredito dovuto (l'informazione centrale:
             «fatturata per 10, tenuta 7 → accredito 3»). -->
        <template #cell-accredito_dovuto="{ data }">
          <strong>{{ formatNumber(data.accredito_dovuto) }}</strong>
        </template>
        <template #cell-tenuti="{ data }">
          {{ formatNumber(data.tenuti) }}
        </template>
        <template #cell-fatturati="{ data }">
          {{ formatNumber(data.fatturati) }}
        </template>
        <template #cell-etichetta="{ data }">
          <Tag :value="etichettaLabel(data.etichetta)"
            :severity="etichettaAccreditoSeverity(data.etichetta)" />
        </template>

        <!-- ddt_numero nullable (forma contatore: aggancio partita via
             ordine, il join al DDT e' LEFT): mai stringa vuota. -->
        <template #cell-ddt_numero="{ data }">
          {{ data.ddt_numero || '—' }}
        </template>

        <!-- Coda ri-consegne: copertura resa/ri-consegnata/residua. -->
        <template #cell-qta_resa="{ data }">
          {{ formatNumber(data.qta_resa) }}
        </template>
        <template #cell-qta_riconsegnata="{ data }">
          {{ formatNumber(data.qta_riconsegnata) }}
        </template>
        <template #cell-qta_residua="{ data }">
          {{ formatNumber(data.qta_residua) }}
        </template>

        <!-- Stato ri-consegna derivato: Tag severity data-driven. -->
        <template #cell-stato_riconsegna="{ data }">
          <Tag :value="t(`vendite.resi.riconsegna_stato.${data.stato_riconsegna}`)"
            :severity="statoRiconsegnaSeverity(data.stato_riconsegna)" />
        </template>

        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>

        <!-- Empty-state onesto: mostrato solo dopo il primo fetch riuscito
             (hasSearched), così non lampeggia durante il caricamento. -->
        <template #empty>
          <div v-if="store.hasSearched" class="app-empty-state">
            {{ t(isRiconsegna ? 'vendite.resi.riconsegna_nessuna_riga' : 'common.no_results') }}
          </div>
        </template>
      </ListaConfigurabile>
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <!-- Annullo dell'accredito: componente condiviso con il drawer del reso. -->
    <AccreditoAnnullaDialog
      v-model:visible="annulloDialog"
      :riga="annulloRiga"
      @annullato="store.fetchList()"
    />

    <!-- Esito del giro (F2): il parziale si LEGGE. -->
    <AccreditoEsitoDialog v-model:visible="esitoVisible" :esito="esito" />
  </div>
</template>
