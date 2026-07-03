// Scopo: DATI DI ESEMPIO per la validazione grafica della dashboard
//        fatturazione (brief-design-dashboard-fatturazione §7).
//        ⚠️ MOCK TEMPORANEO — nessuna chiamata al backend. Alla Fase 2/3
//        questo modulo viene sostituito da store Pinia + API
//        `/api/v1/vendite/dashboard-fatturazione/`. La forma dei dati
//        rispecchia il contratto API del brief (§6) per rendere lo swap
//        mock→API un cambio di sola sorgente.

// Aree del funnel nell'ordine delle card (§7). kind: 'euro' = donut con
// importi (misura = imponibile, D-4), 'count' = frazione n/n (D-2/D-3).
export const AREE = Object.freeze([
  { key: 'PREVENTIVI', kind: 'euro' },
  { key: 'ORDINI', kind: 'euro' },
  { key: 'OFFERTE', kind: 'count' },
  { key: 'CONTRATTI', kind: 'count' },
  { key: 'COMMESSE', kind: 'euro' },
])

// Scopo: riga area a zero (mese senza dati) nel formato dell'aggregata.
function areaVuota(area) {
  return {
    area,
    valore_totale: 0,
    valore_transitato: 0,
    n_documenti: 0,
    n_transitati: 0,
    n_fermi: 0,
    n_abortiti: 0,
  }
}

// Scopo: mese interamente transitato (semaforo ✓) con valori pseudo-variati
// dal seed, per dare movimento realistico ai mesi "a posto".
function meseCompleto(seed) {
  const v = (base) => base + (seed % 5) * 137
  return [
    { area: 'PREVENTIVI', valore_totale: v(14200), valore_transitato: v(14200), n_documenti: 8 + (seed % 3), n_transitati: 8 + (seed % 3), n_fermi: 0, n_abortiti: seed % 2 },
    { area: 'ORDINI', valore_totale: v(10100), valore_transitato: v(10100), n_documenti: 5 + (seed % 2), n_transitati: 5 + (seed % 2), n_fermi: 0, n_abortiti: 0 },
    { area: 'OFFERTE', valore_totale: null, valore_transitato: null, n_documenti: 11 + (seed % 4), n_transitati: 11 + (seed % 4), n_fermi: 0, n_abortiti: 1 },
    { area: 'CONTRATTI', valore_totale: null, valore_transitato: null, n_documenti: 38 + (seed % 3), n_transitati: 38 + (seed % 3), n_fermi: 0, n_abortiti: 0 },
    { area: 'COMMESSE', valore_totale: v(12800), valore_transitato: v(12800), n_documenti: 21 + (seed % 5), n_transitati: 21 + (seed % 5), n_fermi: 0, n_abortiti: 0 },
  ]
}

// Marzo 2026 — 3 fermi (1 preventivo + 2 canoni contratto non generati).
const MARZO_2026 = [
  { area: 'PREVENTIVI', valore_totale: 15200, valore_transitato: 13100, n_documenti: 9, n_transitati: 8, n_fermi: 1, n_abortiti: 0 },
  { area: 'ORDINI', valore_totale: 8400, valore_transitato: 8400, n_documenti: 5, n_transitati: 5, n_fermi: 0, n_abortiti: 0 },
  { area: 'OFFERTE', valore_totale: null, valore_transitato: null, n_documenti: 10, n_transitati: 10, n_fermi: 0, n_abortiti: 0 },
  { area: 'CONTRATTI', valore_totale: null, valore_transitato: null, n_documenti: 41, n_transitati: 39, n_fermi: 2, n_abortiti: 0 },
  { area: 'COMMESSE', valore_totale: 13600, valore_transitato: 13600, n_documenti: 23, n_transitati: 23, n_fermi: 0, n_abortiti: 0 },
]

// Maggio 2026 — il mese "caldo" del mock: 7 fermi distribuiti su tutte le aree.
const MAGGIO_2026 = [
  { area: 'PREVENTIVI', valore_totale: 12400, valore_transitato: 10150, n_documenti: 9, n_transitati: 7, n_fermi: 2, n_abortiti: 1 },
  { area: 'ORDINI', valore_totale: 9800, valore_transitato: 9310, n_documenti: 6, n_transitati: 5, n_fermi: 1, n_abortiti: 0 },
  { area: 'OFFERTE', valore_totale: null, valore_transitato: null, n_documenti: 15, n_transitati: 14, n_fermi: 1, n_abortiti: 1 },
  { area: 'CONTRATTI', valore_totale: null, valore_transitato: null, n_documenti: 42, n_transitati: 40, n_fermi: 2, n_abortiti: 0 },
  { area: 'COMMESSE', valore_totale: 11300, valore_transitato: 6780, n_documenti: 24, n_transitati: 15, n_fermi: 1, n_abortiti: 0 },
]

