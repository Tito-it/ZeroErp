// Scopo: Utility centralizzata per formattazione date.
// Tutte le conversioni Date → stringa per API backend passano da qui.
// Evita il bug toISOString() che converte in UTC (mezzanotte locale → giorno prima in UTC).
//
// ⭐ UN SOLO FUSO, QUELLO DELL'AZIENDA (dal 2026-10-09, brief
//    brief-be-db-fe-un-solo-fuso-aziendale, F-1/F-2/F-4 e decisione T-1).
//    Il fuso e' un DATO del database (`SYSTEM_FUSO_ORARIO`), arriva dal profilo
//    (`fuso_aziendale` di `/core/me/`) e lo consegna qui `impostaFusoAziendale`
//    (store auth, a ogni lettura del profilo). Il fuso del PC dell'utente NON
//    conta: «oggi», l'ora di un istante e l'ora che l'operatore digita sono
//    quelli dell'azienda, gli stessi dei documenti, dei PDF e degli export.
//
//    Due specie di valori, e non vanno confuse:
//    - un GIORNO di calendario (`'YYYY-MM-DD'`, il valore dei DatePicker senza
//      ora) si tiene in una `Date` LOCALE a mezzanotte (`parseIsoDate`,
//      `oggiAziendale`): e' solo il contenitore dei tre numeri, il fuso non
//      c'entra;
//    - un ISTANTE (`timestamptz`, stringa ISO con offset) si legge con
//      `parseIstante` e si mostra con `displayTimestamp`/`displayTime`, che lo
//      convertono nel fuso dell'azienda.
//    ⛔ `new Date()` per «oggi», `new Date('YYYY-MM-DD')` (mezzanotte UTC: nei
//       fusi negativi e' il giorno prima), `setHours(0,0,0,0)` e
//       `toLocale*String` senza fuso stanno solo qui: lo presidia
//       `datePresidio.spec.js`.
//    ⚠️ Prima che il profilo arrivi (pagine di login) il fuso non e' noto, e
//       le funzioni usano quello del browser: li' non si mostrano date di
//       dominio. Non e' un ripiego dei dati: e' la sola informazione che c'e'.

// ── Il fuso dell'azienda ────────────────────────────────────────────────────

let _fuso = null
const _formatter = new Map()

/**
 * Imposta il fuso dell'azienda (nome IANA, es. `Europe/Rome`). La chiama lo
 * store auth a ogni lettura del profilo. Un nome che il browser non conosce
 * non si imposta (e si dice in console): resterebbe un fuso inventato.
 *
 * @param {string|null} nome
 */
export function impostaFusoAziendale(nome) {
  if (!nome) {
    _fuso = null
    return
  }
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: nome })
    _fuso = nome
  } catch {
    console.error(`fuso dell'azienda sconosciuto al browser: ${nome}`)
    _fuso = null
  }
}

/** Il fuso dell'azienda impostato, o null se il profilo non e' ancora arrivato. */
export function fusoAziendale() {
  return _fuso
}

// Scopo: le parti di calendario e d'orologio di un istante NEL FUSO
//        DELL'AZIENDA: `{ y, m, d, hh, mi, ss }` (mese 1-12).
function partiNelFuso(istante) {
  const chiave = _fuso ?? ''
  let fmt = _formatter.get(chiave)
  if (!fmt) {
    fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: _fuso ?? undefined,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
    })
    _formatter.set(chiave, fmt)
  }
  const p = {}
  for (const { type, value } of fmt.formatToParts(istante)) p[type] = value
  return {
    y: Number(p.year), m: Number(p.month), d: Number(p.day),
    hh: Number(p.hour), mi: Number(p.minute), ss: Number(p.second),
  }
}

const _2 = (n) => String(n).padStart(2, '0')

/** L'istante di adesso. Sede unica del «now»: chi lo vuole lo chiede qui. */
export function adesso() {
  return new Date()
}

