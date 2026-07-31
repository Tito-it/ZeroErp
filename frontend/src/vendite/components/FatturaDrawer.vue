<script setup>
// Scopo: Drawer di CONSULTAZIONE della fattura — il documento a video, nello
//        stesso formato degli altri documenti vendite: testata (cliente,
//        emittente, pagamento, totali) in alto, righe al centro, riepilogo IVA
//        in fondo.
//        Generico e richiamabile da più punti: dal kebab delle righe fatture
//        del `LottoDrawer` e dal registry `documentoDrawers` (tappe Passaggi,
//        drill-down cruscotti); domani ricerca universale, portale.
//        SOLA LETTURA per costruzione: la fattura è prodotta dalla pipeline e
//        oltre EMESSA le righe sono congelate a DB
//        (`trgfn_fatture_righe_guard_congelamento`). Le azioni di processo
//        (emissione, numerazione, ristampa massiva) restano nel cockpit.
//        I dati arrivano dagli STESSI lettori che alimentano il contesto del
//        PDF: ciò che si vede qui è ciò che finisce nel documento fiscale.
//        Brief: docs/it/dev/work-done/brief-be-fe-drawer-fattura.md
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RiepilogoIvaTable from '../../core/components/RiepilogoIvaTable.vue'
import ScadenzeSintesi from '../../core/components/ScadenzeSintesi.vue'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import FatturaNoteDrawer from './FatturaNoteDrawer.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { SORGENTE_CODES } from '../../documenti/constants'
import {
  DRAWER_WIDTH,
  MANAGE_ICONS,
  READONLY_DOMAINS,
  READONLY_MODELS,
} from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate } from '../../core/utils/date'
import { formatCurrency, formatIvaLabel, formatNumber } from '../../core/utils/format'
import { statoDocFiscaleSeverity } from '../../core/utils/severity'
import { downloadBlob } from '../../core/utils/download'
import { getFatturaDettaglio } from '../api/fatture'

const props = defineProps({
  visible: { type: Boolean, default: false },
  fatturaId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])
const { t } = useI18n()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const { execute } = useApiHandler()
const docStore = useDocumentiPerSorgenteStore()

// Livello oggetto: `vendite.fattura` è in `config.area_model_overrides` e il
// BE dichiara `model_permission` sia sul dettaglio sia sulle note — il drawer
// deve rispettarlo (brief §11). Il composable fa anche `provide()` ai figli:
// il `NoteDrawer` (via `useInjectReadonly`) eredita il readonly di OGGETTO,
// non solo quello d'area del provider a monte.
const { isReadonly, isBlocked } = useReadonlyMode(
  READONLY_DOMAINS.VENDITE, READONLY_MODELS.FATTURA,
)

// Guard di versione: il drawer è un'istanza unica riusata cambiando
// `fatturaId` — due aperture rapide su fatture diverse sono due fetch in volo
// sullo stesso `dettaglio`. Senza il tag, la risposta arrivata per ultima
// vince anche se è quella della fattura sbagliata.
const fv = useFetchVersion()

// ------------------------------------------------------------------ stato
const dettaglio = ref(null)
const loading = ref(false)
const pdfDialog = ref(false)
const noteDrawer = ref(false)

const fattura = computed(() => dettaglio.value?.fattura ?? null)
const righe = computed(() => dettaglio.value?.righe ?? [])
const riepilogoIva = computed(() => dettaglio.value?.riepilogo_iva ?? [])
const scadenze = computed(() => dettaglio.value?.scadenze ?? [])

// Counter note del badge. Ref e non computed sul dettaglio perché ha DUE
// fonti: il payload BE all'apertura (`contatori.note`, nessun round-trip
// aggiuntivo) e il sub-drawer note dopo ogni create/update/delete — che il
// totale aggiornato ce l'ha già e lo passa con `@saved`. Il conteggio BE usa
// lo stesso perimetro della lista note, quindi i due valori non divergono.
const noteCount = ref(0)

