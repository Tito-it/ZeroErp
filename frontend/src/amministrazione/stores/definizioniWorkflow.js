// Store Pinia della lista EDIZIONI DI WORKFLOW (`pratiche.definizioni_workflow`,
// lista 107). Le azioni fork/nuova-versione/pubblica le chiama la vista.
//
// ⭐ Dal 2026-10-31 e' `createListaStore` (brief-db-liste-datatable-grezze-
//    secondo-giro riga 1): era uno store scritto a mano che leggeva la
//    collezione intera, senza pagina ne' ricerca, sotto una `DataTable` grezza.
//    ⛔ Ritirato con lui il filtro `emittente_fiscale_id`, che nessuna casella
//    impostava: la lista e' `multi_emittente`, la riga dice di chi e'.
// userScoped (default della factory): dati e filtri dell'utente → reset al logout.

import { createListaStore } from '../../core/stores/createListaStore'
import { listDefinizioniWorkflow } from '../api/definizioniWorkflow'

export const useDefinizioniWorkflowStore = createListaStore('amm-definizioni-workflow', {
  fetchPage: listDefinizioniWorkflow,
  // Parte piena: e' configurazione, non una ricerca.
  startsEmpty: false,
  filterDefaults: { tipo_prestazione_id: null },
})
