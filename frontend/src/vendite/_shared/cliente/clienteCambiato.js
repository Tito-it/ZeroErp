// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL CLIENTE NEL FORM E' DIVERSO DA QUELLO SALVATO? Vero se una delle
//        colonne che dicono chi e' il cliente del documento ha nel form un
//        valore diverso da quello del dettaglio letto dal server. Serve a due
//        cose: al salvataggio (con un cambio di cliente la scheda di fornitura
//        del form non viaggia: la rifa' il DB) e al pannello degli indirizzi
//        (prima di Salva mostra ancora quelli del cliente salvato, e lo dice).
// Note: ⭐ Regola del 2 (2026-10-19, ok Tid): offerta e contratto lo
//       scrivevano ognuno a modo suo nel `handleSave`. Gemello lato BE:
//       `coppia_cambiata` di `_cliente_coppia_documento.py`. Il confronto e' sul
//       testo, come la' (un id puo' arrivare come numero o come stringa), e
//       vuoto vale null.
// ------------------------------------------------------------

// Le colonne del cliente di preventivo, offerta e contratto: il billing account
// (l'istanza segue il BA). Il DDT aggiunge il destinatario senza BA.
export const CLIENTE_BA = Object.freeze(['billing_account_id'])

function comeTesto(valore) {
  return valore == null || valore === '' ? null : String(valore)
}

// Scopo: `form` e `detail` sono oggetti piani; senza dettaglio (creazione) non
//        c'e' niente di salvato da cui differire.
export function clienteCambiato(form, detail, campi = CLIENTE_BA) {
  if (!form || !detail) return false
  return campi.some((campo) => comeTesto(form[campo]) !== comeTesto(detail[campo]))
}
