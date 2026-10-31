<script setup>
// Scopo: Tabella riepilogo IVA aggregato per documento (preventivo, fattura,
// ordine). Una riga per gruppo (iva_id, natura, esigibilita, split_payment)
// con imponibile e imposta gia' arrotondati a 2 decimali sull'aggregato per
// aliquota (regola fiscale DPR 633/72 art. 21 + DM 24/12/93). Non ricalcola
// nulla lato FE: i dati arrivano gia' corretti dal BE (vista DB
// `vw_*_riepilogo_iva_dettaglio`).
//
// Riusabile cross-dominio: il chiamante passa la lista `items` con la
// shape standard delle viste riepilogo IVA. Layout compatto, footer con
// totali aggregati. Colonna `arrotondamento` opzionale (diagnostica).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatCurrency, formatNumber } from '../utils/format'
// DataTable grezza: il riepilogo IVA di UN documento (`items` dal chiamante),
// una riga per gruppo d'aliquota con footer dei totali — dettaglio del master,
// non paginato e con le colonne fissate dalla regola fiscale.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()

const props = defineProps({
  // Array di righe riepilogo IVA. Shape attesa per ogni elemento (`id`
  // opzionale: presente sui preventivi, assente sulla vista derivata ordini):
  //   { iva_id, iva_codice, iva_descrizione, iva_aliquota,
  //     natura_id, natura_codice, esigibilita, split_payment,
  //     imponibile, imposta, arrotondamento, totale_riga }
  items: { type: Array, default: () => [] },
  // Mostra colonna arrotondamento (diagnostica). Off di default per UX pulita.
  showArrotondamento: { type: Boolean, default: false },
  // Mostra tooltip didascalico sotto al titolo (riferimento normativo).
  showSubtitle: { type: Boolean, default: false },
})

// Decodifica esigibilita' IVA (character(1) FatturaPA, CHECK
// `chk_fatture_r_iva_esigibilita`). Chiavi i18n LETTERALI e complete: e' la
// forma che `scripts/check_i18n_keys.py` sa verificare — una chiave costruita
// a template sarebbe un punto cieco del guard.
const ESIGIBILITA_LABEL_KEYS = {
  I: 'common.riepilogo_iva_esigibilita_immediata',
  D: 'common.riepilogo_iva_esigibilita_differita',
  S: 'common.riepilogo_iva_esigibilita_split',
}

// Scopo: label esigibilita' — decodifica nota, codice grezzo come fallback
// (un valore fuori vocabolario e' piu' utile visibile che nascosto), '—' se NULL.
function esigibilitaLabel(row) {
  const key = ESIGIBILITA_LABEL_KEYS[row.esigibilita]
  if (key) return t(key)
  return row.esigibilita || '—'
}

// Totali aggregati: somma imponibile + imposta delle righe. Ridondante con la
// testata documento ma utile come check di quadratura nel componente stesso.
const totals = computed(() => {
  let imp = 0
  let iva = 0
  for (const r of props.items) {
    imp += Number(r.imponibile || 0)
    iva += Number(r.imposta || 0)
  }
  return { imponibile: imp, imposta: iva, totale: imp + iva }
})

// Label aliquota: "22%" oppure "Esente" quando aliquota_iva e' 0/NULL e c'e'
// natura (caso fatture); per preventivi natura e' sempre NULL ma mantengo
// comportamento per riusabilita'.
function aliquotaLabel(row) {
  if (row.iva_aliquota != null && Number(row.iva_aliquota) > 0) {
    return `${formatNumber(row.iva_aliquota, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}%`
  }
  return t('common.riepilogo_iva_esente')
}
</script>

