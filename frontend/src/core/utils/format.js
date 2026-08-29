// Scopo: Utility centralizzate per formattazione valori.
// Un solo punto di modifica per formati numerici/dimensioni in tutta l'applicazione.

/**
 * Tolleranza floating-point per confronti tra prezzi.
 * = mezzo step del 6° decimale (InputNumber accetta `max-fraction-digits=6`).
 * Usato per dirty-check / delta override vs prezzo suggerito: copre il
 * rounding di display senza confondere modifiche genuine al 6° decimale.
 * Centralizzato per evitare drift fra i caller (ComponentiDialog,
 * PreventiviRigaComponentiPanel, futuri EDIT panel su ordini/contratti/ddt).
 */
export const PRICE_EPSILON = 5e-7

/**
 * Formatta una dimensione in byte in formato leggibile (B, KB, MB, GB).
 *
 * @param {number|null} bytes - Dimensione in byte
 * @returns {string} - Stringa formattata o vuota se null/0
 */
export function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

/**
 * Formatta un valore come valuta locale (default EUR in it-IT).
 *
 * ⭐ `placeholder` vale `'—'` di default dal 2026-08-29 (autorizzato da Tid).
 *    Prima era la stringa vuota, e nove chiamanti su sessantasette passavano
 *    `{ placeholder: '—' }` a mano — cioe' la convenzione c'era gia' ed era
 *    scritta a mano ogni volta. ⛔ Su un IMPORTO la cella vuota e il trattino
 *    non sono la stessa cosa: `null` qui vuol dire «questo conto non si
 *    applica» (un importo mai dichiarato, un saldo che non esiste), e una cella
 *    vuota si legge come **un dato perso** mentre il trattino si legge come
 *    una risposta.
 * ⚠️ Chi vuole davvero il vuoto lo chiede: `{ placeholder: '' }`.
 * ⚠️ `formatNumber` qui sotto ha ancora `placeholder: ''` — non e' stato
 *    cambiato perche' non e' la stessa domanda: una quantita' assente non e'
 *    per forza «non si applica». Se un giorno lo diventera', si cambia li' e
 *    si dichiara, non per simmetria.
 *
 * @param {number|string|null} value
 * @param {Object} [opts]
 * @param {string} [opts.currency='EUR']
 * @param {string} [opts.locale='it-IT']
 * @param {string} [opts.placeholder='—'] - cosa restituire per null/undefined
 * @param {number} [opts.minimumFractionDigits] - override decimali min (default locale: 2 per EUR)
 * @param {number} [opts.maximumFractionDigits] - override decimali max (default locale: 2 per EUR)
 * @returns {string}
 */
export function formatCurrency(value, opts = {}) {
  const {
    currency = 'EUR',
    locale = 'it-IT',
    placeholder = '—',
    minimumFractionDigits,
    maximumFractionDigits,
  } = opts
  if (value == null) return placeholder
  const formatOpts = { style: 'currency', currency }
  if (minimumFractionDigits != null) formatOpts.minimumFractionDigits = minimumFractionDigits
  if (maximumFractionDigits != null) formatOpts.maximumFractionDigits = maximumFractionDigits
  return Number(value).toLocaleString(locale, formatOpts)
}

/**
 * Formatta un valore come numero locale (default 2 decimali in it-IT).
 *
 * @param {number|string|null} value
 * @param {Object} [opts]
 * @param {string} [opts.locale='it-IT']
 * @param {number} [opts.minimumFractionDigits=2]
 * @param {number} [opts.maximumFractionDigits]
 * @param {string} [opts.placeholder='']
 * @returns {string}
 */
export function formatNumber(value, opts = {}) {
  const {
    locale = 'it-IT',
    minimumFractionDigits = 2,
    maximumFractionDigits,
    placeholder = '',
  } = opts
  if (value == null) return placeholder
  const formatOpts = { minimumFractionDigits }
  if (maximumFractionDigits != null) formatOpts.maximumFractionDigits = maximumFractionDigits
  return Number(value).toLocaleString(locale, formatOpts)
}

/**
 * Etichetta IVA per liste/colonne compatte.
 * - Aliquota > 0 → "22%" (aliquota numerica)
 * - Aliquota 0/NULL (esenti) → `iva_codice` (es. "N1", "ESENTE17") che e'
 *   sempre univoco e breve. Lo schema `config.iva` garantisce per CHECK
 *   che un'aliquota=0 abbia sempre natura o assoggettamento, quindi il
 *   codice e' parlante per l'operatore. Fallback su `placeholder` se
 *   anche il codice manca (record non agganciato a una riga `config.iva`).
 *
 * Per visualizzazioni piu' ricche (riepilogo IVA, drawer dettaglio) usare
 * la descrizione estesa `iva_descrizione`; per la compattezza in liste e
 * datatable usare questa.
 *
 * @param {object} row - Riga con almeno `iva_aliquota` e `iva_codice`.
 * @param {object} [opts]
 * @param {string} [opts.placeholder='—'] - Mostrato se mancano sia aliquota >0 sia codice.
 * @returns {string}
 */
export function formatIvaLabel(row, opts = {}) {
  const { placeholder = '—' } = opts
  if (row == null) return placeholder
  const aliquota = row.iva_aliquota != null ? Number(row.iva_aliquota) : null
  if (aliquota != null && aliquota > 0) return `${row.iva_aliquota}%`
  if (row.iva_codice) return String(row.iva_codice)
  return placeholder
}
