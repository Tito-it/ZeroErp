// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le due azioni di riga «Disattiva» / «Riattiva» di un'anagrafica con
//        `attivo`, con la conferma e il verbo dello store — in un posto solo.
// Note: Regola del 2 (2026-09-21, ok Tid): la stessa coppia di azioni, con la
//       stessa conferma e lo stesso `store.update(id, { attivo })`, era
//       scritta identica TRE volte (lista magazzini, drawer ubicazioni,
//       drawer lotti) — cambiavano solo le chiavi i18n dell'entita'.
//
//       ⭐ Il rifiuto e' del DATABASE (`E_ATTIVO_BLOCK_CHILDREN_EXIST` con
//       figli attivi, 409 con la frase): qui si chiede conferma e si lascia
//       parlare il backend. Riattivare non ha guard, ma resta un gesto
//       esplicito con conferma.
//       ⛔ In sola lettura le azioni si NASCONDONO (permesso ⇒ nascondi,
//       stato ⇒ disabilita — api.md §Capability di riga). `RowActionsMenu`
//       non conosce `hideWhenReadonly`: il filtro sta nel `visible`.
//       ⚠️ `allowWhenInactive` sulla riattivazione NON e' un di piu':
//       `RowActionsMenu` disabilita da se' le azioni sulle righe spente, e
//       senza questo escape la riattivazione sarebbe spenta proprio sulle
//       righe che deve riaccendere.
//
//       Contratto i18n, sotto `prefisso` (es. `magazzino.ubicazioni`):
//         conferma_disattiva_title · conferma_disattiva ({codice})
//         conferma_riattiva_title  · conferma_riattiva  ({codice})
//         esito_disattiva          · esito_riattiva
//       Le etichette dei pulsanti sono comuni: `common.disattiva` /
//       `common.riattiva`.
//
// Uso:
//   const { azioniAttivo } = useAzioniAttivo(store, {
//     prefisso: 'magazzino.ubicazioni',
//     onDone: () => reloadAll(),   // opzionale: chi non ha un evento di tab
//   })
//   function buildRowActions(riga) { return [ ...altre, ...azioniAttivo(riga) ] }
// ------------------------------------------------------------

import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../constants'
import { useApiHandler } from './useApiHandler'
import { useConfirmAction } from './useConfirmAction'
import { useInjectReadonly } from './useReadonlyMode'

// Scopo: le azioni «Disattiva»/«Riattiva» di riga legate a uno store con
//        `update(id, payload)` e al prefisso i18n dell'entita'.
// @param {object} store - lo store della lista, con `update(id, { attivo })`.
// @param {object} opts
// @param {string} opts.prefisso - prefisso i18n dell'entita' (vedi contratto).
// @param {Function} [opts.onDone] - dopo una scrittura riuscita (es. `reloadAll`);
//        chi si rinfresca dall'evento di tab dello store non ne ha bisogno.
export function useAzioniAttivo(store, { prefisso, onDone = null }) {
  const { t } = useI18n()
  const { execute } = useApiHandler()
  const { confirmAction } = useConfirmAction()
  const isReadonly = useInjectReadonly()

  // Scopo: chiede conferma e scrive `attivo`; il rifiuto arriva dal DB con la
  //        sua frase. ⛔ Nessun refetch qui oltre a `onDone`: il verbo dello
  //        store emette il suo evento, e chi ascolta si ricarica.
  function cambiaAttivo(riga, attivo) {
    const verbo = attivo ? 'riattiva' : 'disattiva'
    confirmAction({
      header: t(`${prefisso}.conferma_${verbo}_title`),
      message: t(`${prefisso}.conferma_${verbo}`, { codice: riga.codice }),
      danger: !attivo,
      onAccept: async () => {
        const res = await execute(
          () => store.update(riga.id, { attivo }),
          { successMessage: t(`${prefisso}.esito_${verbo}`) },
        )
        if (res !== null && typeof onDone === 'function') onDone(res)
      },
    })
  }

  // Scopo: le due voci per `RowActionsMenu`: una sola e' visibile per riga,
  //        secondo lo stato; nessuna in sola lettura.
  function azioniAttivo(riga) {
    return [
      {
        key: 'disattiva',
        label: t('common.disattiva'),
        icon: MANAGE_ICONS.DISATTIVA,
        severity: 'danger',
        visible: !isReadonly.value && riga.attivo,
        command: () => cambiaAttivo(riga, false),
      },
      {
        key: 'riattiva',
        label: t('common.riattiva'),
        icon: MANAGE_ICONS.RIATTIVA,
        visible: !isReadonly.value && !riga.attivo,
        allowWhenInactive: true,
        command: () => cambiaAttivo(riga, true),
      },
    ]
  }

  return { azioniAttivo, cambiaAttivo }
}
