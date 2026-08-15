// Store Pinia per la gestione unita' di misura.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listUnitaMisura, getUnitaMisura, createUnitaMisura, updateUnitaMisura, disattivaUnitaMisura } from '../api/catalogo'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { TAB_ENTITIES } from '../../core/constants'
import { CATALOGO_LOOKUP_RELS } from '../constants'

export const useUnitaMisuraStore = defineStore('catalogo-unita-misura', () => {
  const { emitDataChanged } = useTabEvents()


  const filters = ref({
    search: '',
    attivo: true,
    limit: 25,
    offset: 0,
    order_by: 'codice',
    order_dir: 'asc'
  })

  // Lista via BB condiviso (migrazione 2026-08-10): porta la guardia di versione
  // anti-race che qui mancava. `ricercaCorta: 'svuota'` conserva ESATTAMENTE l'UX
  // di prima — parte piena, ma una ricerca sotto i 3 caratteri svuota invece di
  // lasciare a video righe che non c'entrano con quello che si sta scrivendo.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    ricercaCorta: 'svuota',
    buildParams: (f, searchTerm) => {
      const params = {}
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo
      return params
    },
    fetchPage: listUnitaMisura,
  })

  async function fetchDetail(id) {
    const res = await getUnitaMisura(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createUnitaMisura(payload)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UNITA_MISURA)
    emitDataChanged(TAB_ENTITIES.UNITA_MISURA, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateUnitaMisura(id, payload)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UNITA_MISURA)
    emitDataChanged(TAB_ENTITIES.UNITA_MISURA, id)
    return res.data.data
  }

  async function disattiva(id) {
    const res = await disattivaUnitaMisura(id)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UNITA_MISURA)
    emitDataChanged(TAB_ENTITIES.UNITA_MISURA, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update, disattiva
  }
})
