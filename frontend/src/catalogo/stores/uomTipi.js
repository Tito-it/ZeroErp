// Store Pinia per la gestione tipologie UoM.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listUomTipi, getUomTipo, createUomTipo, updateUomTipo } from '../api/catalogo'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { TAB_ENTITIES } from '../../core/constants'
import { CATALOGO_LOOKUP_RELS } from '../constants'

export const useUomTipiStore = defineStore('catalogo-uom-tipi', () => {
  const { emitDataChanged } = useTabEvents()


  const filters = ref({
    search: '',
    attivo: true,
    limit: 25,
    offset: 0,
    order_by: 'descrizione',
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
      const params = {
        limit: f.limit,
        offset: f.offset,
      }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo
      return params
    },
    fetchPage: listUomTipi,
  })

  async function fetchDetail(id) {
    const res = await getUomTipo(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createUomTipo(payload)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UOM_TIPI)
    emitDataChanged(TAB_ENTITIES.UOM_TIPI, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateUomTipo(id, payload)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UOM_TIPI)
    emitDataChanged(TAB_ENTITIES.UOM_TIPI, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
