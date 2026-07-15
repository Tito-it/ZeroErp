// Mappa tipo sorgente (config.sorgenti.codice_interno) -> drawer di dettaglio:
// componente async, nome della prop id, e se il drawer accetta `mode`
// (ResoDrawer e CommessaDrawer NON hanno `mode`). 7 tipi: i 6 documenti +
// COMMESSA (drawer leggero, Fase C genealogia inversa). Solo FATTURA resta
// esclusa: nodo terminale senza drawer proprio (Q4 brief lineage).
//
// I drawer sono caricati via `defineAsyncComponent` (import dinamico) di
// proposito: i drawer importano staticamente LineagePassaggiPanel (che monta
// l'host) — un import STATICO dei drawer creerebbe un ciclo. L'import
// dinamico spezza il ciclo statico e code-splitta i drawer.
import { defineAsyncComponent } from 'vue'

export const LINEAGE_DRAWERS = {
  PREVENTIVO: {
    comp: defineAsyncComponent(() => import('../../preventivi/components/PreventiviDrawer.vue')),
    idProp: 'preventivoId',
    hasMode: true,
  },
  OFFERTA_COMMERCIALE: {
    comp: defineAsyncComponent(() => import('../../offerte/components/OffertaDrawer.vue')),
    idProp: 'offertaId',
    hasMode: true,
  },
  ORDINE_VENDITA: {
    comp: defineAsyncComponent(() => import('../../ordini/components/OrdiniDrawer.vue')),
    idProp: 'ordineId',
    hasMode: true,
  },
  CONTRATTO: {
    comp: defineAsyncComponent(() => import('../../components/ContrattoDrawer.vue')),
    idProp: 'contrattoId',
    hasMode: true,
  },
  DDT_VENDITA: {
    comp: defineAsyncComponent(() => import('../../ddt/components/DdtDrawer.vue')),
    idProp: 'ddtId',
    hasMode: true,
  },
  RESO_VENDITA: {
    comp: defineAsyncComponent(() => import('../../resi/components/ResoDrawer.vue')),
    idProp: 'resoId',
    hasMode: false,
  },
  // Fase C: la commessa non ha lista/CRUD, ma il suo nodo lineage è
  // consultabile in un drawer leggero (genealogia inversa). Read-only:
  // nessun `mode`.
  COMMESSA: {
    comp: defineAsyncComponent(() => import('./CommessaDrawer.vue')),
    idProp: 'commessaId',
    hasMode: false,
  },
}

// Tipi con drawer di dettaglio apribile dalle tappe del pannello "Passaggi".
export const LINEAGE_DRAWER_TIPI = Object.keys(LINEAGE_DRAWERS)
