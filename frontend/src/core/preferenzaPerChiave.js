// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ LA PREFERENZA PER CHIAVE — quali chiavi di una configurazione
//        (lista o dashboard) l'utente ha SCELTO, e quindi vanno salvate.
//        Dal 2026-11-01 `fn_resolve_lista_config` e `fn_resolve_dashboard_config`
//        risolvono ogni chiave per conto suo e dicono da dove viene
//        (`origine`: preferenza, ruolo, emittente_fiscale, sistema, catalogo).
//        Una chiave assente dalla preferenza vale «come lo standard».
// ⭐ Regola del 2 (ok Tid 2026-11-01): due consumatori, `useListaConfig` e
//    `useDashboardConfig`.
//
// Una chiave e' scelta se:
//   - viene gia' dalla preferenza (`origine[k] === 'preferenza'`), oppure
//   - l'utente l'ha toccata (il valore e' diverso da quello caricato).
// ⭐ `null` vuol dire «come lo standard»: la chiave si toglie anche se veniva
//    dalla preferenza. E' la voce «Come lo standard (N)» del drawer.
// ⛔ Prima del 2026-11-01 si salvava la configurazione RISOLTA intera: chi
//    personalizzava le colonne congelava anche la misura di pagina, l'ordine e
//    i filtri del preset di quel momento, senza poterli vedere.
// ⛔ Nessuna chiave scelta = nessuna preferenza: il chiamante fa il DELETE.
//    Il BE rifiuta il PUT vuoto (E_UI_PREFERENZA_VALIDAZIONE).
// ⚠️ «Toccata» qui vuol dire «diversa da com'era caricata», col confronto
//    unico `valoriUguali`. Chi riscrive una chiave senza cambiarne il senso
//    (rinumera `ordine`, aggiunge `visibile: true`) la fa sembrare scelta: le
//    modali mandano una chiave solo se e' cambiata davvero (`ListaColonneModal`,
//    `DashboardWidgetModal`).
// ------------------------------------------------------------

import { valoriUguali } from './composables/useDrawerFormPreserve'

export const ORIGINE_PREFERENZA = 'preferenza'

// Scopo: le chiavi scelte di `config`, fra le `chiavi` ammesse, col loro
//        valore com'e' (la forma del payload la da' il chiamante).
//        `snapshot` e' la configurazione com'era al caricamento.
export function chiaviScelte(config, snapshot, chiavi) {
  const out = {}
  if (!config) return out
  for (const k of chiavi) {
    const valore = config[k]
    if (valore === null || valore === undefined) continue
    const dallaPreferenza = config.origine?.[k] === ORIGINE_PREFERENZA
    if (dallaPreferenza || !valoriUguali(valore, snapshot?.[k])) out[k] = valore
  }
  return out
}
