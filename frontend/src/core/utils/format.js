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

// Le cifre decimali di una QUANTITA' a video e nei campi di input: le quantita'
// dei documenti e del magazzino (UoM base) arrivano fino a 6 decimali — la
// proporzione dei componenti di un kit reso si arrotonda li' (round(…, 6) in
// `vendite.fn_reso_merce_da_rientrare`). Una sede sola per il numero.
export const QTA_MAX_DECIMALI = 6

/**
 * Una QUANTITA' a video: niente zeri inutili («4», «2,5»), fino a
 * `QTA_MAX_DECIMALI` decimali. Regola del 2 (2026-10-13): la stessa forma era
 * scritta a mano nei componenti del kit della fattura, e la chiedevano i
 * prelievi della bolla, i rientri del reso e i blocchi di magazzino.
 * @param {number|string|null} value
 * @param {object} [opts]
 * @param {string} [opts.placeholder='']
 * @returns {string}
 */
export function formatQuantita(value, { placeholder = '' } = {}) {
  return formatNumber(value, { placeholder, minimumFractionDigits: 0, maximumFractionDigits: QTA_MAX_DECIMALI })
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

/**
 * Numero leggibile di una fattura a partire dai campi denormalizzati che le
 * righe satellite portano con se' (`fattura_anno`, `fattura_serie`,
 * `fattura_numero`, `fattura_id`): `"2026/A n. 815"`.
 *
 * ⭐ Estratto il 2026-09-04 (regola del 2, ok Tid) da `CodaStampaTab`, quando
 *    il drawer rapido delle code ha dovuto nominare le STESSE righe: la riga di
 *    coda deve leggersi identica nella scheda e nel pannello che la richiama —
 *    scritta due volte, il giorno in cui una delle due cambia le due divergono
 *    senza che niente fallisca.
 * ⚠️ Il ripiego e' `#<id>`, non un vuoto: finche' la fattura e' in BOZZA il
 *    numero e' NULL per costruzione (lo assegna il trigger alla numerazione), e
 *    una cella vuota si leggerebbe come un dato perso invece che come «non
 *    ancora numerata».
 *
 * @param {object} row - Riga con i campi `fattura_*`.
 * @param {object} [opts]
 * @param {string} [opts.placeholder='—'] - Usato se manca anche l'id.
 * @returns {string}
 */
export function formatFatturaNumero(row, opts = {}) {
  const { placeholder = '—' } = opts
  if (row == null) return placeholder
  if (row.fattura_numero == null) {
    return row.fattura_id != null ? `#${row.fattura_id}` : placeholder
  }
  // ⚠️ Anno e serie si compongono e POI si uniscono con uno spazio solo: la
  //    forma `${anno}${serie} n. ${numero}` lasciava un'etichetta che comincia
  //    con uno spazio quando l'anno manca — invisibile in una cella, non in un
  //    messaggio di conferma dove finisce fra virgolette.
  const anno = `${row.fattura_anno ?? ''}${row.fattura_serie ? `/${row.fattura_serie}` : ''}`
  return [anno, `n. ${row.fattura_numero}`].filter(Boolean).join(' ')
}