<template>
  <div>
    <div class="app-riepilogo-iva__header">
      <h4 class="app-riepilogo-iva__title">{{ t('common.riepilogo_iva_titolo') }}</h4>
      <small v-if="showSubtitle" class="app-riepilogo-iva__subtitle">
        {{ t('common.riepilogo_iva_sottotitolo') }}
      </small>
    </div>

    <!-- Tabella read-only: nessun data-key. Le shape riepilogo IVA non hanno
         tutte un `id` univoco (la vista ordini deriva senza id tecnico; le
         fatture useranno la chiave composita iva+natura+esigibilita+split):
         per una tabella senza selezione/espansione PrimeVue usa l'indice di
         riga, evitando key duplicate quando id e' assente. -->
    <!-- Larghezze: 31+27+27+15 = 100 con la colonna esigibilita' (sempre).
         La colonna diagnostica `arrotondamento` (10%) la sfora di proposito:
         con `table-layout: fixed` il browser riproporziona, ed e' una vista
         di controllo, non di lettura. -->
    <DataTable :value="items" size="small" striped-rows show-gridlines class="app-datatable"
      :pt="{ table: { style: 'table-layout: fixed;' } }">
      <template #empty>
        <span style="color: var(--app-text-muted);">
          {{ t('common.riepilogo_iva_vuoto') }}
        </span>
      </template>

      <Column field="iva_aliquota" :header="t('common.riepilogo_iva_col_aliquota')"
        :footer="t('common.riepilogo_iva_totale')"
        header-style="text-align: left;" body-style="text-align: left;"
        footer-style="text-align: left; font-weight: 600;"
        style="width: 31%;">
        <template #body="{ data }">
          <div style="display: flex; flex-direction: column; gap: 0.1rem;">
            <span>{{ aliquotaLabel(data) }}</span>
            <small v-if="data.iva_descrizione" style="color: var(--app-text-muted);">
              {{ data.iva_descrizione }}
            </small>
            <small v-if="data.natura_codice" style="color: var(--app-text-muted);">
              {{ t('common.riepilogo_iva_natura_label') }}: {{ data.natura_codice }}
            </small>
          </div>
        </template>
      </Column>

      <Column field="imponibile" :header="t('common.riepilogo_iva_col_imponibile')"
        header-style="text-align: right;" body-style="text-align: right;"
        footer-style="text-align: right; font-weight: 600;"
        style="width: 27%;">
        <template #body="{ data }">{{ formatCurrency(data.imponibile) }}</template>
        <template #footer>{{ formatCurrency(totals.imponibile) }}</template>
      </Column>

      <Column field="imposta" :header="t('common.riepilogo_iva_col_imposta')"
        header-style="text-align: right;" body-style="text-align: right;"
        footer-style="text-align: right; font-weight: 600;"
        style="width: 27%;">
        <template #body="{ data }">{{ formatCurrency(data.imposta) }}</template>
        <template #footer>{{ formatCurrency(totals.imposta) }}</template>
      </Column>

      <!-- Esigibilita' IVA decodificata (I/D/S FatturaPA): SEMPRE, su tutti i
           documenti di vendita. Dal 2026-10-01 la coppia esigibilita'/scissione
           di fattura, preventivo, ordine e DDT esce dalla stessa regola DB
           (`script.fn_esigibilita_iva`, R-4 di brief-db-esigibilita-iva-per-
           cassa-emittente): la prop `showEsigibilita` che la accendeva e' stata
           RITIRATA quando tutti e quattro i consumer la passavano uguale.
           NULL = cliente o regime non noto: la cella mostra '—'. -->
      <Column field="esigibilita"
        :header="t('common.riepilogo_iva_col_esigibilita')"
        header-style="text-align: left;" body-style="text-align: left;"
        style="width: 15%;">
        <template #body="{ data }">{{ esigibilitaLabel(data) }}</template>
      </Column>

      <Column v-if="showArrotondamento" field="arrotondamento"
        :header="t('common.riepilogo_iva_col_arrotondamento')"
        header-style="text-align: right;" body-style="text-align: right;"
        style="width: 10%;">
        <template #body="{ data }">
          <span v-tooltip.top="t('common.riepilogo_iva_arrotondamento_tooltip')"
            style="color: var(--app-text-muted); font-size: 0.85em;">
            {{ data.arrotondamento != null ? formatNumber(data.arrotondamento, { minimumFractionDigits: 4, maximumFractionDigits: 6 }) : '—' }}
          </span>
        </template>
      </Column>
    </DataTable>

    <!-- Totale documento (imponibile + IVA): dopo il footer per-aliquota,
         su riga propria. Singolo valore allineato a destra. -->
    <div class="app-riepilogo-iva__totale">
      <span class="app-riepilogo-iva__totale-label">{{ t('common.riepilogo_iva_totale') }}</span>
      <span class="app-riepilogo-iva__totale-value">{{ formatCurrency(totals.totale) }}</span>
    </div>
  </div>
</template>

<style scoped>
.app-riepilogo-iva__header {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 0.4rem;
}

.app-riepilogo-iva__title {
  margin: 0;
  font-size: 0.95rem;
}

.app-riepilogo-iva__subtitle {
  color: var(--app-text-muted);
  font-size: 0.8rem;
}

.app-riepilogo-iva__totale {
  display: flex;
  justify-content: flex-end;
  align-items: baseline;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem 0;
  font-size: 1rem;
}

.app-riepilogo-iva__totale-label {
  color: var(--app-text-muted);
  font-weight: 600;
}

.app-riepilogo-iva__totale-value {
  font-weight: 700;
  font-size: 1.05rem;
}
</style>
