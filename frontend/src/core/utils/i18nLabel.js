// Scopo: decodifica i18n fail-visible per vocabolari estensibili DB-side
//        (motivi fermo, classi backlog, stadi funnel, azioni giornale, ...):
//        ritorna la label tradotta se la chiave esiste, altrimenti il
//        fallback (tipicamente il codice grezzo, o una label generica) —
//        MAI il path della chiave i18n mancante a video.
//        Estratto 2026-07-06 (regola del 2, ok Tid): unifica i micro-helper
//        `te(key) ? t(key) : code` sparsi in dashboard/pratiche/catalogo.
//        t/te vengono iniettati dal chiamante (useI18n del componente) per
//        restare reattivi al cambio locale.
//        `params` (opzionale, 2026-09-24): i parametri della frase — lista
//        per i segnaposto posizionali `{0}`, oggetto per quelli con nome.
//        Omesso = `t(key)` come prima.
export function labelOrCode(t, te, key, fallback, params) {
  if (!te(key)) return fallback
  return params === undefined ? t(key) : t(key, params)
}

// Scopo: L'etichetta di un RUOLO APPLICATIVO (la veste: OPERATORE,
//        CLIENTE_PORTALE, ...), dalla chiave `auth.ruolo_applicativo.<CODICE>`;
//        chiave mancante ⇒ il codice (fail-visible, `labelOrCode`); codice
//        assente ⇒ '' (il segnaposto a video lo sceglie il chiamante).
//        Estratto 2026-09-27 (regola del 2, ok Tid): la regola era scritta tre
//        volte — lista operatori, profilo del portale, dialog del riuso — e le
//        copie gia' divergevano (il profilo non ripiegava sul codice e avrebbe
//        mostrato il path della chiave).
export function etichettaRuoloApplicativo(t, te, codice) {
  if (!codice) return ''
  return labelOrCode(t, te, `auth.ruolo_applicativo.${codice}`, codice)
}

// Scopo: ⭐ L'INTESTAZIONE DI UNA COLONNA DI LISTA, tradotta. Il catalogo
//        `ui.lista_colonna` porta DUE cose: l'`etichetta` (italiana, scritta
//        nel seed) e la `etichetta_i18n_key`, che è la vera fonte multilingua.
//        Qui si sceglie fra le due, una volta per tutti i consumatori.
//
// ⚠️ NASCE DA UN DIFETTO MISURATO (2026-08-22, rilievo di Tid). Le colonne non
// si traducevano MAI — in nessuna lista, in nessuna lingua — e non perché
// mancassero le traduzioni: 506 colonne su 47 liste dichiarano la loro chiave e
// tutte e 506 esistono in `it.json` E in `en.json`. Il difetto era di
// PLUMBING, in due punti che si nascondevano a vicenda:
//   1. `ListaConfigurabile` cercava la chiave nei metadati del CATALOGO, ma
//      l'endpoint del catalogo non la restituiva (mancava nella SELECT);
//      quella della CONFIG, che arrivava a ogni richiesta, non veniva letta;
//   2. la modale «personalizza colonne» leggeva direttamente l'`etichetta`.
// E il guard `te(key)` — giusto in sé — rendeva il tutto SILENZIOSO: chiave
// non trovata, nessun avviso, ripiego sull'italiano. Un difetto che si vede
// solo cambiando lingua e leggendo le intestazioni.
//
// 📌 Le chiavi si prendono in ordine: prima la config (arriva sempre, è la
// risoluzione per QUESTO utente), poi il catalogo, poi le etichette letterali.
export function etichettaColonna(t, te, { config = null, meta = null } = {}) {
  const key = config?.etichetta_i18n_key || meta?.etichetta_i18n_key
  if (key && te(key)) return t(key)
  return meta?.etichetta || config?.etichetta || config?.codice || meta?.codice || ''
}