/**
 * Un ISTANTE da una stringa ISO con offset (com'e' un `timestamptz` nel JSON)
 * o da una `Date`. `null` se assente o illeggibile.
 *
 * @param {string|Date|null} v
 * @returns {Date|null}
 */
export function parseIstante(v) {
  if (!v) return null
  const d = v instanceof Date ? v : new Date(v)
  return isNaN(d.getTime()) ? null : d
}

/**
 * OGGI nel fuso dell'azienda, come `Date` locale a mezzanotte (il contenitore
 * di un giorno di calendario, come quelli dei DatePicker).
 *
 * @returns {Date}
 */
export function oggiAziendale() {
  const p = partiNelFuso(adesso())
  return new Date(p.y, p.m - 1, p.d)
}

/** Come `oggiAziendale()`, in `'YYYY-MM-DD'`. */
export function oggiAziendaleString() {
  return toDateString(oggiAziendale())
}

/**
 * Il GIORNO (`'YYYY-MM-DD'`) in cui cade un istante, nel fuso dell'azienda:
 * le 23:30 UTC del 14 sono il 15 a Roma.
 *
 * @param {string|Date|null} ts
 * @returns {string|null}
 */
export function giornoAziendale(ts) {
  const d = parseIstante(ts)
  if (!d) return null
  const p = partiNelFuso(d)
  return `${p.y}-${_2(p.m)}-${_2(p.d)}`
}

/**
 * Il mese `'YYYY-MM'` di un giorno di calendario (`Date` locale o
 * `'YYYY-MM-DD'`). Sede unica della concatenazione.
 *
 * @param {Date|string|null} d
 * @returns {string|null}
 */
export function toMeseString(d) {
  const s = toDateStringOrNull(d)
  return s ? s.substring(0, 7) : null
}

/**
 * Un istante mostrato come l'OROLOGIO DELL'AZIENDA in una `Date` locale: le
 * sue ore e i suoi minuti locali sono quelli dell'azienda. Serve a precaricare
 * un DatePicker con l'ora (F-4): l'operatore legge l'ora dell'azienda, non
 * quella del suo PC. Il ritorno e' `oraAziendaleComeIstante`.
 *
 * @param {string|Date|null} ts
 * @returns {Date|null}
 */
export function istanteComeOraAziendale(ts) {
  const d = parseIstante(ts)
  if (!d) return null
  const p = partiNelFuso(d)
  return new Date(p.y, p.m - 1, p.d, p.hh, p.mi, p.ss)
}

/**
 * L'ISTANTE di un'ora dell'azienda digitata in un DatePicker: la `Date` locale
 * porta data e ora DELL'AZIENDA nei suoi campi locali, e si risolve nel fuso
 * dell'azienda (non in quello del PC). Inverso di `istanteComeOraAziendale`.
 * ⚠️ Nell'ora che il cambio legale salta l'istante e' quello dopo il salto.
 *
 * @param {Date|null} d
 * @returns {Date|null}
 */
export function oraAziendaleComeIstante(d) {
  if (!(d instanceof Date) || isNaN(d.getTime())) return null
  const comeUtc = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(),
    d.getHours(), d.getMinutes(), d.getSeconds())
  // Due passi: l'offset del fuso si legge all'istante candidato, che puo'
  // stare dall'altra parte di un cambio legale rispetto alla prima stima.
  let istante = comeUtc - _offsetMs(new Date(comeUtc))
  istante = comeUtc - _offsetMs(new Date(istante))
  return new Date(istante)
}

// Scopo: lo scarto in millisecondi fra l'orologio dell'azienda e UTC a un istante.
function _offsetMs(istante) {
  const p = partiNelFuso(istante)
  const comeUtc = Date.UTC(p.y, p.m - 1, p.d, p.hh, p.mi, p.ss)
  return comeUtc - Math.floor(istante.getTime() / 1000) * 1000
}

