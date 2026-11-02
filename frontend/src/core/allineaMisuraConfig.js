// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ QUANDO UNA LISTA RIPRENDE LE RIGHE PER PAGINA DALLA SUA
//        CONFIGURAZIONE (`pagina_dimensione` di `fn_resolve_lista_config`).
//        Si riallinea quando la misura della configurazione CAMBIA rispetto
//        all'ultima applicata: al primo caricamento, e dopo che l'utente l'ha
//        cambiata nel drawer di personalizzazione (preferenza per chiave,
//        2026-11-01). Una ricarica con la stessa misura non tocca niente: la
//        scelta fatta dal paginatore durante la sessione resta.
// ⛔ Fino al 2026-11-01 la regola era «una volta sola», in quattro copie
//    (`useListaConfigurabilePage`, `useListaDrawerPaginata`, Situazione aperta,
//    Backlog): la misura scelta nel drawer non arrivava alla lista fino al
//    ricaricamento della pagina.
// ⭐ Regola del 2 (ok Tid 2026-11-01). ⚠️ Una FACTORY, non un oggetto
//    condiviso: ogni lista ha la sua memoria dell'ultima misura.
// ------------------------------------------------------------

// Scopo: un allineatore per una lista. `daApplicare(config)` da' la misura
//        da applicare, o `null` se non c'e' niente da fare; `reset()` lo
//        riporta a «mai allineato» (riapertura su un altro padre).
export function allineaMisuraConfig() {
  let ultima = null
  return {
    daApplicare(config) {
      const misura = config?.pagina_dimensione
      if (!misura || misura === ultima) return null
      ultima = misura
      return misura
    },
    reset() {
      ultima = null
    },
  }
}