// Numero fiscale: una fattura in DRAFT ha `numero` NULL — il progressivo si
// assegna alla numerazione. Renderlo esplicito, mai una cella vuota: in un
// documento fiscale un vuoto si legge come dato perso, non come stato del
// processo.
const numeroDisplay = computed(() => {
  const f = fattura.value
  if (!f) return ''
  if (!f.numero) return t('vendite.fatture.non_numerata')
  return `${f.serie ? f.serie + ' ' : ''}${f.numero}${f.anno ? '/' + f.anno : ''}`
})

// ------------------------------------------------------------------ load
// Scopo: carica il documento; 404/fuori scope → toast + chiusura (il BE non
//        distingue inesistente da fuori scope, e il drawer non deve provarci).
async function loadDettaglio() {
  if (!props.fatturaId) return
  const my = fv.tag()
  loading.value = true
  try {
    const res = await loadDetailOrClose(() => getFatturaDettaglio(props.fatturaId))
    if (!fv.isCurrent(my)) return
    if (res == null) return
    dettaglio.value = res.data?.data ?? null
    noteCount.value = Number(dettaglio.value?.contatori?.note ?? 0)
  } finally {
    if (fv.isCurrent(my)) loading.value = false
  }
}

watch(
  () => [props.visible, props.fatturaId],
  async ([visible]) => {
    // Dialog documenti e drawer note sono teleported (fuori dal DOM di questo
    // drawer): senza chiusura esplicita resterebbero aperti orfani quando il
    // padre si chiude. Stesso presidio del `LottoDrawer`.
    pdfDialog.value = false
    noteDrawer.value = false
    if (!visible || !props.fatturaId) {
      // Invalida le fetch in volo: una risposta tardiva non deve ripopolare
      // il drawer chiuso (o quello riaperto su un'altra fattura).
      fv.invalidate()
      return
    }
    dettaglio.value = null
    noteCount.value = 0
    await loadDettaglio()
  },
  { immediate: true },
)

// Campi della testata come DATI e non come markup ripetuto: dodici blocchi
// label/valore copiati a mano sono dodici occasioni di sbagliare una chiave
// senza che nulla se ne accorga (a video comparirebbe solo un '—').
// ⚠️ `labelKey` con la chiave i18n COMPLETA e LETTERALE, mai costruita a
// pezzi: è la forma che `scripts/check_i18n_keys.py` sa verificare
// (`RE_KEYPROP`). Un `t(\`vendite.fatture.${k}\`)` diventerebbe un "punto
// cieco" del guard, cioè esattamente il difetto silenzioso che quel guard
// esiste per intercettare.
const campiCliente = computed(() => {
  const f = fattura.value ?? {}
  return [
    { labelKey: 'vendite.fatture.cliente', value: f.ragione_sociale_completa },
    { labelKey: 'vendite.fatture.id_fiscale', value: f.id_fiscale_univoco_cf_piva },
    { labelKey: 'vendite.fatture.indirizzo', value: f.cliente_indirizzo },
    { labelKey: 'vendite.fatture.ba', value: f.ba_codice },
  ]
})

const campiDocumento = computed(() => {
  const f = fattura.value ?? {}
  return [
    { labelKey: 'vendite.fatture.tipo_doc', value: f.tipo_doc_fiscale_descrizione },
    { labelKey: 'vendite.fatture.emittente', value: f.emittente_denominazione },
    { labelKey: 'vendite.fatture.pagamento', value: f.pagamento_modalita_codice },
    {
      labelKey: 'vendite.fatture.data_contabilizzazione',
      value: f.data_contabilizzazione ? displayDate(f.data_contabilizzazione) : null,
    },
  ]
})

