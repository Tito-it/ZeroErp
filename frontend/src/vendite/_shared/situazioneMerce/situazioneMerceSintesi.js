// Scopo: Da payload della situazione merce a RIASSUNTO IN TESTATA — la
// decisione §5.2 del brief pannello: «in testata una riga sola che dice SE c'e'
// qualcosa di aperto, e da li' si apre il dettaglio».
//
// ⭐ LA REGOLA CHE GOVERNA TUTTO E' IL §5.4: il pannello non mostra MAI il
// numero negativo. `-8` diventa «8 da accreditare». Un saldo negativo si legge
// come un guasto anche quando e' la descrizione corretta del mondo; l'operatore
// deve leggere CHE COSA C'E' DA FARE, non fare l'algebra fra due colonne.
//
// ⚠️ E il verso del saldo NON si traduce qui: arriva gia' tradotto dal database
// nella colonna `stato` (richiesta BE-2 — «due traduzioni divergono e diventano
// due frasi per lo stesso numero»). Questo modulo SOMMA per stato, non decide
// quale stato sia.
//
// PERCHE' UN MODULO PURO e non un computed dentro la barra: e' la stessa
// aritmetica per due contesti (ordine e DDT) e la stessa che la dialog usa per
// i totali. Scritta due volte, prima o poi i due numeri divergono — ed e'
// precisamente il difetto che il §5.4 chiede di non commettere.

import { formatNumber } from '../../../core/utils/format'
import { STATO_MERCE } from './situazioneMerceCostanti'

// Scopo: formato UNICO delle quantita' del pannello (barra e dialog): qui si
//        contano PEZZI — «8 da accreditare» si legge, «8,00» no. Vive nel
//        modulo condiviso perche' era gia' copiato identico nei due componenti
//        (regola del 2): barra e dettaglio devono scrivere lo stesso numero
//        nello stesso modo.
export function formatQtaMerce(v) {
  return formatNumber(v, { minimumFractionDigits: 0, maximumFractionDigits: 2, placeholder: '—' })
}

// La sorgente del conto cambia col contesto, e non e' un dettaglio:
//  - sull'ORDINE si somma `righe_ordine` (una riga per riga d'ordine, che
//    aggrega gia' tutte le sue spedizioni). Sommare anche le partite
//    conterebbe la stessa merce due volte;
//  - sul DDT `righe_ordine` e' vuota di proposito e si sommano le `partite`,
//    che sono le righe di QUELLA spedizione.
// Una sola delle due liste entra nel totale, mai entrambe.
function _righeDelConto(sezioni) {
  return sezioni.righe_ordine?.length ? sezioni.righe_ordine : (sezioni.partite ?? [])
}

// Scopo: somma numerica tollerante. I valori arrivano dal DB come stringhe
//        (Decimal serializzato), e `null` e' un valore legittimo che significa
//        «non si applica» — va SALTATO, non convertito in 0.
function _somma(righe, estrai) {
  let totale = 0
  for (const r of righe) {
    const v = estrai(r)
    if (v == null) continue
    const n = Number(v)
    if (Number.isFinite(n)) totale += n
  }
  return totale
}

/**
 * Riassunto della situazione merce di un documento.
 *
 * @param {object} sezioni - `{ righe_ordine, partite, accrediti, riconsegne }`
 * @returns {object} le voci del riassunto + `haPendenze` / `tuttoRegolare`
 */
