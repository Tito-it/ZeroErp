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

// Scopo: I referenti del cliente per veste: `{ portale: [voce], shop: [voce],
// email_suggerita }`, una voce per veste (anche spenta) con `identita_id`,
// `username`, `email`, `stato` (di `script.fn_stato_veste`), `utilizzabile`
// (di `script.fn_veste_utilizzabile`), `valido_dal`/`valido_al`,
// `token_scade_at`. Elenco vuoto: nessuno invitato. Dal 2026-11-28 (giro 4 del
// brief-db-accessi-area-clienti, D-M7) un cliente ha piu' referenti.
export function getStatoAccessiCliente(clienteId) {
  return api.get(`/anagrafiche/clienti/${clienteId}/stato-accessi/`)
}

// Scopo: I referenti del fornitore (solo `portale`: niente shop B2C).
export function getStatoAccessiFornitore(fornitoreId) {
  return api.get(`/anagrafiche/fornitori/${fornitoreId}/stato-accessi/`)
}

// Scopo: Revoca la veste portale di UN referente del cliente (`identitaId`,
// dalla voce dell'elenco). Idempotente: se gia' spenta ritorna
// `{disattivato: false, stato: "REVOCATA"}` e mette comunque il segno della
// revoca. Invalida i token pendenti — se un invito era in volo, il link smette
// di funzionare; la riapre solo un nuovo invito.
export function disattivaPortaleCliente(clienteId, identitaId) {
  return api.post(`/anagrafiche/clienti/${clienteId}/disattiva-portale/`, { identita_id: identitaId })
}

// Scopo: Revoca la veste shop di un referente del cliente. Idempotente.
export function disattivaShopCliente(clienteId, identitaId) {
  return api.post(`/anagrafiche/clienti/${clienteId}/disattiva-shop/`, { identita_id: identitaId })
}

// Scopo: Revoca la veste portale di un referente del fornitore. Idempotente.
export function disattivaPortaleFornitore(fornitoreId, identitaId) {
  return api.post(`/anagrafiche/fornitori/${fornitoreId}/disattiva-portale/`, { identita_id: identitaId })
}
