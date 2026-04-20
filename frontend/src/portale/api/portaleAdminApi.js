// Scopo: client API admin-side per invito portale cliente/fornitore.
// Gli endpoint vivono sotto /api/v1/anagrafiche/{clienti|fornitori}/{id}/invita-portale/
// (coerenza con il CRUD esistente, vedi api.md §Routing). Il BE delega
// al service InvitoPortaleService dell'app portale.
import api from '../../core/api'

// Scopo: Invita un cliente al portale. `reinvio=true` invalida i token
// precedenti prima di generare il nuovo invito.
export function invitaClientePortale(clienteId, { email, reinvio = false } = {}) {
  return api.post(`/anagrafiche/clienti/${clienteId}/invita-portale/`, {
    email,
    reinvio,
  })
}

// Scopo: Invita un fornitore al portale. Simmetrico a invitaClientePortale.
export function invitaFornitorePortale(fornitoreId, { email, reinvio = false } = {}) {
  return api.post(`/anagrafiche/fornitori/${fornitoreId}/invita-portale/`, {
    email,
    reinvio,
  })
}
