// Store Pinia per la gestione unita' di misura.
//
// ⭐ Dal 2026-09-18 e' `createCrudStore` e basta: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams`, e con il CRUD
//    riscritto per UNA riga — ogni write deve anche INVALIDARE la cache del
//    lookup (`LookupSelect` con `rel=catalogo.unita_misura` la tiene in
//    memoria). Quella riga oggi e' `afterWrite`, l'aggancio post-write della
//    factory, nato qui e nella sorella `uomTipi` (regola del 2).
import { createCrudStore } from '../../core/stores/createCrudStore'
import { listUnitaMisura, getUnitaMisura, createUnitaMisura, updateUnitaMisura, disattivaUnitaMisura } from '../api/catalogo'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { TAB_ENTITIES } from '../../core/constants'
import { CATALOGO_LOOKUP_RELS } from '../constants'

export const useUnitaMisuraStore = createCrudStore('catalogo-unita-misura', {
  api: {
    list: listUnitaMisura,
    detail: getUnitaMisura,
    create: createUnitaMisura,
    update: updateUnitaMisura,
  },
  tabEntity: TAB_ENTITIES.UNITA_MISURA,
  extraActions: { disattiva: disattivaUnitaMisura },
  // Ogni scrittura — create, update, disattiva — rende stantia la cache del
  // lookup condiviso: si invalida PRIMA che le altre tab ricevano l'evento.
  afterWrite: () => invalidateLookup(CATALOGO_LOOKUP_RELS.UNITA_MISURA),
  // Parte piena, ma una ricerca sotto i 3 caratteri SVUOTA invece di lasciare
  // a video righe che non c'entrano con quello che si sta scrivendo: e' l'UX
  // che questa lista ha sempre avuto (`ricercaCorta`, migrazione 2026-08-10).
  startsEmpty: false,
  ricercaCorta: 'svuota',
  filterDefaults: { attivo: true },
  orderBy: 'codice',
})
