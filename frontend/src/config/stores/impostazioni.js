// Store Pinia della lista IMPOSTAZIONI (`config.parametri_impostazioni`, lista
// 108): i parametri coi valori a ogni livello della cascata, e gli override.
//
// ⭐ Dal 2026-10-31 e' `createListaStore` (brief-db-liste-datatable-grezze-
//    secondo-giro riga 2): pagina, ricerca e ordinamento li fa il backend. Prima
//    leggeva la lista intera e la filtrava nel browser (`filteredParameters`),
//    sotto una `DataTable` grezza; e non era `userScoped`, cioe' gli override
//    personali restavano in memoria al logout.
import { createListaStore } from '../../core/stores/createListaStore'
import { fetchParameterSettings } from '../../core/apiCore'
import { useParameterSettings } from '../../core/composables/useParameterSettings'

export const useImpostazioniStore = createListaStore('config-impostazioni', {
  fetchPage: fetchParameterSettings,
  // Parte piena: e' il catalogo dei parametri, non una ricerca.
  startsEmpty: false,
  orderBy: 'code',
  extend: () => {
    const { saveOverride, removeOverride } = useParameterSettings()
    return { saveOverride, removeOverride }
  },
})
