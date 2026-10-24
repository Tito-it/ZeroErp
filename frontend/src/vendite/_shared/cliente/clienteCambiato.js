// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL CLIENTE NEL FORM E' DIVERSO DA QUELLO SALVATO? Vero se una delle
//        colonne che dicono chi e' il cliente del documento ha nel form un
//        valore diverso da quello del dettaglio letto dal server. Lo usa
//        `useCambioClienteDocumento` (il cambio si salva subito, con conferma).
// Note: ⭐ Regola del 2 (2026-10-19, ok Tid): offerta e contratto lo
//       scrivevano a mano nel `handleSave`. Gemello lato BE: `coppia_cambiata`
//       di `_cliente_coppia_documento.py`, e come la' gli id si confrontano
//       sul TESTO: un id puo' arrivare come numero o come stringa (rotta,
//       contesto di pratica), e 7 contro '7' non e' un cambio di cliente.
//       ⛔ Qui un falso «cambiato» non e' un avviso: apre la conferma che
//       SALVA (`useCambioClienteDocumento`). Il resto del confronto e' quello
//       UNICO del progetto, `valoriUguali` di `useDrawerFormPreserve`: vuoto
//       vale vuoto comunque sia scritto.
// ------------------------------------------------------------

import { valoriUguali } from '../../../core/composables/useDrawerFormPreserve'

// Le colonne del cliente di preventivo, offerta e contratto: il billing account
// (l'istanza segue il BA). Il DDT aggiunge il destinatario senza BA.
export const CLIENTE_BA = Object.freeze(['billing_account_id'])

// Scopo: un id come testo (gemello di `_come_testo` del BE); il vuoto lo
//        decide `valoriUguali`.
function comeTesto(valore) {
  return typeof valore === 'number' ? String(valore) : valore
}

// Scopo: `form` e `detail` sono oggetti piani; senza dettaglio (creazione) non
//        c'e' niente di salvato da cui differire.
export function clienteCambiato(form, detail, campi = CLIENTE_BA) {
  if (!form || !detail) return false
  return campi.some((campo) => !valoriUguali(comeTesto(form[campo]), comeTesto(detail[campo])))
}