/**
 * Converte un valore data in stringa YYYY-MM-DD per invio al backend.
 * Accetta: Date, stringa ISO, null/undefined.
 * Usa ora locale (non UTC) per evitare shift di giorno.
 *
 * @param {Date|string|null} d - Valore data
 * @returns {string|null} - Stringa 'YYYY-MM-DD' o null
 */
/**
 * Formatta una data per visualizzazione: DD/MM/YYYY.
 * Accetta: stringa 'YYYY-MM-DD', Date, null/undefined.
 *
 * @param {string|Date|null} d - Valore data
 * @returns {string} - Stringa 'DD/MM/YYYY' o stringa vuota
 */
// ⭐ Una stringa con l'ORA e' un istante: il giorno e' quello dell'azienda
//    (`giornoAziendale`), non i primi dieci caratteri, che col JSON in `Z`
//    sarebbero il giorno UTC (fino al 2026-10-09, F-1).
// ⚠️ Separatore `T` (JSON) o spazio: un `timestamptz::text` del backend arriva
//    come `'2026-09-14 23:30:00+00'`, ed e' un istante come l'altro.
export function displayDate(d) {
  if (!d) return ''
  const s = typeof d === 'string'
    ? (d.length > 10 && (d[10] === 'T' || d[10] === ' ') ? (giornoAziendale(d) ?? d) : d)
    : toDateString(d)
  if (!s || s.length < 10) return s || ''
  const [y, m, day] = s.substring(0, 10).split('-')
  return `${day}/${m}/${y}`
}

/**
 * Formatta un timestamp per visualizzazione: DD/MM/YYYY, HH:mm:ss.
 * Accetta: stringa ISO, Date, null/undefined.
 *
 * @param {string|Date|null} ts - Valore timestamp
 * @returns {string} - Stringa 'DD/MM/YYYY, HH:mm:ss' o stringa vuota
 */
// ⭐ Nel fuso dell'AZIENDA, non del browser (T-1, dal 2026-10-09).
export function displayTimestamp(ts) {
  const d = parseIstante(ts)
  if (!d) return ''
  const p = partiNelFuso(d)
  return `${_2(p.d)}/${_2(p.m)}/${p.y}, ${_2(p.hh)}:${_2(p.mi)}:${_2(p.ss)}`
}

/**
 * Formatta solo l'ora (HH:mm) di un timestamp, nel fuso dell'AZIENDA.
 * Accetta: stringa ISO, Date, null/undefined.
 *
 * @param {string|Date|null} ts - Valore timestamp
 * @returns {string} - Stringa 'HH:mm' o stringa vuota
 */
export function displayTime(ts) {
  const d = parseIstante(ts)
  if (!d) return ''
  const p = partiNelFuso(d)
  return `${_2(p.hh)}:${_2(p.mi)}`
}

/**
 * La DATA di oggi da mostrare (topbar): giorno della settimana, giorno, mese
 * e anno nella lingua data, nel fuso dell'azienda.
 *
 * @param {string} locale - es. 'it-IT'
 * @returns {string}
 */
