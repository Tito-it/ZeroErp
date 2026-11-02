<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista dei documenti generati per una sorgente specifica (Tranche M,
//        building block riusabile): la timeline dei PDF emessi — il piu'
//        recente in cima — con le azioni per riga (scarica originale,
//        ristampa fedele, aggiungi allegati) e il dettaglio inline dei file.
//
// ⭐ DAL 2026-09-27 E' LA LISTA CONFIGURABILE `documenti.documenti_sorgente`
//    (84), montata con lo scaffolding dei tab-lista (`useDrawerTabLista` +
//    `<DrawerTabLista>`). Era una `DataTable` grezza su uno store scritto a
//    mano che non mandava `page_size`: il backend ne dava 50 e la lista si
//    fermava li' SENZA DIRLO — nessun paginatore, nessun conteggio. Ora ha
//    pagine, ordinamento, ricerca, «Personalizza colonne» ed «Espandi tutte».
//
// ⭐ IL PADRE E' LA SORGENTE, l'emittente e' quello del documento. La lista a
//    catalogo non e' certificata multi-emittente: senza `emittenteFiscaleId`
//    il super admin su «Tutti» vedrebbe il pannello «scegli un emittente»
//    dentro il dialog di un documento che gli sta gia' dicendo da quale
//    emittente viene. Il chiamante lo passa dalla riga o dal dettaglio che ha
//    in mano.
//
//        v1: niente azioni di stato (ARCHIVIA/ANNULLA) ne' eliminazione
//        (trigger DB block_delete su documenti_generati).
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useDocumentiSorgenteListaStore } from '../stores/documentiSorgenteLista'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useNotify } from '../../core/composables/useNotify'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DocumentoEmissioneDialog from './DocumentoEmissioneDialog.vue'
import DocumentoFileElenco from './DocumentoFileElenco.vue'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { downloadBlob } from '../../core/utils/download'
import { MANAGE_ICONS } from '../../core/constants'

const props = defineProps({
  // ⚠️ Letto UNA volta, alla creazione: sceglie lo store della sorgente
  //    (`useDocumentiSorgenteListaStore`). Ogni chiamante lo passa costante.
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: [Number, null], required: true },
  // L'emittente del documento sorgente (PK `emittenti_fiscali`), gia'
  // fissato dal contesto che apre la lista. ⛔ Obbligatorio nei fatti: un
  // documento l'emittente ce l'ha sempre, e senza la lista NON legge (resta in
  // caricamento — il padre composto di `useListaStoreCore`). `null` e' solo
  // «il dettaglio non e' ancora arrivato».
  emittenteFiscaleId: { type: [Number, null], default: null },
  // Se true, abilita l'azione di riga "Aggiungi allegati" (append di file
  // secondari al documento generato). Il caller la attiva quando lo stato
  // della sorgente lo consente (es. offerta in EMESSA).
  allowAllegati: { type: Boolean, default: false },
  // Se true, a ogni pagina caricata apre il dettaglio di tutte le righe
  // (principale + allegati). Usato dal dialog dedicato
  // `PdfDocumentiSorgenteDialog`: in modalita' picker ha senso mostrare
  // subito il contenuto completo.
  defaultExpanded: { type: Boolean, default: false },
})

const { t } = useI18n()
const notify = useNotify()
const store = useDocumentiSorgenteListaStore(props.sorgenteCode)
const azioni = useDocumentiPerSorgenteStore()

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(store, {
  // Il padre composto: la sorgente e l'emittente del documento. ⚠️ Finche'
  //    l'emittente manca la lista non legge e resta in caricamento.
  parentId: {
    sorgenteId: () => props.sorgenteId,
    emittenteId: () => props.emittenteFiscaleId,
  },
  searchTableOptions: { defaultSortField: 'generato_at', defaultSortOrder: 'desc' },
})

// Stato dialog append allegati (modalita' non-advances-state).
const allegatiDialogVisible = ref(false)
const allegatiDocId = ref(null)
const allegatiLoading = ref(false)
// Versione dei file per documento: incrementata dopo un append, fa rileggere
// il dettaglio gia' aperto (`DocumentoFileElenco`, prop `versione`).
const versioneFile = ref({})

