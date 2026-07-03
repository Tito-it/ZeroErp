<script setup>
// Scopo: Dashboard fatturazione — controllo del transito per competenza
//        (brief-design-dashboard-fatturazione §7).
//        ⚠️ VERSIONE MOCK per validazione grafica: i dati arrivano da
//        `vendite/mock/dashboardFatturazione.mock.js`, NESSUNA chiamata BE.
//        Alla Fase 3 il mock viene sostituito da store Pinia + API
//        `/api/v1/vendite/dashboard-fatturazione/` senza toccare il layout.
//        Layout: pannello laterale anno + 12 mesi con semaforo (D-5),
//        card per area (donut € / frazione conteggi, D-2/D-3/D-4),
//        drill-down fermi in pagina (non drawer: confronto card↔dettaglio).
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DonutTransito from '../../core/components/charts/DonutTransito.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, READONLY_DOMAINS } from '../../core/constants'
import { formatCurrency } from '../../core/utils/format'
import { resolveSeverity } from '../../core/utils/severity'
import { AREE, buildMockAnno, listMockFermi } from '../mock/dashboardFatturazione.mock'

const { t, locale } = useI18n()
const notify = useNotify()

// Provider readonly di area: la dashboard e' consultazione pura, ma il
// provider mantiene il pattern standard (ReadonlyBadge nel suffix toolbar).
useReadonlyMode(READONLY_DOMAINS.VENDITE)

// Anno libero (D-5): frecce ◀ ▶, 12 mesi sempre presenti.
const anno = ref(2026)
// Mese selezionato (indice 0-11). Default: maggio, il mese "caldo" del mock.
const meseIdx = ref(4)
// Area selezionata per il drill-down fermi (click su card).
const areaSelezionata = ref(null)

const matrice = computed(() => buildMockAnno(anno.value))
const mesi = computed(() => matrice.value.mesi)
const meseCorrente = computed(() => mesi.value[meseIdx.value])

// Scopo: nome mese localizzato dal locale i18n attivo (niente 12 chiavi i18n).
function nomeMese(idx, forma = 'long') {
  return new Date(anno.value, idx, 1).toLocaleDateString(locale.value, { month: forma })
}

// Scopo: semaforo del mese per il pannello laterale.
//        'ok' = ha dati e tutto transitato; 'fermi' = fermi > 0; 'vuoto' = zero dati.
function statoMese(mese) {
  const nFermi = mese.aree.reduce((acc, a) => acc + a.n_fermi, 0)
  const nDocumenti = mese.aree.reduce((acc, a) => acc + a.n_documenti, 0)
  if (nDocumenti === 0) return { stato: 'vuoto', fermi: 0 }
  if (nFermi > 0) return { stato: 'fermi', fermi: nFermi }
  return { stato: 'ok', fermi: 0 }
}

// Righe card del mese selezionato, decorate con la config area (kind €/n).
const cards = computed(() =>
  AREE.map((cfg) => {
    const dati = meseCorrente.value.aree.find((a) => a.area === cfg.key)
    return { ...cfg, ...dati }
  })
)

// Riepilogo mese: somme delle sole aree in euro (le aree a conteggi non
// hanno valore monetario in v1) + conteggi fermi/abortiti cross-area.
const totaliMese = computed(() => {
  const euro = meseCorrente.value.aree.filter((a) => a.valore_totale !== null)
  const totale = euro.reduce((acc, a) => acc + a.valore_totale, 0)
  const transitato = euro.reduce((acc, a) => acc + a.valore_transitato, 0)
  const fermi = meseCorrente.value.aree.reduce((acc, a) => acc + a.n_fermi, 0)
  const abortiti = meseCorrente.value.aree.reduce((acc, a) => acc + a.n_abortiti, 0)
  return { totale, transitato, fermo: totale - transitato, fermi, abortiti }
})

// Drill-down fermi dell'area selezionata nel mese corrente.
const fermiRows = computed(() => {
  if (!areaSelezionata.value) return []
  return listMockFermi(meseCorrente.value.competenza_mese, areaSelezionata.value)
})

const areaSelezionataLabel = computed(() =>
  areaSelezionata.value ? t(`dashboard_fatturazione.area_${areaSelezionata.value.toLowerCase()}`) : ''
)

function selezionaMese(idx) {
  meseIdx.value = idx
  areaSelezionata.value = null
}

function selezionaArea(areaKey) {
  areaSelezionata.value = areaSelezionata.value === areaKey ? null : areaKey
}

function cambiaAnno(delta) {
  anno.value += delta
  areaSelezionata.value = null
}

