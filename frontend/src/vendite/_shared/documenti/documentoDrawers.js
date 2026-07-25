// Mappa tipo sorgente (config.sorgenti.codice_interno) -> drawer di dettaglio:
// componente async, nome della prop id, e se il drawer accetta `mode`
// (ResoDrawer e CommessaDrawer NON hanno `mode`). 7 tipi: i 6 documenti +
// COMMESSA (drawer leggero, Fase C genealogia inversa). Solo FATTURA resta
// esclusa: nodo terminale senza drawer proprio (Q4 brief lineage).
//
// I drawer sono caricati via import dinamico (`load`) di proposito: i drawer
// importano staticamente LineagePassaggiPanel (che monta l'host) — un import
// STATICO dei drawer creerebbe un ciclo. L'import dinamico spezza il ciclo
// statico e code-splitta i drawer.
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

export const LINEAGE_DRAWERS = {
  PREVENTIVO: drawer(() => import('../../preventivi/components/PreventiviDrawer.vue'), 'preventivoId', true),
  OFFERTA_COMMERCIALE: drawer(() => import('../../offerte/components/OffertaDrawer.vue'), 'offertaId', true),
  ORDINE_VENDITA: drawer(() => import('../../ordini/components/OrdiniDrawer.vue'), 'ordineId', true),
  CONTRATTO: drawer(() => import('../../components/ContrattoDrawer.vue'), 'contrattoId', true),
  DDT_VENDITA: drawer(() => import('../../ddt/components/DdtDrawer.vue'), 'ddtId', true),
  RESO_VENDITA: drawer(() => import('../../resi/components/ResoDrawer.vue'), 'resoId', false),
  // Fase C: la commessa non ha lista/CRUD, ma il suo nodo lineage è
  // consultabile in un drawer leggero (genealogia inversa). Read-only:
  // nessun `mode`.
  COMMESSA: drawer(() => import('./CommessaDrawer.vue'), 'commessaId', false),
}

// Tipi con drawer di dettaglio apribile dalle tappe del pannello "Passaggi".
export const LINEAGE_DRAWER_TIPI = Object.keys(LINEAGE_DRAWERS)
