// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: IL FOOTER DI UN DRAWER DOCUMENTO — quale variante di `AppDrawer`
//        (`footer`) mostra, secondo lo stato del documento. Estratto il
//        2026-10-03 (D-11 di work-done/analisi-fe-chrome-drawer.md,
//        regola del 2, ok Tid): migrando i documenti su `AppDrawer` la stessa
//        computed era nata identica in quattro drawer (reso, DDT, ordine,
//        preventivo) e in variante in due (contratto, offerta).
//
// ⭐ LA REGOLA, del modello dei documenti e non di un drawer:
//    · col form di una RIGA aperto → 'nessuno': il form ha il suo
//      Annulla/Salva, un secondo footer lo duplicherebbe;
//    · finche' la testata si modifica → 'form' (Annulla/Salva);
//    · il documento c'e' ma non si tocca → 'chiudi': un'uscita deliberata in
//      basso, non solo la X (dopo la bozza il cambio di stato passa dalla
//      DrawerActionsBar, un Salva non avrebbe niente da salvare);
//    · nient'altro (documento non ancora letto) → 'nessuno'.
//
// ⚠️ «Si modifica» lo decide il chiamante (`modificabile`), perche' ha una
//    regola di dominio sua: il contratto in ATTIVO tecnicamente si modifica ma
//    il Salva non si mostra, l'offerta guarda il readonly di stato.
//
// Uso:
//   const footerDrawer = useFooterDocumento({
//     formRigaAperto: () => formRigaAperto.value,      // facoltativo
//     modificabile: () => testata.modificabile.value,     // useTestataDocumento
//     presente: () => hasDetail.value,
//   })
//   <AppDrawer :footer="footerDrawer" …>
import { computed } from 'vue'

export function useFooterDocumento({ formRigaAperto = () => false, modificabile, presente }) {
  return computed(() => {
    if (formRigaAperto()) return 'nessuno'
    if (modificabile()) return 'form'
    return presente() ? 'chiudi' : 'nessuno'
  })
}