// Totali di CHIUSURA, resi sotto il riepilogo IVA: imponibile e imposta NON si
// ripetono qui — sono già il footer di quadratura di `RiepilogoIvaTable`.
// Restano bollo e arrotondamento (solo se valorizzati: sono rettifiche, non
// voci fisse del documento) e le due righe forti di totale.
// ⚠️ `totale_doc` NON è la somma del riepilogo IVA: include bollo e
// arrotondamento. È il numero della testata, l'unico autorevole.
const campiTotali = computed(() => {
  const f = fattura.value ?? {}
  const arrotondamento = Number(f.arrotondamento_attuale ?? 0)
  return [
    {
      labelKey: 'vendite.fatture.bollo',
      importo: f.bollo_importo,
      visible: f.bollo_applicato === true,
    },
    {
      labelKey: 'vendite.fatture.arrotondamento',
      importo: f.arrotondamento_attuale,
      visible: arrotondamento !== 0,
    },
    { labelKey: 'vendite.fatture.totale_doc', importo: f.totale_doc, forte: true },
    { labelKey: 'vendite.fatture.totale_a_pagare', importo: f.totale_a_pagare, forte: true },
  ].filter((c) => c.visible !== false)
})

// Utility del billing account: qualificatore di contesto della fattura, reso
// sotto lo stato. Descrizione con fallback sul codice (`utility_codice` è
// sempre valorizzato, la descrizione può mancare su config incomplete).
const utilityLabel = computed(() => {
  const f = fattura.value ?? {}
  return f.utility_descrizione || f.utility_codice || null
})

// Scopo: sconto riga — percentuale formattata it-IT solo se > 0, '—'
//        altrimenti. NB: dal BE i numeric arrivano come STRINGA ("0.00" è
//        truthy): il confronto va fatto sul numero, mai sulla stringa.
function scontoLabel(row) {
  const v = Number(row.sconto_percentuale)
  if (!Number.isFinite(v) || v === 0) return '—'
  return `${formatNumber(row.sconto_percentuale, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}%`
}

// ------------------------------------------------------------------ azioni
// Nessun verbo di modifica: consultazione, stampa, archivio PDF e note. La
// stampa è una LETTURA (render on-the-fly, nessun record): disponibile anche
// in sola lettura, come nel `LottoDrawer` (C-8).

// Scopo: anteprima PDF sincrona on-the-fly («Vedi stampa», brief §4): render
//        della fattura corrente via motore documentale, download immediato.
async function anteprimaFattura() {
  docStore.setSorgente(SORGENTE_CODES.FATTURA, props.fatturaId)
  const result = await execute(() => docStore.anteprima({}))
  if (result) downloadBlob(result.blob, result.fileName)
}

const drawerActions = computed(() => [
  {
    key: 'anteprima',
    kind: 'manage',
    label: t('vendite.fatture.azione_anteprima'),
    icon: MANAGE_ICONS.PDF,
    disabled: !props.fatturaId,
    command: anteprimaFattura,
  },
  {
    key: 'documenti',
    kind: 'manage',
    label: t('vendite.fatture.azione_documenti'),
    icon: MANAGE_ICONS.ARCHIVE,
    disabled: !props.fatturaId,
    command: () => { pdfDialog.value = true },
  },
  {
    key: 'note',
    kind: 'manage',
    label: t('vendite.fatture.azione_note'),
    icon: MANAGE_ICONS.NOTE,
    // Badge solo se ci sono note: `null` = nessun badge (il BB nasconde la
    // pillola su null/''), 0 stamperebbe uno zero che non informa.
    badge: noteCount.value > 0 ? noteCount.value : null,
    disabled: !props.fatturaId,
    command: () => { noteDrawer.value = true },
  },
])

// Scopo: allinea il badge al totale note comunicato dal sub-drawer dopo un
//        create/update/delete. Nessuna rilettura del dettaglio: ricaricarlo
//        mentre il drawer note è aperto sopra rigenererebbe `righe`, cioè le
//        opzioni del select riga che il figlio sta usando.
function onNoteSaved(total) {
  if (typeof total === 'number' && Number.isFinite(total)) noteCount.value = total
}

