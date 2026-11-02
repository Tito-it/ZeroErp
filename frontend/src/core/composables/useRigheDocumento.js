// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: IL LEGAME FRA UN DRAWER DOCUMENTO E LA SUA TABELLA-RIGHE — estratto il
//        2026-10-03 (regola del 2, ok Tid): la stessa manciata di righe era
//        ricopiata nei quattro drawer documento di vendite (preventivo,
//        ordine, DDT, reso), uguale salvo il nome della regola «testata
//        modificabile».
//
// ⭐ TRE COSE CHE VANNO INSIEME:
//    · `righeTableRef` — il ref della tabella-righe (`RigheMasterDetailTable`
//      dietro un `*RigheTable`), per `loadRighe` e per la sua fotografia;
//    · `documento` — testata E riga aperta, una domanda sola all'uscita
//      (`unisciFotografie`, D-13): `documento.chiudiConConferma` va a
//      `conferma-uscita` (o a `useDrawerAutosaveBozza` come `confermaUscita`);
//    · `footerDrawer` — la variante del footer secondo lo stato (BB
//      `useFooterDocumento`, D-11), che legge `formRigaAperto`, scritto da
//      `onFormAperto` sull'evento `form-aperto` della tabella.
//
// ⚠️ `modificabile` e `presente` sono getter letti al render: possono nominare
//    computed dichiarati piu' sotto nel setup.
//
// Uso:
//   const { righeTableRef, onFormAperto, documento, footerDrawer } = useRigheDocumento({
//     testata: { modificato, chiudiConConferma },          // useDrawerFormPreserve
//     modificabile: () => testata.modificabile.value,     // useTestataDocumento
//     presente: () => hasDetail.value,
//   })
//   <AppDrawer :footer="footerDrawer" :conferma-uscita="documento.chiudiConConferma" …>
//     <OrdiniRigheTable ref="righeTableRef" @form-aperto="onFormAperto" … />
import { ref } from 'vue'
import { unisciFotografie } from './useDrawerFormPreserve'
import { useFooterDocumento } from './useFooterDocumento'

export function useRigheDocumento({ testata, modificabile, presente }) {
  const righeTableRef = ref(null)
  const formRigaAperto = ref(false)
  const documento = unisciFotografie(testata, () => righeTableRef.value)
  const footerDrawer = useFooterDocumento({
    formRigaAperto: () => formRigaAperto.value,
    modificabile,
    presente,
  })
  function onFormAperto(aperto) {
    formRigaAperto.value = aperto
  }
  return { righeTableRef, formRigaAperto, onFormAperto, documento, footerDrawer }
}
