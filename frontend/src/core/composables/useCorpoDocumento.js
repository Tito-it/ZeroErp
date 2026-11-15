// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: IL CORPO DI UN DOCUMENTO DOPO LA BOZZA — se il corpo del drawer
//        (sub-drawer, note, componenti: cio' che eredita `READONLY_KEY`) si
//        cambia ancora, letto dalle chiavi della capability e mai dal codice
//        dello stato. Nato il 2026-11-14 (brief-db-stati-documento-dal-
//        vocabolario FE-P1, FE-O1, FE-C1, FE-D1, FE-R3; regola del 2, ok Tid):
//        la stessa regola l'aveva scritta FE-V2 dentro `OffertaDrawer`, e gli
//        altri cinque drawer documento la scrivevano come
//        `stato_codice_interno !== 'DRAFT'`.
//
// ⭐ LA REGOLA, del database e non del drawer: ogni sezione si chiude dalla
//    SUA chiave (`can_edit_righe`, `can_edit_indirizzi`, `can_edit_utility`,
//    …), che il DB legge dal lock della tabella della sezione. Il corpo e'
//    chiuso quando e' chiusa una delle chiavi `corpo`: per i documenti con le
//    righe e' `can_edit_righe` (il lock delle righe coincide con la bozza dal
//    giro D-LOCK), per l'offerta `can_edit_utility` (le righe sono un
//    sotto-drawer fuori dal corpo).
//
// ⚠️ Righe, indirizzi e testata leggono gia' la loro chiave da se'
//    (`canEditRighe`, `DocumentoIndirizziSection`, `useTestataDocumento`):
//    `corpoChiuso` e' il readonly di cio' che resta, da passare in OR coi
//    permessi e da fornire con `provide(READONLY_KEY, …)`.
//
// ⛔ `presente` dice «il documento ESISTE» (come in `useTestataDocumento`): in
//    EDIT e' vero gia' durante il caricamento, quando la capability e' vuota,
//    e il corpo resta chiuso (fail-closed). In CREATE il corpo e' aperto.
//
// Uso:
//   const corpo = useCorpoDocumento({
//     caps,                                          // useEntityCapabilities
//     corpo: ['can_edit_righe'],                     // chiuse queste => corpo chiuso
//     sezioni: ['can_edit_righe', 'can_edit_indirizzi'], // per il banner
//     presente: () => isEdit.value || hasDetail.value,
//   })
//   const isReadonly = computed(() => isReadonlyPuro.value || corpo.corpoChiuso.value)
//   <Message v-if="corpo.sezioneChiusa.value" …>  // «fuori bozza»
import { computed } from 'vue'

export function useCorpoDocumento({ caps, corpo, sezioni = corpo, presente }) {
  const chiusa = (chiave) => !caps.flag(chiave)

  // Il corpo: chiuso se il documento esiste e una delle sue chiavi e' spenta
  // (capability vuota compresa: fail-closed).
  const corpoChiuso = computed(() => presente() && corpo.some(chiusa))

  // Almeno una sezione del drawer e' chiusa: il segnale del banner «fuori
  // bozza». Senza documento, nessuna.
  const sezioneChiusa = computed(() => presente() && sezioni.some(chiusa))

  return { corpoChiuso, sezioneChiusa }
}
