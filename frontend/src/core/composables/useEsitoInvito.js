// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La lettura UNICA dell'esito di un invito di veste (operatore,
//        cliente e fornitore portale, cliente shop). Il backend risponde
//        `inviato` = l'email E' PARTITA (BB `InvitoVeste.spedisci`): con
//        `false` il link c'e' ma la persona non l'ha ricevuto, e il toast di
//        successo sarebbe una bugia. Regola del 2 (ok Tid 2026-09-28): la
//        lettura serviva a `OperatoreDrawer` e `PortaleAccessoPanel`.
// Note: ⛔ Si guarda `=== false`, non la verità del campo: una risposta che
//        non porta `inviato` (un endpoint che non lo dice) resta un successo,
//        come prima. Il campo lo dichiarano tutti e tre i flussi d'invito.
// ------------------------------------------------------------

import { useI18n } from 'vue-i18n'
import { useNotify } from './useNotify'

export function useEsitoInvito() {
  const notify = useNotify()
  const { t } = useI18n()

  // Scopo: Toast dell'esito. `data` e' il `data` dell'envelope; `messaggioOk`
  //        il testo di successo del chiamante (porta la sua veste). Ritorna
  //        se l'email e' partita.
  function notificaEsitoInvito(data, messaggioOk) {
    if (data?.inviato === false) {
      notify.warn(t('common.invito_non_spedito'))
      return false
    }
    notify.success(messaggioOk)
    return true
  }

  return { notificaEsitoInvito }
}