</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @update:visible="(v) => { if (!v) onClose() }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :title="t('vendite.fatture.drawer_titolo')" :icon="NAV_ICONS.FATTURE" />
    </template>

    <!-- Livello oggetto BLOCCATO: pannello sostitutivo (safety net — il BE
         risponde comunque 403 sul dettaglio). -->
    <AccessoBloccatoPanel v-if="isBlocked" />

    <div v-else class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">
        <div v-if="loading && !fattura" class="app-loading">
          <i class="pi pi-spin pi-spinner" />
        </div>

        <template v-if="fattura">
          <!-- Header: numero e data emissione etichettati (in un documento
               fiscale un valore nudo non dice quale dei due è). Il cliente non
               sta qui: è la prima voce della sezione Cliente. -->
          <DrawerEntityHeader>
            <span class="app-drawer-header-muted">{{ t('vendite.fatture.label_numero') }}</span>
            <Tag :value="numeroDisplay" severity="secondary" />
            <template v-if="fattura.data">
              <span class="app-drawer-header-muted">
                {{ t('vendite.fatture.data_emissione') }}
              </span>
              <span>{{ displayDate(fattura.data) }}</span>
            </template>
            <template #status>
              <!-- Stato in alto, utility sotto: è il contesto del documento
                   (quale servizio si sta fatturando), non un suo stato. -->
              <div class="app-drawer-header-status-stack">
                <Tag
                  v-if="fattura.stato_descrizione"
                  :value="fattura.stato_descrizione"
                  :severity="statoDocFiscaleSeverity(fattura.stato_codice_interno)"
                />
                <Tag v-if="utilityLabel" :value="utilityLabel" severity="info" />
              </div>
            </template>
          </DrawerEntityHeader>

          <DrawerActionsBar :actions="drawerActions" />

          <!-- Cliente e Documento affiancati (`form-grid-2col`, collassa a una
               colonna su schermi stretti): due schede corte, nessuna ragione di
               incolonnarle su un drawer WIDE. -->
          <div class="form-grid-2col">
            <div>
              <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_cliente') }}</h4></div>
              <div v-for="c in campiCliente" :key="c.labelKey" class="app-doc-campo">
                <span class="app-doc-campo-label">{{ t(c.labelKey) }}</span>
                <span>{{ c.value || '—' }}</span>
              </div>
            </div>

            <div>
              <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_documento') }}</h4></div>
              <div v-for="c in campiDocumento" :key="c.labelKey" class="app-doc-campo">
                <span class="app-doc-campo-label">{{ t(c.labelKey) }}</span>
                <span>{{ c.value || '—' }}</span>
              </div>
              <!-- Scadenza: la prossima rata PER DATA, col chip che apre il
                   piano completo. Non è uno stato di pagamento — il modello non
                   sa quale rata sia stata incassata (vedi useScadenzeSintesi). -->
              <div class="app-doc-campo">
                <span class="app-doc-campo-label">
                  {{ t('vendite.fatture.prossima_rata') }}
                </span>
                <ScadenzeSintesi :scadenze="scadenze" />
              </div>
            </div>
          </div>

          <!-- Righe. Fonte: vw_fattura_righe_esposte (kit già risolti). -->
          <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_righe') }}</h4></div>
          <!-- Niente `data-key`: le righe KIT_PADRE sono sintetiche della
               vista e hanno `id` NULL — usarlo come chiave produrrebbe
               duplicati. Si lascia il fallback per indice di PrimeVue. -->
          <DataTable
            :value="righe"
            class="app-datatable app-datatable--inner"
            striped-rows
            size="small"
          >
            <Column field="riga_nr" :header="t('vendite.fatture.col_riga')" style="width: 60px;" />
            <Column field="descrizione" :header="t('vendite.fatture.col_descrizione')">
              <template #body="{ data }">
                <!-- `livello` è il contratto della vista: 0 = riga di primo
                     livello (NORMALE o KIT_PADRE), 1 = componente di kit, che
                     va rientrato sotto il padre. -->
                <span :class="{ 'app-fattura-componente': data.livello === 1 }">
                  <span v-if="data.articolo_codice" class="app-fattura-articolo">
                    {{ data.articolo_codice }}
                  </span>
                  {{ data.descrizione || data.articolo_descrizione || '—' }}
                </span>
              </template>
            </Column>
            <Column field="quantita" :header="t('vendite.fatture.col_qta')" style="width: 80px;">
              <template #body="{ data }">
                <!-- Quantità NULL sui KIT_PADRE (la vista non le somma): '—',
                     mai un finto zero. max 6 decimali = precisione colonna. -->
                {{ formatNumber(data.quantita, { placeholder: '—', minimumFractionDigits: 0, maximumFractionDigits: 6 }) }}
              </template>
            </Column>
            <Column field="uom_codice" :header="t('vendite.fatture.col_uom')" style="width: 70px;" />
            <Column field="prezzo_unitario" :header="t('vendite.fatture.col_prezzo')" style="width: 110px;">
              <template #body="{ data }">
                {{ formatCurrency(data.prezzo_unitario, { placeholder: '—', minimumFractionDigits: 2, maximumFractionDigits: 6 }) }}
              </template>
            </Column>
            <Column field="sconto_percentuale" :header="t('vendite.fatture.col_sconto')" style="width: 80px;">
              <template #body="{ data }">{{ scontoLabel(data) }}</template>
            </Column>
            <Column field="iva_codice" :header="t('vendite.fatture.col_iva')" style="width: 80px;">
              <template #body="{ data }">
                <!-- BB formatIvaLabel: aliquota > 0 → "22%", esente → codice
                     IVA parlante; fallback natura di riga (snapshot). -->
                {{ formatIvaLabel(data, { placeholder: data.iva_natura || '—' }) }}
              </template>
            </Column>
            <Column field="importo_riga" :header="t('vendite.fatture.col_imponibile')" style="width: 110px;">
              <template #body="{ data }">
                {{ formatCurrency(data.importo_riga, { placeholder: '—' }) }}
              </template>
            </Column>
            <template #empty>
              <div class="app-empty-state">
                <i class="pi pi-inbox" /><p>{{ t('vendite.fatture.nessuna_riga') }}</p>
              </div>
            </template>
          </DataTable>

          <!-- Riepilogo IVA: BB condiviso con preventivi/ordini/DDT (titolo,
               label esenti con natura, footer di quadratura, totale documento).
               Lettura pura da fatture_riepiloghi_iva: nessun ricalcolo qui. -->
          <RiepilogoIvaTable :items="riepilogoIva" show-esigibilita show-subtitle />

          <!-- Chiusura del documento: bollo/arrotondamento se ci sono, poi i
               due totali. `totale_doc` e `totale_a_pagare` entrambi perché
               divergono quando ci sono fondi/acconti applicati, e mostrarne uno
               solo lascia l'operatore senza spiegazione. Placeholder '—' sugli
               importi assenti: NULL non è zero, e su un documento fiscale uno
               zero inventato è un'informazione falsa. -->
          <div class="app-doc-totali">
            <div
              v-for="c in campiTotali"
              :key="c.labelKey"
              class="app-doc-totali-riga"
              :class="{ 'app-doc-totali-riga--forte': c.forte }"
            >
              <span class="app-doc-totali-label">{{ t(c.labelKey) }}</span>
              <span class="app-doc-totali-value">
                {{ formatCurrency(c.importo, { placeholder: '—' }) }}
              </span>
            </div>
          </div>
        </template>
      </template>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <!-- Archivio PDF generati + allegati (motore documentale, sorgente
         FATTURA). Niente `allow-allegati` hardcoded: l'append è una capability
         governata dagli stati (`pdf_allow_allegati`), non una decisione del
         drawer — stessa porta del `LottoDrawer`. -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialog"
      :sorgente-code="SORGENTE_CODES.FATTURA"
      :sorgente-id="fatturaId"
      :title="t('vendite.fatture.documenti_titolo', { numero: numeroDisplay })"
    />

    <!-- Note della fattura (BB partizionato). Il readonly di oggetto arriva
         al NoteDrawer via provide/inject (useReadonlyMode sopra). -->
    <FatturaNoteDrawer
      v-model:visible="noteDrawer"
      :fattura-id="fatturaId"
      :righe="righe"
      @saved="onNoteSaved"
    />
  </Drawer>
</template>

<style scoped>
/* Solo decorazione della tabella righe: il layout della scheda (campi
   label/valore, totali di chiusura) vive nelle classi globali `app-doc-*`. */
.app-fattura-articolo {
  color: var(--app-text-muted);
  margin-right: 0.4rem;
}
.app-fattura-componente {
  padding-left: 1.2rem;
}
</style>