// Scopo: con `defaultExpanded`, apre il dettaglio di tutte le righe di OGNI
//        pagina caricata. ⚠️ Dopo `nextTick`: `espandiTutte` legge le righe
//        dalla prop della lista, che arriva un giro dopo lo store.
watch(
  () => store.items,
  async (righe) => {
    if (!props.defaultExpanded || !righe?.length) return
    await nextTick()
    listaRef.value?.espandiTutte?.()
  },
)

// Scopo: Severity stato applicativo documento (DDL CHECK chiuso v1).
function statoSeverity(stato) {
  if (stato === 'GENERATO') return 'info'
  if (stato === 'ARCHIVIATO') return 'success'
  if (stato === 'ANNULLATO') return 'danger'
  return 'secondary'
}

// Presenza del file originale: la persistenza dei file e' iniziata il
// 2026-07-21, e per i documenti anteriori non c'e'. `!== false` e non un
// truthy-check: un backend che non mandasse il campo non deve spegnere il
// download di tutti.
function haFile(row) {
  return row.has_file_principale !== false
}

// Scopo: le azioni di riga distinguono i TRE percorsi, che prima si
//        confondevano in uno solo (brief ristampa-fedele §5.2):
//         1. «Scarica originale» — il file prodotto allora, byte per byte.
//            Disponibile SOLO se il file esiste: per i documenti anteriori
//            alla persistenza l'azione e' DISABILITATA CON LA RAGIONE invece
//            di fallire con un 404 generico (§5.2.2).
//         2. «Ristampa fedele» — ri-renderizza l'originale dalla versione di
//            template di allora e dal contesto congelato. E' l'unico percorso
//            possibile sui documenti senza file, e la verifica di un file
//            conservato.
//        Il terzo percorso — «Genera nuovo documento», che produce un
//        documento DIVERSO col modello di oggi — non vive qui: e' un'azione
//        della sorgente (pulsante di emissione), non di un documento gia'
//        generato. Tenerlo fuori da questo menu e' parte del chiarimento.
function buildRowActions(row) {
  const conFile = haFile(row)
  const actions = [
    {
      key: 'download',
      label: t('documenti.lista.action_download'),
      icon: MANAGE_ICONS.DOWNLOAD,
      severity: 'primary',
      disabled: !conFile,
      tooltip: conFile ? '' : t('documenti.lista.download_non_disponibile'),
      command: () => onDownload(row.id),
    },
    {
      key: 'ristampa',
      label: t('documenti.lista.action_ristampa_fedele'),
      icon: MANAGE_ICONS.STAMPA,
      tooltip: t('documenti.lista.ristampa_fedele_hint'),
      command: () => onRistampaFedele(row.id),
    },
  ]
  if (props.allowAllegati) {
    actions.push({
      key: 'allegati',
      label: t('documenti.lista.action_aggiungi_allegati'),
      icon: MANAGE_ICONS.ALLEGATI,
      command: () => openAllegati(row.id),
    })
  }
  return actions
}

function openAllegati(documentoId) {
  allegatiDocId.value = documentoId
  allegatiDialogVisible.value = true
}

// Scopo: Append allegati al documento (modalita' non-advances-state). Su
//        conferma carica i file scelti come file secondari del documento.
async function onAllegatiConferma(payload) {
  const files = payload?.files || []
  if (!files.length || allegatiDocId.value == null) return
  const docId = allegatiDocId.value
  allegatiLoading.value = true
  try {
    azioni.setSorgente(props.sorgenteCode, props.sorgenteId)
    await azioni.aggiungiAllegati(docId, files)
    notify.success(t('documenti.allegati.aggiunti_ok'))
    allegatiDialogVisible.value = false
    // Il dettaglio della riga, se aperto, rilegge i file e mostra il nuovo.
    versioneFile.value[docId] = (versioneFile.value[docId] ?? 0) + 1
  } catch (err) {
    notify.error(t('documenti.allegati.errore'))
    console.error('aggiungiAllegati', err)
  } finally {
    allegatiLoading.value = false
  }
}

