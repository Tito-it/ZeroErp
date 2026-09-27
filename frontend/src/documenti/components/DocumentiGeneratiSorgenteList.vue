<script setup>
// Scopo: Lista documenti generati per una sorgente specifica
//        (Tranche M building block riusabile). Visualizza la
//        timeline (ORDER BY `generato_at DESC` lato BE) con azioni
//        per riga: Scarica PDF (RowActionsMenu).
//
//        v1: niente azioni di stato (ARCHIVIA/ANNULLA) ne' eliminazione
//        (trigger DB block_delete su documenti_generati).
//
//        Riusabile da qualsiasi caller che imposti la coppia
//        (sorgenteCode, sorgenteId) sullo store. Il caller e' anche
//        responsabile di chiamare `fetchList` al cambio di sorgente.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useNotify } from '../../core/composables/useNotify'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DocumentoEmissioneDialog from './DocumentoEmissioneDialog.vue'
import { downloadBlob } from '../../core/utils/download'
import { formatSize } from '../../core/utils/format'
import { displayTimestamp } from '../../core/utils/date'
import { MANAGE_ICONS } from '../../core/constants'

const props = defineProps({
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: [Number, null], required: true },
  // Se true, fetch automatico al mount/cambio props.
  autoFetch: { type: Boolean, default: true },
  // Se true, quando la lista e' vuota mostra solo il messaggio empty.
  hideHeaderWhenEmpty: { type: Boolean, default: false },
  // Se true, abilita l'azione di riga "Aggiungi allegati" (append di file
  // secondari al documento generato). Il caller la attiva quando lo stato
  // della sorgente lo consente (es. offerta in EMESSA).
  allowAllegati: { type: Boolean, default: false },
  // Se true, dopo il fetchList iniziale espande tutte le righe e carica
  // i file (principale + allegati) per ognuna. Usato dal dialog dedicato
  // `PdfDocumentiSorgenteDialog`: in modalita' picker ha senso mostrare
  // subito il contenuto completo. Default off per i drawer (anagrafiche/
  // preventivi/contratti) dove la lista e' compatta e l'expand on-demand
  // mantiene la UI snella.
  defaultExpanded: { type: Boolean, default: false },
})

const { t } = useI18n()
const store = useDocumentiPerSorgenteStore()
const notify = useNotify()

// Stato dialog append allegati (modalita' non-advances-state).
const allegatiDialogVisible = ref(false)
const allegatiDocId = ref(null)
const allegatiLoading = ref(false)

// Expansion riga: lista file (principale + allegati) per documento.
// Lazy fetch on row expand; cache su filesPerDoc.
const expandedRows = ref({})
const filesPerDoc = ref({})
const filesLoading = ref({})

watch(
  () => [props.sorgenteCode, props.sorgenteId],
  async ([code, id]) => {
    if (!code || !id) return
    store.setSorgente(code, id)
    if (props.autoFetch) {
      try { await store.fetchList() } catch { /* errore gia' gestito dallo store */ }
    }
    if (props.defaultExpanded) {
      expandAllRows()
    }
  },
  { immediate: true },
)

// Scopo: espande tutte le righe attualmente caricate e fa il fetch dei
//        file di ciascuna (lazy: salta se gia' in cache). Invocato post-
//        fetchList quando defaultExpanded=true.
function expandAllRows() {
  const items = store.items || []
  if (!items.length) return
  const expanded = {}
  for (const row of items) {
    if (row?.id != null) expanded[row.id] = true
  }
  expandedRows.value = expanded
  for (const row of items) {
    if (row?.id != null) loadFiles(row.id)
  }
}

// Scopo: Severity stato applicativo documento (DDL CHECK chiuso v1).
function statoSeverity(stato) {
  if (stato === 'GENERATO') return 'info'
  if (stato === 'ARCHIVIATO') return 'success'
  if (stato === 'ANNULLATO') return 'danger'
  return 'secondary'
}

const isEmpty = computed(() => !store.loading && (store.items?.length ?? 0) === 0)
const showListChrome = computed(() => !isEmpty.value || !props.hideHeaderWhenEmpty)