export function displayOggiEsteso(locale) {
  return adesso().toLocaleDateString(locale, {
    timeZone: _fuso ?? undefined,
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

// ⛔ SU UNA INVALID DATE QUESTA FUNZIONE PRODUCE "NaN-NaN-NaN", E DEVE
//    CONTINUARE A FARLO. Sembra un difetto ed e' il comportamento giusto QUI:
//    i suoi ~90 chiamanti sono in maggioranza PAYLOAD DI FORM (`valido_al`,
//    `data_valuta`, `data_scadenza`, `data_riattivazione_prevista`), e li'
//    «data scritta male» e «nessuna data» sono l'OPPOSTO l'una dell'altra.
//    Una stringa storta la respinge il backend con un 400 che l'operatore vede;
//    un `null` su un campo OPZIONALE verrebbe accettato e salverebbe il record
//    col campo SVUOTATO — su un `valido_al` vuol dire trasformare in silenzio
//    una validita' chiusa in una aperta.
// ⚠️ Provato e ritirato il 2026-09-08: il guard su `Number.isNaN` era stato
//    messo QUI per il filtro data delle code, e collassava i due significati
//    per tutti i chiamanti. Chi vuole «data oppure niente» usa
//    `toDateStringOrNull` qui sotto: sono due domande diverse e restano due
//    funzioni.
export function toDateString(d) {
  if (!d) return null
  if (d instanceof Date) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  // Se gia' stringa, ritorna cosi' com'e' (assume formato valido)
  return String(d)
}

/**
 * Come `toDateString`, ma una data NON VALIDA vale «nessuna data» (`null`).
 *
 * ⭐ E' la variante per i FILTRI di lista, dove «non ho ancora finito di
 * scrivere una data» deve valere «non filtrare» — non «filtra per una data
 * impossibile». Il chiamante tipico e' il `buildParams` di uno store.
 *
 * ⛔ NON usarla per i payload dei form: li' una data storta deve arrivare al
 * backend e farsi respingere, altrimenti il campo si salva vuoto in silenzio.
 * E' esattamente la ragione per cui esistono due funzioni invece di un guard
 * dentro `toDateString`.
 *
 * ⚠️ DA DOVE ARRIVA UNA INVALID DATE, perche' non e' un caso di laboratorio: i
 * `DatePicker` PrimeVue hanno `manualInput` a `true` di DEFAULT (verificato su
 * 4.5), quindi il campo si digita — e mentre si digita il componente emette
 * una `Date` non valida. Sulle due code produceva
 * `data_da=NaN-NaN-NaN` e un `E_VALIDATION_INPUT / data_da_invalid` a ogni
 * tasto (2026-09-07).
 *
 * @param {Date|string|null} d - Valore data
 * @returns {string|null} - 'YYYY-MM-DD', oppure null se assente o non valida
 */
export function toDateStringOrNull(d) {
  if (d instanceof Date && Number.isNaN(d.getTime())) return null
  return toDateString(d)
}

/**
 * Converte un valore data/ora in stringa ISO 8601 (UTC) per campi timestamptz.
 * A differenza di toDateString (solo data, no shift di fuso), qui serve l'istante
 * assoluto: per un timestamp completo toISOString() e' corretto e non ambiguo
 * (il backend lo casta a timestamptz).
 *
 * @param {Date|string|null} d - Valore data/ora
 * @returns {string|null} - Stringa ISO con offset (UTC) o null
 */
export function toTimestampString(d) {
  if (!d) return null
  const date = d instanceof Date ? d : new Date(d)
  if (isNaN(date.getTime())) return null
  return date.toISOString()
}

/**
 * Converte una stringa ISO 'YYYY-MM-DD' in Date locale senza shift di fuso.
 * Usato per precaricare DatePicker da valori persistiti nel backend.
 *
 * @param {string|Date|null} s - Stringa ISO o Date
 * @returns {Date|null} - Date locale a mezzanotte o null
 */
export function parseIsoDate(s) {
  if (!s) return null
  if (s instanceof Date) return s
  const match = String(s).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

/**
 * Il nome del giorno della settimana `indice` (0 = lunedi', come
 * `dovuto.giorno` delle sveglie) nella lingua data. Un giorno di calendario
 * qualunque di quel nome, quindi nessun fuso in gioco.
 *
 * @param {number} indice - 0 (lunedi') … 6 (domenica)
 * @param {string} locale - es. 'it-IT'
 * @returns {string}
 */
export function nomeGiornoSettimana(indice, locale) {
  // Il 1° gennaio 2024 e' un lunedi'.
  return new Date(2024, 0, 1 + Number(indice)).toLocaleDateString(locale, { weekday: 'long' })
}

/**
 * I dodici nomi dei mesi (gennaio … dicembre) nella lingua data: indice 0 =
 * gennaio. Il gemello di `nomeGiornoSettimana` per i mesi; un giorno di
 * calendario qualunque di ogni mese, quindi nessun fuso in gioco. Estratto il
 * 2026-10-31 (regola del 2, ok Tid): i cruscotti mensili (`useDashMesiNav`) e
 * la tendina del mese di partenza dei canoni sulla testata.
 *
 * @param {string} locale - es. 'it-IT'
 * @returns {string[]}
 */
export function nomiMesi(locale) {
  const fmt = new Intl.DateTimeFormat(locale, { month: 'long' })
  return Array.from({ length: 12 }, (_, m) => fmt.format(new Date(2024, m, 1)))
}

/**
 * Ritorna una Date locale a mezzanotte = OGGI DELL'AZIENDA + N giorni.
 * Helper standard per i parameters lead-gg dei `defaultForm()` (Fase 2
 * refactor frontend vendite). Centralizzare evita pattern ripetuto
 * `const d = new Date(); d.setHours(0,0,0,0); d.setDate(d.getDate() + N)`
 * in ogni drawer (era cablato in CloneVersioneDrawer, PromoArticoloDrawer).
 *
 * @param {number} n - Giorni da sommare a oggi (0 = oggi, 1 = domani, ...).
 * @returns {Date} - Date locale a mezzanotte.
 */
export function addDaysToToday(n) {
  const d = oggiAziendale()
  if (n) d.setDate(d.getDate() + Number(n))
  return d
}

/**
 * Un giorno di calendario (`Date` o `'YYYY-MM-DD'`) a mezzanotte locale, per
 * i confronti fra giorni (`a < b`) senza l'ora. `null` se assente o illeggibile.
 * Sede unica di `setHours(0, 0, 0, 0)`.
 *
 * @param {Date|string|null} d
 * @returns {Date|null}
 */
export function giornoDi(d) {
  if (!d) return null
  if (d instanceof Date) {
    if (isNaN(d.getTime())) return null
    const g = new Date(d.getTime())
    g.setHours(0, 0, 0, 0)
    return g
  }
  return parseIsoDate(d)
}

/**
 * Giorni di arretrato del floor temporale di default delle liste.
 * Sta qui, non nei singoli store: e' una scelta UX di progetto, e cambiarla
 * deve costare una riga sola.
 */
export const LISTE_FILTRO_DATA_GIORNI = 60

/**
 * Floor temporale di DEFAULT delle liste: `oggi - 60 giorni`, riportato al
 * PRIMO GIORNO del mese risultante. Es. oggi 15-08-2026 -> 01-06-2026.
 *
 * L'allineamento al giorno 1 non e' un arrotondamento estetico: rende il
 * default stabile dentro il mese (non scorre di un giorno ogni giorno, quindi
 * l'operatore non vede la lista cambiare da sola) e fa sempre vedere il mese
 * corrente per intero, che e' come si legge un archivio operativo.
 *
 * Regola precedente (fino al 2026-08-01): 1° gennaio dell'anno-1. Era troppo
 * larga — su liste popolate significava scorrere fino a due anni di documenti
 * per arrivare a quelli di ieri.
 *
 * @returns {Date} - Date locale a mezzanotte, primo del mese.
 */
export function defaultFiltroDataDa() {
  const d = addDaysToToday(-LISTE_FILTRO_DATA_GIORNI)
  d.setDate(1)
  return d
}

/**
 * Come `defaultFiltroDataDa()`, ma in stringa `YYYY-MM-DD`: e' la forma che
 * gli store mettono in `filters.data_da` e che il backend riceve.
 *
 * @returns {string} - Data ISO (solo giorno).
 */
export function defaultFiltroDataDaString() {
  return toDateString(defaultFiltroDataDa())
}
