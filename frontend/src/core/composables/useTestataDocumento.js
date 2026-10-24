// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: LA TESTATA DI UN DOCUMENTO DOPO LA BOZZA — quali campi del form si
//        cambiano ancora, letti dalla capability e mai dallo stato. Nato il
//        2026-10-10 (brief-db-testata-dopo-emissione, R-FE-3; regola del 2,
//        ok Tid): la stessa regola serviva ai sei drawer documento di vendite
//        (ordine, DDT, reso, preventivo, offerta, contratto).
//
// ⭐ LA REGOLA, del database e non del drawer: il lock di testata
//    (`vendite.trgfn_doc_testata_lock_fuori_bozza`) dice colonna per colonna
//    in quali stati una colonna si cambia, e la capability lo porta al form:
//    `can_edit_testata` («almeno una colonna si cambia») e
//    `non_editable_fields` (quelle ferme). Qui si legge, non si deduce.
//
// ⚠️ `can_edit_testata` conta TUTTE le colonne della testata, anche quelle
//    che il form non mostra (le note). Per questo il chiamante dichiara i
//    `campi` che il suo form mostra: la testata e' modificabile solo se
//    almeno UNO di quelli e' aperto. Senza, su un ordine confermato
//    comparirebbe un «Salva» sopra un form tutto spento.
//
// ⚠️ Il CORPO del drawer resta protetto dal readonly di stato del chiamante
//    (righe e sub-drawer seguono le loro regole; gli indirizzi la capability
//    `can_edit_indirizzi`, in `DocumentoIndirizziSection`). Il form della
//    testata ci sta sopra con `app-escape` quando ha qualcosa di aperto
//    (`sopraCorpoProtetto`), e il footer ne libera il Salva
//    (`footerReadonly`, la prop omonima di `AppDrawer`).
//
// ⛔ `presente` dice «il documento ESISTE», non «il dettaglio e' arrivato»: in
//    EDIT e' vero gia' durante il caricamento, quando la capability e' ancora
//    vuota e quindi il form resta fermo (fail-closed). Con `hasDetail` da solo
//    il form si aprirebbe, col Salva, finche' il dettaglio non arriva.
//
// Uso:
//   const testata = useTestataDocumento({
//     caps,                                         // useEntityCapabilities
//     campi: CAMPI_FORM_TESTATA_DDT,                // le colonne che il form mostra
//     readonlyPuro: () => isReadonlyPuro.value,     // permessi, split…
//     presente: () => isEdit.value || hasDetail.value, // il documento esiste
//     corpoProtetto: () => isReadonly.value,        // il readonly di stato del drawer
//   })
//   <div :class="{ 'app-escape': testata.sopraCorpoProtetto.value }">
//     <DdtForm :is-modificabile="testata.modificabile.value"
//              :non-editable-fields="testata.campiBloccati.value" … />
//   </div>
//   <AppDrawer :footer-readonly="testata.footerReadonly.value" …>
import { computed } from 'vue'

export function useTestataDocumento({ caps, campi, readonlyPuro, presente, corpoProtetto }) {
  // Le colonne ferme nello stato, dalla capability. Senza documento (creazione)
  // non ce ne sono: il form e' tutto aperto e decide la creazione.
  const campiBloccati = computed(() => (presente() ? [...caps.nonEditableFields.value] : []))

  // Il form ha almeno un campo da cambiare: permessi, poi capability.
  const modificabile = computed(() => {
    if (readonlyPuro()) return false
    if (!presente()) return true
    if (!caps.canEdit.value) return false
    const fermi = caps.nonEditableFields.value
    return campi.some((campo) => !fermi.has(campo))
  })

  // Scopo: un campo del form e' spento? Spento tutto se la testata non si
  //        modifica, altrimenti campo per campo dalla capability.
  function bloccato(campo) {
    if (!modificabile.value) return true
    return presente() && caps.nonEditableFields.value.has(campo)
  }

  // Il form esce dal corpo protetto solo se ha qualcosa di aperto.
  const sopraCorpoProtetto = computed(() => modificabile.value && corpoProtetto())

  // `AppDrawer.footerReadonly`: libera il Salva sopra un corpo protetto;
  // `undefined` = il footer segue la catena readonly.
  const footerReadonly = computed(() => (modificabile.value ? false : undefined))

  return { modificabile, campiBloccati, bloccato, sopraCorpoProtetto, footerReadonly }
}