// Scopo: le azioni di riga distinguono i TRE percorsi, che prima si
//        confondevano in uno solo (brief ristampa-fedele §5.2):
//         1. «Scarica originale» — il file prodotto allora, byte per byte.
//            Disponibile SOLO se il file esiste: la persistenza dei file e'
//            iniziata il 2026-07-21, e per i documenti anteriori l'azione
//            e' DISABILITATA CON LA RAGIONE invece di fallire con un 404
//            generico (§5.2.2).
//         2. «Ristampa fedele» — ri-renderizza l'originale dalla versione di
//            template di allora e dal contesto congelato. E' l'unico percorso
//            possibile sui documenti senza file, e la verifica di un file
//            conservato.
//        Il terzo percorso — «Genera nuovo documento», che produce un
//        documento DIVERSO col modello di oggi — non vive qui: e' un'azione
//        della sorgente (pulsante di emissione), non di un documento gia'
//        generato. Tenerlo fuori da questo menu e' parte del chiarimento.
function buildRowActions(row) {
  const haFile = row.has_file_principale !== false
  const actions = [
    {
      key: 'download',
      label: t('documenti.lista.action_download'),
      icon: MANAGE_ICONS.DOWNLOAD,
      severity: 'primary',
      disabled: !haFile,
      tooltip: haFile ? '' : t('documenti.lista.download_non_disponibile'),
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
    store.setSorgente(props.sorgenteCode, props.sorgenteId)
    await store.aggiungiAllegati(docId, files)
    notify.success(t('documenti.allegati.aggiunti_ok'))
    allegatiDialogVisible.value = false
    // Auto-espandi la riga e ricarica i file per mostrare il nuovo allegato.
    expandedRows.value[docId] = true
    await loadFiles(docId, { force: true })
  } catch (err) {
    notify.error(t('documenti.allegati.errore'))
    console.error('aggiungiAllegati', err)
  } finally {
    allegatiLoading.value = false
  }
}

async function onDownload(documentoId) {
  try {
    const { blob, fileName } = await store.download(documentoId)
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
    const { blob, fileName, pdfHashMatch } = await store.ristampaFedele(documentoId)
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

// Scopo: lazy fetch dei file del documento all'espansione della riga.
//        Cache per documentoId; invalidata dopo upload allegati per
//        rifletter immediatamente il nuovo file. Mutazione diretta delle
//        chiavi su ref di tipo `ref({})`: Vue 3 traccia gia' le mutazioni
//        sulle proprieta' (no bisogno di spread per reattivita').
async function loadFiles(documentoId, { force = false } = {}) {
  if (!force && filesPerDoc.value[documentoId] !== undefined) return
  filesLoading.value[documentoId] = true
  try {
    store.setSorgente(props.sorgenteCode, props.sorgenteId)
    const data = await store.listFiles(documentoId)
    filesPerDoc.value[documentoId] = data?.results || []
  } catch (err) {
    console.error('listFiles', err)
    filesPerDoc.value[documentoId] = []
  } finally {
    filesLoading.value[documentoId] = false
  }
}

function onRowExpand(event) {
  loadFiles(event.data.id)
}

async function onDownloadFile(documentoId, fileId) {
  try {
    store.setSorgente(props.sorgenteCode, props.sorgenteId)
    const { blob, fileName } = await store.downloadFile(documentoId, fileId)
    downloadBlob(blob, fileName)
  } catch (err) {
    notify.error(t('documenti.genera_pdf.download_error'))
    console.error('downloadFile', err)
  }
}

async function reload() {
  try { await store.fetchList() } catch { /* gia' gestito */ }
}
</script>

<template>
  <!-- `app-escape` alla radice: il BB vive tipicamente in drawer post-DRAFT
       il cui contenuto e' `app-readonly` (pointer-events: none). Le azioni
       qui sono tutte di lettura (download/espansione/refresh), lecite anche
       in permesso LETTURA, quindi l'escape e' incondizionato. Evita che ogni
       caller debba ricordarsi il wrapper (regola del 2: ContrattoDrawer lo
       aveva, PreventiviDrawer no e la lista risultava non cliccabile). -->
  <div class="documenti-sorgente-list app-escape">
    <div v-if="showListChrome" class="section-header">
      <h4>{{ t('documenti.lista.title') }}</h4>
      <Button
        :icon="MANAGE_ICONS.RELOAD"
        text
        size="small"
        :loading="store.loading"
        @click="reload"
        :tooltip="t('common.refresh')"
      />
    </div>

    <DataTable
      v-if="showListChrome"
      :value="store.items"
      :loading="store.loading"
      striped-rows
      class="app-datatable"
      data-key="id"
      v-model:expandedRows="expandedRows"
      @row-expand="onRowExpand"
    >
      <Column expander style="width: 36px;" />
      <Column field="progressivo_sorgente" :header="t('documenti.lista.col_progressivo')" style="width: 80px;" />
      <Column field="generato_at" :header="t('documenti.lista.col_generato_at')" style="width: 180px;">
        <template #body="{ data }">
          {{ displayTimestamp(data.generato_at) }}
        </template>
      </Column>
      <Column field="titolo" :header="t('documenti.lista.col_titolo')" />
      <Column field="nome_file" :header="t('documenti.lista.col_nome_file')" style="width: 200px;" />
      <Column field="stato" :header="t('documenti.lista.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
        </template>
      </Column>
      <!-- Presenza del file originale: dice a colpo d'occhio quali documenti
           si possono scaricare com'erano e quali vanno ri-renderizzati. Non
           e' un difetto del documento (la persistenza e' iniziata dopo), per
           questo e' `secondary` e non `danger`. -->
      <Column :header="t('documenti.lista.col_originale')" style="width: 110px;">
        <template #body="{ data }">
          <Tag
            :value="data.has_file_principale !== false
              ? t('documenti.lista.originale_presente')
              : t('documenti.lista.originale_assente')"
            :severity="data.has_file_principale !== false ? 'success' : 'secondary'"
          />
        </template>
      </Column>
      <Column :header="''" class="app-col-actions" style="width: 80px;">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>

      <!-- Expansion: lista file del documento (principale + allegati),
           con badge tipo e download per id. -->
      <template #expansion="{ data }">
        <div class="documenti-sorgente-list__files">
          <div v-if="filesLoading[data.id]" class="app-text-muted">
            {{ t('documenti.allegati.files_loading') }}
          </div>
          <ul v-else-if="filesPerDoc[data.id]?.length" class="documenti-sorgente-list__file-list">
            <li v-for="f in filesPerDoc[data.id]" :key="f.id" class="documenti-sorgente-list__file">
              <Tag
                :value="f.is_principale
                  ? t('documenti.allegati.tipo_principale')
                  : t('documenti.allegati.tipo_allegato')"
                :severity="f.is_principale ? 'info' : 'secondary'"
              />
              <span class="documenti-sorgente-list__file-name">{{ f.file_name }}</span>
              <span class="documenti-sorgente-list__file-size">{{ formatSize(f.file_size_bytes) }}</span>
              <Button
                :icon="MANAGE_ICONS.DOWNLOAD"
                text
                rounded
                size="small"
                v-tooltip.top="t('documenti.lista.action_download')"
                @click="onDownloadFile(data.id, f.id)"
              />
            </li>
          </ul>
          <div v-else class="app-text-muted">
            {{ t('documenti.allegati.files_empty') }}
          </div>
        </div>
      </template>
    </DataTable>

    <div v-if="isEmpty" class="app-text-muted text-center mt-1">
      {{ t('documenti.lista.empty') }}
    </div>

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

<style scoped>
.documenti-sorgente-list .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.documenti-sorgente-list__files {
  padding: 0.5rem 1rem;
}
.documenti-sorgente-list__file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.documenti-sorgente-list__file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--app-border-color);
  border-radius: var(--app-border-radius);
}
.documenti-sorgente-list__file-name {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.documenti-sorgente-list__file-size {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
</style>
