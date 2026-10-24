// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: ⭐ LA FRASE CHE SPIEGA UN'AZIONE SPENTA, letta da dove la manda il
//        database. Le `script.fn_check_*` di dominio (§12.5.1) rispondono con
//        un array ORDINATO di motivi, e il backend porta in riga il primo:
//        `<verbo>_reason`, `<verbo>_reason_key`, `<verbo>_dettaglio`. Qui si
//        traduce la terna in una frase, una volta per tutte le superfici.
//
// ⛔ E' LETTURA, NON TRASPORTO. Questo modulo non sa quale verbo sta
//    spiegando, non conosce nessun dominio e non tiene stato: prende la terna
//    e restituisce una stringa. Il giorno che un verbo nuovo nasce, non si
//    tocca niente qui — si passa un prefisso diverso.
//
// ⭐ IL PREFISSO E' UN PARAMETRO PERCHE' I VERBI SONO PIU' DI UNO SULLA STESSA
//    RIGA. Un registro di numerazione ne ha due, e rispondono a domande
//    diverse: `rimozione_blocco_*` dice «posso spegnerlo?»,
//    `forma_blocco_*` dice «posso cambiargli la forma del numero?». Su un
//    registro che ha gia' numerato sono spenti ENTRAMBI, per motivi diversi —
//    riusare una colonna per l'altra domanda mostrerebbe la frase sbagliata
//    senza che niente fallisca (api.md §12.5.4).
//
// ⚠️ I PARAMETRI DELLA FRASE STANNO IN `dettaglio`, NON IN `valori`. Le check
//    emettono due cose diverse e si somigliano: `valori` e' un array
//    POSIZIONALE che riempie i `%s` del messaggio a catalogo (lo legge il
//    database, per il testo del rifiuto), `dettaglio` e' un oggetto con NOMI
//    (`codice`, `quante`, `ultimo_numero`) ed e' quello che riempie i
//    segnaposto `{...}` della chiave i18n. Passare `valori` a `t()` non
//    solleva niente: stampa la frase coi segnaposto ancora dentro.

// Scopo: la terna di un verbo, letta dalla riga. Separata dalla composizione
//        perche' chi vuole solo sapere SE l'azione e' bloccata non ha bisogno
//        di `t`/`te` (e non deve importarli per scoprirlo).
export function bloccoDaRiga(riga, prefisso) {
  return {
    reason: riga?.[`${prefisso}_reason`] || '',
    reasonKey: riga?.[`${prefisso}_reason_key`] || '',
    dettaglio: riga?.[`${prefisso}_dettaglio`] ?? null,
  }
}

// Scopo: la terna -> la frase. Fail-visible su DUE livelli, ed e' lo stesso
//        ripiego di `useDrawerActions`: senza CHIAVE si mostra il codice
//        macchina (che dice comunque qualcosa), con la chiave ma senza
//        traduzione ci pensa il `te()`.
// ⛔ La chiave si guarda PRIMA di passarla: il database puo' emettere un
//    motivo senza `reason_key`, e chiedere a `te()` di controllare un valore
//    nullo non e' una domanda che ha senso fare.
export function componiBloccoMotivo(t, te, { reason = '', reasonKey = '', dettaglio = null } = {}) {
  if (!reasonKey) return reason
  if (!te(reasonKey)) return reason
  // ⚠️ Il guard sul TIPO, non su `?.length`: se un domani il repository
  //    smettesse di decodificare il jsonb, `dettaglio` sarebbe una STRINGA —
  //    che `t()` accetta come lista di parametri posizionali e che renderebbe
  //    la frase con i segnaposto vuoti invece di lasciarla intera. E' la
  //    stessa regola del guard su `storia` nel tab BA.
  const params =
    dettaglio && typeof dettaglio === 'object' && !Array.isArray(dettaglio)
      ? dettaglio
      : null
  return params ? t(reasonKey, params) : t(reasonKey)
}

// Scopo: la scorciatoia che usano le superfici — riga + prefisso -> frase.
export function motivoBloccoRiga(t, te, riga, prefisso) {
  return componiBloccoMotivo(t, te, bloccoDaRiga(riga, prefisso))
}

// Scopo: «l'azione e' spenta?», letta dalla stessa fonte della frase.
// ⛔ Si guarda il FLAG del backend (`can_*`) quando c'e', e si ripiega sulla
//    presenza del motivo. Dedurre il blocco dalla sola frase funzionerebbe
//    oggi e si romperebbe il giorno che una check emette un motivo
//    informativo: la domanda «posso?» la risponde il backend, non il testo.
export function bloccoAttivo(riga, prefisso, campoFlag = null) {
  if (campoFlag && riga && campoFlag in riga) return riga[campoFlag] === false
  return Boolean(riga?.[`${prefisso}_reason`])
}

// Scopo: la frase di un verbo spento quando la riga porta il SOLO codice del
//        motivo (`<verbo>_blocco`, linee-guida-sql §12.5.1: il `reason` del
//        primo motivo della check, `NULL` = ammesso) e la chiave i18n e'
//        convenzione del DB: `<prefissoChiave>.<codice minuscolo>`.
//        Stringa vuota se il codice non c'e' (azione accesa).
// ⭐ Estratto il 2026-10-12 alla seconda occorrenza (regola del 2, ok Tid,
//    brief-db-date-consegna-righe-in-blocco §8): `correggi_qta_evasa_blocco`
//    della riga di DDT e `data_consegna_confermata_blocco` della riga d'ordine.
//    Fail-visible come `componiBloccoMotivo`: chiave non tradotta -> codice.
export function motivoDaCodiceBlocco(t, te, codice, prefissoChiave) {
  if (!codice) return ''
  return componiBloccoMotivo(t, te, {
    reason: codice,
    reasonKey: `${prefissoChiave}.${String(codice).toLowerCase()}`,
  })
}
