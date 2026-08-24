// Scopo: decodifica i18n fail-visible per vocabolari estensibili DB-side
//        (motivi fermo, classi backlog, stadi funnel, azioni giornale, ...):
//        ritorna la label tradotta se la chiave esiste, altrimenti il
//        fallback (tipicamente il codice grezzo, o una label generica) —
//        MAI il path della chiave i18n mancante a video.
//        Estratto 2026-07-06 (regola del 2, ok Tid): unifica i micro-helper
//        `te(key) ? t(key) : code` sparsi in dashboard/pratiche/catalogo.
//        t/te vengono iniettati dal chiamante (useI18n del componente) per
//        restare reattivi al cambio locale.
export function labelOrCode(t, te, key, fallback) {
  return te(key) ? t(key) : fallback
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