export function sintesiSituazioneMerce(sezioni) {
  const righe = _righeDelConto(sezioni)
  const partite = sezioni.partite ?? []
  const accrediti = sezioni.accrediti ?? []
  const riconsegne = sezioni.riconsegne ?? []

  // I due versi del saldo, letti dallo `stato` che il DB ha gia' deciso.
  // ⚠️ `da_accreditare` si somma cambiando SEGNO: il payload porta -8, il
  // pannello dice «8». E' il §5.4 in una riga di codice.
  const daFatturare = _somma(
    righe.filter((r) => r.stato === STATO_MERCE.DA_FATTURARE),
    (r) => r.differenza,
  )
  // ⚠️ `|| 0` non e' difensivismo: senza, la negazione di una somma vuota da'
  // `-0`, che supera ogni guardia `> 0` ma si FORMATTA come «-0» — cioe' il
  // numero negativo che il §5.4 vieta, ricomparso dalla porta di servizio.
  // Trovato sui dati veri (un ordine mai spedito, dove la lista e' vuota).
  const daAccreditare =
    -_somma(
      righe.filter((r) => r.stato === STATO_MERCE.DA_ACCREDITARE),
      (r) => r.differenza,
    ) || 0

  // Residuo aperto della coda ri-consegne: merce tornata che deve ancora
  // tornare al cliente. Viene dalla vista della coda, non ricalcolato — cosi'
  // il pannello dice lo stesso numero del tab «Da ri-consegnare».
  const daRiconsegnare = _somma(riconsegne, (r) => r.qta_residua)

  // Arretrato di SPEDIZIONE (solo sull'ordine): esiste come voce a se' perche'
  // il §8.1 del brief partita ha separato i tre significati che `differenza`
  // appiattiva. Non e' un saldo da fatturare ne' da accreditare: e' merce che
  // deve ancora partire.
  const daSpedire = _somma(sezioni.righe_ordine ?? [], (r) => r.da_spedire)

  // ⚠️ FE-3: `fatturato_anticipato` NON e' un accredito. Sta qui come voce
  // separata e non entra in nessuna somma di saldo — sommarlo alla differenza
  // rimetterebbe il falso allarme del rilievo A, cioe' l'applicazione che chiede
  // di emettere note di credito per merce che deve ancora spedire.
  const fatturatoAnticipato = _somma(sezioni.righe_ordine ?? [], (r) => r.fatturato_anticipato)

  // ⚠️ FE-1: «non calcolabile» deve APPARIRE diverso da «tutto regolare».
  // Qui si contano le righe, non le quantita': di un conto che non si puo'
  // fare non esiste un totale, e inventarne uno sarebbe l'errore opposto.
  const nonMisurabili = righe.filter((r) => r.misurabile === false).length

  // ⚠️ FE-2: l'avviso sulla riga sospetta esiste SOLO se il frontend lo mostra
  // (S6b: «una colonna che nessuno mostra non avvisa nessuno»). Si legge sempre
  // dalle partite, anche sull'ordine: e' una proprieta' della riga di merce.
  const sospette = partite.filter((p) => p.sospetto_duplicato_ordine === true).length

  // Le due code sono la coda di lavoro vera: il conteggio serve a dire
  // «da qui si va a fare qualcosa», e l'etichetta DOVUTA/FACOLTATIVA sta nel
  // dettaglio, dove c'e' lo spazio per spiegarla.
  const nAccrediti = accrediti.length

  // 🔴 Righe con un IMPEGNO vero — e serve a una cosa sola, ma decisiva.
  // Dal 2026-08-18 (`20260818-06`) una riga di ordine sotto la soglia
  // CONFERMATO esce `NON_IMPEGNATA` con `da_spedire` NULL: giusto, ma toglie
  // l'unica voce che su una bozza faceva `haPendenze`. Senza questo filtro
  // `tuttoRegolare` diventerebbe TRUE su un ordine in bozza — la spunta verde
  // «tutto regolare» su un documento dove non e' successo NIENTE.
  // ⚠️ E' lo stesso requisito §5.2 di sempre, sul terzo caso che allora non
  // esisteva: «tutto regolare», «non ancora calcolato» e «non ancora
  // impegnato» sono TRE cose, e solo la prima si puo' affermare.
  const righeImpegnate = righe.filter((r) => r.stato !== STATO_MERCE.NON_IMPEGNATA)

  // «Pendenza» = c'e' qualcosa da fare o da guardare. L'anticipo NON e' una
  // pendenza (e' un fatto contabile che si dichiara), e nemmeno le partite in
  // ri-consegna (i loro pezzi sono contati sulla partita d'origine).
  const haPendenze =
    daFatturare > 0 ||
    daAccreditare > 0 ||
    daRiconsegnare > 0 ||
    daSpedire > 0 ||
    nonMisurabili > 0 ||
    sospette > 0

  return {
    daFatturare,
    daAccreditare,
    daRiconsegnare,
    daSpedire,
    fatturatoAnticipato,
    nonMisurabili,
    sospette,
    nAccrediti,
    nPartite: partite.length,
    haPendenze,
    nonImpegnate: righe.length - righeImpegnate.length,
    // ⚠️ `tuttoRegolare` NON e' `!haPendenze`: pretende anche che ci sia
    // qualcosa da raccontare — righe con un impegno vero. Su un documento
    // senza merce, o su un ordine ancora in bozza, il pannello non deve
    // affermare «tutto regolare»: non ha guardato niente.
    // E' l'altra meta' del requisito §5.2, quella che si dimentica.
    tuttoRegolare: !haPendenze && righeImpegnate.length > 0,
  }
}