async function onDownload(documentoId) {
  try {
    azioni.setSorgente(props.sorgenteCode, props.sorgenteId)
    const { blob, fileName } = await azioni.download(documentoId)
    downloadBlob(blob, fileName)
  } catch (err) {
    notify.error(t('documenti.genera_pdf.download_error'))
    console.error('download', err)
  }
}

// Scopo: ristampa fedele (percorso 3). Il PDF si scarica come gli altri; la
//        differenza sta nel VERDETTO che si comunica dopo: se i byte non
//        coincidono con l'originale il documento e' fedele nel contenuto ma
//        non nei byte (renderer non deterministico, decisione §8.2) e va
//        detto — un warn, non un errore. `null` = header assente: non
//        verificabile, che e' diverso da "diverso".
async function onRistampaFedele(documentoId) {
  try {
    azioni.setSorgente(props.sorgenteCode, props.sorgenteId)
    const { blob, fileName, pdfHashMatch } = await azioni.ristampaFedele(documentoId)
    downloadBlob(blob, fileName)
    if (pdfHashMatch === false) {
      notify.warn(t('documenti.lista.ristampa_fedele_contenuto'))
    } else {
      notify.success(t('documenti.lista.ristampa_fedele_ok'))
    }
  } catch (err) {
    notify.error(t('documenti.lista.ristampa_fedele_error'))
    console.error('ristampaFedele', err)
  }
}
</script>

<template>
  <!-- `app-escape` alla radice: il BB vive tipicamente in drawer post-DRAFT
       il cui contenuto e' `app-readonly` (pointer-events: none). Le azioni
       qui sono tutte di lettura (download/espansione/refresh), lecite anche
       in permesso LETTURA, quindi l'escape e' incondizionato. Evita che ogni
       caller debba ricordarsi il wrapper (regola del 2: ContrattoDrawer lo
       aveva, PreventiviDrawer no e la lista risultava non cliccabile). -->
  <div class="app-escape">
    <DrawerTabLista
      ref="listaRef"
      codice="documenti.documenti_sorgente"
      :emittente-esplicito="emittenteFiscaleId"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('documenti.lista.search_placeholder')"
        />
      </template>

      <!-- La frase del dominio al posto dell'empty-state generico, e solo se
           la lettura e' riuscita: con `erroreCaricamento` la lista e' vuota
           per un'altra ragione. -->
      <template #empty>
        <span v-if="!store.erroreCaricamento">{{ t('documenti.lista.empty') }}</span>
      </template>

      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
      </template>

      <!-- Presenza del file originale: dice a colpo d'occhio quali documenti
           si possono scaricare com'erano e quali vanno ri-renderizzati. Non
           e' un difetto del documento (la persistenza e' iniziata dopo), per
           questo e' `secondary` e non `danger`. -->
      <template #cell-originale="{ data }">
        <Tag
          :value="haFile(data)
            ? t('documenti.lista.originale_presente')
            : t('documenti.lista.originale_assente')"
          :severity="haFile(data) ? 'success' : 'secondary'"
        />
      </template>

      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>

      <!-- Dettaglio inline: i file del documento (principale + allegati),
           letti quando la riga si apre. -->
      <template #row-expansion="{ data }">
        <DocumentoFileElenco
          :sorgente-code="sorgenteCode"
          :sorgente-id="sorgenteId"
          :documento-id="data.id"
          :versione="versioneFile[data.id] ?? 0"
        />
      </template>
    </DrawerTabLista>

    <!-- Append allegati a un documento gia' generato (modalita' append). -->
    <DocumentoEmissioneDialog
      v-if="allowAllegati"
      v-model:visible="allegatiDialogVisible"
      :sorgente-code="sorgenteCode"
      :sorgente-id="sorgenteId"
      :advances-state="false"
      :header="t('documenti.allegati.dialog_titolo')"
      :confirm-label="t('documenti.allegati.conferma')"
      :loading="allegatiLoading"
      @confirm="onAllegatiConferma"
    />
  </div>
</template>