// Scopo: passo mese ±1 per lo stepper compatto (piccoli schermi),
//        scavalcando l'anno ai bordi (dic ▶ = gennaio anno successivo).
function stepMese(delta) {
  let idx = meseIdx.value + delta
  if (idx > 11) {
    anno.value += 1
    idx = 0
  } else if (idx < 0) {
    anno.value -= 1
    idx = 11
  }
  meseIdx.value = idx
  areaSelezionata.value = null
}

// Severity Tag per gli stati documento mostrati nel drill-down (mock).
const STATO_FERMO_SEVERITY = {
  DRAFT: 'secondary',
  EMESSO: 'info',
  ACCETTATO: 'info',
  ACCETTATA: 'info',
  CONFERMATO: 'info',
  ATTIVO: 'success',
  APERTA: 'info',
}

// Azioni riga drill-down: "apri documento" — nel mock notifica soltanto
// (con dati reali navighera' alla lista area con ?search=<codice>).
function buildRowActions() {
  return [
    {
      key: 'apri',
      label: t('dashboard_fatturazione.apri_documento'),
      icon: MANAGE_ICONS.LIST,
      command: () => notify.warn(t('dashboard_fatturazione.mock_azione')),
    },
  ]
}

// Toolbar standard: solo ricarica (nel mock notifica il contesto di esempio).
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: () => notify.warn(t('dashboard_fatturazione.mock_azione')),
  },
])
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('dashboard_fatturazione.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('dashboard_fatturazione.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <!-- Banner mock: la pagina mostra dati di esempio, nessuna chiamata BE. -->
    <Message severity="warn" :closable="false" size="small">
      {{ t('dashboard_fatturazione.mock_banner') }}
    </Message>

    <div class="app-dash-layout">
      <!-- Pannello laterale: anno libero + 12 mesi con semaforo (D-5). -->
      <aside class="app-dash-mesi">
        <div class="app-dash-anno">
          <Button
            icon="pi pi-chevron-left"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.anno_precedente')"
            v-tooltip.bottom="t('dashboard_fatturazione.anno_precedente')"
            @click="cambiaAnno(-1)"
          />
          <span>{{ anno }}</span>
          <Button
            icon="pi pi-chevron-right"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.anno_successivo')"
            v-tooltip.bottom="t('dashboard_fatturazione.anno_successivo')"
            @click="cambiaAnno(1)"
          />
        </div>
        <button
          v-for="(mese, idx) in mesi"
          :key="mese.competenza_mese"
          type="button"
          class="app-dash-mese-btn"
          :class="{ 'is-active': idx === meseIdx }"
          @click="selezionaMese(idx)"
        >
          <span class="app-dash-mese-nome">{{ nomeMese(idx) }}</span>
          <template v-if="statoMese(mese).stato === 'ok'">
            <i class="pi pi-check app-dash-mese-ok" v-tooltip.right="t('dashboard_fatturazione.mese_ok')" />
          </template>
          <template v-else-if="statoMese(mese).stato === 'fermi'">
            <span class="app-dash-mese-fermi" v-tooltip.right="t('dashboard_fatturazione.mese_fermi', { n: statoMese(mese).fermi })">
              <i class="pi pi-exclamation-triangle" /> {{ statoMese(mese).fermi }}
            </span>
          </template>
          <template v-else>
            <i class="pi pi-minus app-dash-mese-vuoto" v-tooltip.right="t('dashboard_fatturazione.mese_vuoto')" />
          </template>
        </button>
      </aside>

      <!-- Colonna principale: competenza + card aree + totali + fermi. -->
      <div class="app-dash-main">
        <!-- Stepper compatto anno/mese: visibile SOLO su piccoli schermi
             (CSS-first, sostituisce il pannello 12 mesi). -->
        <div class="app-dash-stepper">
          <Button
            icon="pi pi-chevron-left"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.mese_precedente')"
            @click="stepMese(-1)"
          />
          <span class="app-dash-stepper-label">
            {{ nomeMese(meseIdx) }} {{ anno }}
            <template v-if="statoMese(meseCorrente).stato === 'ok'">
              <i class="pi pi-check app-dash-mese-ok" />
            </template>
            <template v-else-if="statoMese(meseCorrente).stato === 'fermi'">
              <span class="app-dash-mese-fermi">
                <i class="pi pi-exclamation-triangle" /> {{ statoMese(meseCorrente).fermi }}
              </span>
            </template>
            <template v-else>
              <i class="pi pi-minus app-dash-mese-vuoto" />
            </template>
          </span>
          <Button
            icon="pi pi-chevron-right"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.mese_successivo')"
            @click="stepMese(1)"
          />
        </div>

        <div class="app-dash-header">
          <h3 style="margin: 0;">
            {{ t('dashboard_fatturazione.competenza_titolo', { mese: nomeMese(meseIdx), anno }) }}
          </h3>
        </div>

        <div class="app-dash-cards">
          <div
            v-for="card in cards"
            :key="card.key"
            class="app-dash-card"
            :class="{ 'is-selected': areaSelezionata === card.key }"
            role="button"
            tabindex="0"
            @click="selezionaArea(card.key)"
            @keydown.enter="selezionaArea(card.key)"
          >
            <span class="app-dash-card-title">
              {{ t(`dashboard_fatturazione.area_${card.key.toLowerCase()}`) }}
            </span>

            <!-- Aree in euro: donut transitato vs fermo (D-4: imponibile). -->
            <DonutTransito
              v-if="card.kind === 'euro'"
              :transitato="card.valore_transitato"
              :fermo="card.valore_totale - card.valore_transitato"
              format="currency"
              :label-transitato="t('dashboard_fatturazione.transitato')"
              :label-fermo="t('dashboard_fatturazione.fermo')"
            />

            <!-- Aree a conteggi (D-2/D-3): frazione n/n + dettaglio. -->
            <template v-else>
              <div class="app-dash-frazione">
                {{ card.n_documenti > 0 ? `${card.n_transitati}/${card.n_documenti}` : '—' }}
              </div>
              <div class="app-donut-transito-legend">
                <div class="app-donut-transito-legend-row">
                  <span class="app-donut-transito-label">{{ t('dashboard_fatturazione.transitati_n') }}</span>
                  <span class="app-donut-transito-value">{{ card.n_transitati }}</span>
                </div>
                <div class="app-donut-transito-legend-row">
                  <span class="app-donut-transito-label">{{ t('dashboard_fatturazione.fermi_n') }}</span>
                  <span class="app-donut-transito-value">{{ card.n_fermi }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>

        <div class="app-dash-totali">
          <span>
            {{ t('dashboard_fatturazione.totale_mese') }}
            <strong>{{ formatCurrency(totaliMese.totale) }}</strong>
          </span>
          <span>
            {{ t('dashboard_fatturazione.transitato_mese') }}
            <strong>{{ formatCurrency(totaliMese.transitato) }}</strong>
          </span>
          <span>
            {{ t('dashboard_fatturazione.fermo_mese') }}
            <strong>{{ formatCurrency(totaliMese.fermo) }}</strong>
          </span>
          <span v-if="totaliMese.abortiti > 0">
            {{ t('dashboard_fatturazione.abortiti_mese') }}
            <strong>{{ totaliMese.abortiti }}</strong>
          </span>
        </div>

        <!-- Drill-down fermi in pagina (click su card, §7). -->
        <div class="app-dash-fermi">
          <template v-if="areaSelezionata">
            <h4 class="app-dash-fermi-title">
              {{ t('dashboard_fatturazione.fermi_titolo', { area: areaSelezionataLabel }) }}
            </h4>
            <DataTable
              v-if="fermiRows.length > 0"
              :value="fermiRows"
              class="app-datatable app-datatable--inner"
              striped-rows
              data-key="codice"
            >
              <Column field="codice" :header="t('dashboard_fatturazione.col_codice')" style="width: 130px;" />
              <Column field="cliente" :header="t('dashboard_fatturazione.col_cliente')" />
              <Column field="valore" :header="t('dashboard_fatturazione.col_valore')" style="width: 120px;">
                <template #body="{ data }">
                  {{ data.valore !== null ? formatCurrency(data.valore) : '—' }}
                </template>
              </Column>
              <Column field="motivo_fermo" :header="t('dashboard_fatturazione.col_motivo')">
                <template #body="{ data }">
                  {{ t(`dashboard_fatturazione.motivo_fermo.${data.motivo_fermo}`) }}
                </template>
              </Column>
              <Column field="stato_codice" :header="t('dashboard_fatturazione.col_stato')" style="width: 130px;">
                <template #body="{ data }">
                  <Tag :value="data.stato_codice" :severity="resolveSeverity(STATO_FERMO_SEVERITY, data.stato_codice)" />
                </template>
              </Column>
              <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
                <template #body="{ data }">
                  <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
                </template>
              </Column>
            </DataTable>
            <div v-else class="app-empty-state">
              <i class="pi pi-check-circle" />
              <p>{{ t('dashboard_fatturazione.nessun_fermo') }}</p>
            </div>
          </template>
          <div v-else class="app-empty-state">
            <i class="pi pi-chart-pie" />
            <p>{{ t('dashboard_fatturazione.fermi_hint') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
