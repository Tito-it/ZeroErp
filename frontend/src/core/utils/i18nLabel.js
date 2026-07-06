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
