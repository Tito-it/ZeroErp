// Store Pinia per la gestione tipologie UoM.
//
// ⭐ Dal 2026-09-18 e' `createCrudStore` e basta: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams`, e con il CRUD
//    riscritto per UNA riga — l'invalidazione della cache del lookup a ogni
//    write. Quella riga oggi e' `afterWrite`, l'aggancio post-write della
//    factory, nato qui e nella sorella `unitaMisura` (regola del 2).
import { createCrudStore } from '../../core/stores/createCrudStore'
import { listUomTipi, getUomTipo, createUomTipo, updateUomTipo } from '../api/catalogo'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { TAB_ENTITIES } from '../../core/constants'
import { CATALOGO_LOOKUP_RELS } from '../constants'

export const useUomTipiStore = createCrudStore('catalogo-uom-tipi', {
  api: {
    list: listUomTipi,
    detail: getUomTipo,
    create: createUomTipo,
    update: updateUomTipo,
  },
  tabEntity: TAB_ENTITIES.UOM_TIPI,
  // Ogni scrittura rende stantia la cache del lookup condiviso: si invalida
  // PRIMA che le altre tab ricevano l'evento.
  afterWrite: () => invalidateLookup(CATALOGO_LOOKUP_RELS.UOM_TIPI),
  // Parte piena, ma una ricerca sotto i 3 caratteri SVUOTA invece di lasciare
  // a video righe che non c'entrano con quello che si sta scrivendo: e' l'UX
  // che questa lista ha sempre avuto (`ricercaCorta`, migrazione 2026-08-10).
  startsEmpty: false,
  ricercaCorta: 'svuota',
  filterDefaults: { attivo: true },
  orderBy: 'descrizione',
})
