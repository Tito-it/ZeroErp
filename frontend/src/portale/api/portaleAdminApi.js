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

// Scopo: Invita un cliente come SHOP_CUSTOMER (B1 §13.7 admin-driven).
// Stesso pattern di invitaClientePortale ma genera identita SHOP_CUSTOMER
// invece di CLIENTE_PORTALE. Supportato solo per clienti (i fornitori non
// accedono allo shop B2C consumer).
export function invitaClienteShop(clienteId, { email, reinvio = false } = {}) {
  return api.post(`/anagrafiche/clienti/${clienteId}/invita-shop/`, {
    email,
    reinvio,
  })
}

// ── Stato + disattivazione veste (§6.2.4 + §6.2.6) ────────────────────

// Scopo: Legge lo stato aggregato delle vesti non-operatore del cliente
// (portale + shop). Ritorna `{ portale: {...stato}, shop: {...stato} }`
// con `stato ∈ {NESSUNO, PENDING, DISATTIVO, ATTIVO}`. Usato dal
// PortaleAccessoPanel per renderizzare stato corrente + abilitare/
// nascondere i pulsanti azione.
export function getStatoAccessiCliente(clienteId) {
  return api.get(`/anagrafiche/clienti/${clienteId}/stato-accessi/`)
}

// Scopo: Stato veste portale del fornitore (niente shop B2C).
export function getStatoAccessiFornitore(fornitoreId) {
  return api.get(`/anagrafiche/fornitori/${fornitoreId}/stato-accessi/`)
}

// Scopo: Soft-revoke veste portale cliente. Idempotente: se gia'
// disattivata ritorna `{disattivato: false, stato: "DISATTIVO"}`.
// Invalida i token pendenti — se un invito era in volo, il link smette
// di funzionare.
export function disattivaPortaleCliente(clienteId) {
  return api.post(`/anagrafiche/clienti/${clienteId}/disattiva-portale/`)
}

// Scopo: Soft-revoke veste shop cliente. Idempotente.
export function disattivaShopCliente(clienteId) {
  return api.post(`/anagrafiche/clienti/${clienteId}/disattiva-shop/`)
}

// Scopo: Soft-revoke veste portale fornitore. Idempotente.
export function disattivaPortaleFornitore(fornitoreId) {
  return api.post(`/anagrafiche/fornitori/${fornitoreId}/disattiva-portale/`)
}