// Scopo: matrice annuale nel formato del contratto API §6 (12 mesi SEMPRE
// presenti, D-5). 2026 = anno ricco (mesi ok, mesi con fermi, mesi vuoti);
// 2025 = anno chiuso tutto ✓; altri anni = vuoti.
export function buildMockAnno(anno) {
  const mesi = []
  for (let m = 0; m < 12; m++) {
    const competenza = `${anno}-${String(m + 1).padStart(2, '0')}-01`
    let aree
    if (anno === 2026) {
      if (m <= 1 || m === 3) aree = meseCompleto(m + 1) // gen, feb, apr ✓
      else if (m === 2) aree = MARZO_2026 // mar ⚠ 3
      else if (m === 4) aree = MAGGIO_2026 // mag ⚠ 7
      else aree = AREE.map((a) => areaVuota(a.key)) // giu..dic vuoti
    } else if (anno === 2025) {
      aree = meseCompleto(m + 7)
    } else {
      aree = AREE.map((a) => areaVuota(a.key))
    }
    mesi.push({ competenza_mese: competenza, aree })
  }
  return { anno, mesi }
}

// Drill-down fermi per (competenza_mese, area) — formato dell'endpoint
// `/dashboard-fatturazione/fermi/` (§6): documento, valore, motivo, stato.
const FERMI = {
  '2026-03-01': {
    PREVENTIVI: [
      { codice: 'PRV0000098', cliente: 'Studio Tecnico Ferri', valore: 2100, motivo_fermo: 'PUSH_PARZIALE', stato_codice: 'ACCETTATO' },
    ],
    CONTRATTI: [
      { codice: 'CNT0000007', cliente: 'Immobiliare Sole SRL', valore: null, motivo_fermo: 'CANONE_NON_GENERATO', stato_codice: 'ATTIVO' },
      { codice: 'CNT0000019', cliente: 'Blu Servizi SNC', valore: null, motivo_fermo: 'CANONE_NON_GENERATO', stato_codice: 'ATTIVO' },
    ],
  },
  '2026-05-01': {
    PREVENTIVI: [
      { codice: 'PRV0000123', cliente: 'Rossi Impianti SRL', valore: 1450, motivo_fermo: 'RIGA_RESIDUA', stato_codice: 'ACCETTATO' },
      { codice: 'PRV0000131', cliente: 'Condominio Aurora', valore: 800, motivo_fermo: 'IN_ATTESA_ACCETTAZIONE', stato_codice: 'EMESSO' },
    ],
    ORDINI: [
      { codice: 'ORD0000045', cliente: 'Verdi Costruzioni SpA', valore: 490, motivo_fermo: 'ORDINE_DRAFT', stato_codice: 'DRAFT' },
    ],
    OFFERTE: [
      { codice: 'OFF0000012', cliente: 'Bianchi Energia SRL', valore: null, motivo_fermo: 'SENZA_FIGLIO', stato_codice: 'ACCETTATA' },
    ],
    CONTRATTI: [
      { codice: 'CNT0000007', cliente: 'Immobiliare Sole SRL', valore: null, motivo_fermo: 'CANONE_NON_GENERATO', stato_codice: 'ATTIVO' },
      { codice: 'CNT0000021', cliente: 'Gamma Ristorazione SRL', valore: null, motivo_fermo: 'CANONE_NON_GENERATO', stato_codice: 'ATTIVO' },
    ],
    COMMESSE: [
      { codice: 'CMS0000032', cliente: 'Rossi Impianti SRL', valore: 4520, motivo_fermo: 'NON_EMESSA', stato_codice: 'APERTA' },
    ],
  },
}

// Scopo: lista fermi mock per il pannello drill-down.
export function listMockFermi(competenzaMese, area) {
  return FERMI[competenzaMese]?.[area] ?? []
}
