// Registry "chiave documento -> drawer di dettaglio": componente async, nome
// della prop id, e se il drawer accetta `mode` (ResoDrawer, CommessaDrawer e
// CommessaGestioneDrawer NON hanno `mode`).
//
// Promosso a BB cross-dominio 2026-07-25 (era `_shared/lineage/lineageDrawers`,
// regola del 2 — 2o consumatore): oltre alle tappe del pannello "Passaggi" lo
// usano ora le liste drill-down dei cruscotti (Situazione aperta, Backlog) per
// aprire il documento IN DRAWER invece di navigare alla lista d'area. Il nome
// `lineage*` era diventato una bugia: qui non c'e' nulla di genealogico.
//
// Le chiavi sono i codici sorgente (`config.sorgenti.codice_interno`) piu' le
// chiavi NON-sorgente dei drawer che non hanno un tipo sorgente proprio
// (COMMESSA_GESTIONE). Solo FATTURA resta esclusa: nodo terminale senza drawer
// proprio (Q4 brief lineage).
//
// I drawer sono caricati via import dinamico (`load`) di proposito: ogni drawer
// documento importa staticamente `DocumentoCollegamentiBar`, che monta l'host —
// quindi un import STATICO dei drawer qui chiuderebbe il ciclo
// drawer → barra → host → registry → drawer. L'import dinamico lo spezza e
// code-splitta i drawer.
//
// Ogni entry espone `load`, il loader grezzo del chunk. L'host lo ATTENDE,
// poi rende il componente RISOLTO (non un `defineAsyncComponent`): così il
// drawer monta in modo sincrono con `visible=false` e osserva poi la
// transizione false->true che innesca `@after-show` e il watch di caricamento
// dettaglio. Con `defineAsyncComponent` invece il componente reale montava un
// microtask DOPO il mount del placeholder — cioe' dopo che `visible` era gia'
// true — e il drawer si apriva con i soli default (bug "primo click apre
// vuoto, riapertura ok": il chunk in cache rendeva sincrona solo la 2a volta).

function drawer(load, idProp, hasMode) {
  return { load, idProp, hasMode }
}

// Chiavi del registry — fonte unica per i caller (mai literal sparsi).
// I primi 7 sono codici sorgente veri (`config.sorgenti.codice_interno`, gli
// stessi che il BE mette in from_doc_tipo/to_doc_tipo del lineage);
// COMMESSA_GESTIONE e' una chiave NON-sorgente, vedi sotto.
export const DOCUMENTO_DRAWER_TIPI = Object.freeze({
  PREVENTIVO: 'PREVENTIVO',
  OFFERTA_COMMERCIALE: 'OFFERTA_COMMERCIALE',
  ORDINE_VENDITA: 'ORDINE_VENDITA',
  CONTRATTO: 'CONTRATTO',
  DDT_VENDITA: 'DDT_VENDITA',
  RESO_VENDITA: 'RESO_VENDITA',
  COMMESSA: 'COMMESSA',
  COMMESSA_GESTIONE: 'COMMESSA_GESTIONE',
})

// Chiavi NON-sorgente: drawer raggiungibili per id ma senza un
// `config.sorgenti.codice_interno` corrispondente. Tenute a parte perche' i
// consumatori che partono da un TIPO SORGENTE (lineage) non devono vederle.
const CHIAVI_NON_SORGENTE = [DOCUMENTO_DRAWER_TIPI.COMMESSA_GESTIONE]

export const DOCUMENTO_DRAWERS = {
  [DOCUMENTO_DRAWER_TIPI.PREVENTIVO]:
    drawer(() => import('../../preventivi/components/PreventiviDrawer.vue'), 'preventivoId', true),
  [DOCUMENTO_DRAWER_TIPI.OFFERTA_COMMERCIALE]:
    drawer(() => import('../../offerte/components/OffertaDrawer.vue'), 'offertaId', true),
  [DOCUMENTO_DRAWER_TIPI.ORDINE_VENDITA]:
    drawer(() => import('../../ordini/components/OrdiniDrawer.vue'), 'ordineId', true),
  [DOCUMENTO_DRAWER_TIPI.CONTRATTO]:
    drawer(() => import('../../components/ContrattoDrawer.vue'), 'contrattoId', true),
  [DOCUMENTO_DRAWER_TIPI.DDT_VENDITA]:
    drawer(() => import('../../ddt/components/DdtDrawer.vue'), 'ddtId', true),
  [DOCUMENTO_DRAWER_TIPI.RESO_VENDITA]:
    drawer(() => import('../../resi/components/ResoDrawer.vue'), 'resoId', false),
  // Fase C: la commessa non ha lista/CRUD, ma il suo nodo lineage è
  // consultabile in un drawer leggero (genealogia inversa). Read-only:
  // nessun `mode`.
  [DOCUMENTO_DRAWER_TIPI.COMMESSA]:
    drawer(() => import('../lineage/CommessaDrawer.vue'), 'commessaId', false),
  // Drawer di GESTIONE commessa (lo stesso montato da DashboardCompetenzaView):
  // apre le righe COMMESSE del drill-down Backlog, che prima non avevano alcuna
  // azione (l'area non ha una view lista). Distinto dal drawer leggero
  // `COMMESSA` dei passaggi: qui servono le azioni di governo.
  [DOCUMENTO_DRAWER_TIPI.COMMESSA_GESTIONE]:
    drawer(() => import('../../components/CommessaGestioneDrawer.vue'), 'commessaId', false),
}

// Tipi SORGENTE con drawer di dettaglio: il registry meno le chiavi
// non-sorgente. Consumato dalle tappe dei "Passaggi", che partono da un
// `config.sorgenti.codice_interno`.
export const SORGENTE_DRAWER_TIPI = Object.keys(DOCUMENTO_DRAWERS).filter(
  (k) => !CHIAVI_NON_SORGENTE.includes(k),
)

// Scopo: una tappa del grafo lineage e' apribile se ha un id di dominio
//        risolto dal BE e un tipo sorgente con drawer. Regola UNICA (era
//        ripetuta in 3 file, 2026-07-25): la usa chi decide se rendere il
//        codice come link e chi apre il drawer. `docId` null = documento fuori
//        scope RLS -> tappa consultiva; FATTURA = nodo terminale senza drawer.
export function isTappaApribile(row) {
  return row?.docId != null && SORGENTE_DRAWER_TIPI.includes(row.tipoCodice)
}
