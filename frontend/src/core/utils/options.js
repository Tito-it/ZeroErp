// Factory di options riutilizzabili per Select/Dropdown PrimeVue.
// Scopo: centralizzare i pattern ripetuti (bool tri-state, ecc.) per evitare
// duplicazione in 6+ SearchTable admin (pattern rilevato su listini v5).

// Scopo: la voce «tutti» di un filtro tri-state, in UNA definizione.
// ⛔ NON E' DECORAZIONE, ed e' la ragione per cui questo pezzo ha una sede sua:
//    e' il GESTO con cui l'operatore SPEGNE il filtro. Senza, un filtro che
//    nasce valorizzato non si puo' piu' togliere — e col segno dei filtri
//    attivi diventa un'unita' contata su cui non c'e' nessuna azione possibile
//    (standard FE §«Un filtro che l'operatore non puo' togliere e' un difetto»,
//    trovato in-app da Tid il 2026-09-23 su `/catalogo/articoli`).
// ⚠️ Il valore e' `null` e non l'assenza della chiave: `paramsFiltro` manda i
//    soli filtri `!= null`, quindi «tutti» e' l'unico valore che NON viaggia.
function voceTutti(t) {
  return { value: null, label: t('common.all') }
}

// Scopo: le opzioni di un filtro a VOCABOLARIO (stati, tipi) precedute dalla
//        voce «tutti» — la stessa di `buildBoolOptions`, senza ricopiarla.
//        `voci` = `[{ value, label }]` gia' tradotte.
export function buildOptionsConTutti(t, voci) {
  return [voceTutti(t), ...voci]
}

// Scopo: Ritorna le 3 opzioni standard per un Select "tri-state bool"
// (tutti, si, no). Passare la funzione t di vue-i18n.
export function buildBoolOptions(t) {
  return [
    voceTutti(t),
    { value: true, label: t('common.yes') },
    { value: false, label: t('common.no') }
  ]
}

// Scopo: le 3 opzioni del filtro ATTIVO — tutti / attivo / non attivo.
// ⭐ E' `buildBoolOptions` con le etichette di DOMINIO, e la differenza non e'
//    cosmetica: li' il filtro chiede «si o no?» su una proprieta' qualunque,
//    qui chiede lo STATO della riga, che e' un concetto del modello (ogni
//    anagrafica ha `attivo`, e `AttivoTag` lo rende con queste stesse parole).
// ⛔ ESTRATTA IL 2026-09-23 (regola del 2, ok Tid) DA CINQUE SEDI, una delle
//    quali era gia' una factory in un altro dominio
//    (`amministrazione/constants.js::buildFilterStatoOptions`, ritirata nello
//    stesso giro) e due delle quali — listini e famiglie documento — mostravano
//    nella TENDINA una parola diversa da quella che la loro stessa COLONNA
//    scriveva con `AttivoTag`: «Inattivo» contro «Non attivo».
//    ⚠️ E' il difetto che la duplicazione nasconde: cinque copie della stessa
//    terna divergono una alla volta, e nessuna fallisce.
// ⚠️ Le etichette stanno in `common.*` e NON in `amministrazione.*`: un
//    building block di `core` che leggesse il vocabolario di un dominio
//    invertirebbe la dipendenza — e infatti la copia di `ListiniSearchTable`
//    (che sta in `vendite`) importava le chiavi di `amministrazione`.
export function buildAttivoOptions(t) {
  return [
    voceTutti(t),
    { value: true, label: t('common.active') },
    { value: false, label: t('common.inactive') }
  ]
}
