// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA COLLA FRA UN DRAWER E IL BB `ListaConFormInline` (2026-10-31,
//        regola del 2): la stessa ventina di righe era scritta uguale in
//        `NoteDrawer` e `ArticoloUomDrawer`. Dice, in un punto solo:
//        · il PADRE della lista, solo a drawer aperto: il `null` alla
//          chiusura azzera la lista, e le voci del padre precedente non
//          lampeggiano sotto il prossimo;
//        · se il form della voce e' aperto (`@form-aperto`), e quindi il
//          footer del drawer: `'nessuno'` a form aperto (il form ha gia' il
//          suo Annulla/Salva), `'chiudi'` altrimenti;
//        · le modifiche della voce aperta (D-13) e l'uscita con conferma, che
//          `AppDrawer` riceve in `:modificato` e `:conferma-uscita`.
// Note: Uso nel drawer:
//         const { listaRef, formAperto, padre, modificato, chiudiConConferma,
//                 footer, onFormAperto } = useDrawerListaConForm({
//           visible: () => props.visible,
//           padre: () => props.articoloId,
//         })
//         <AppDrawer :modificato="modificato" :conferma-uscita="chiudiConConferma"
//                    :footer="footer" …>
//           <ListaConFormInline ref="listaRef" :parent-id="padre"
//                               @form-aperto="onFormAperto" …>
//       ⚠️ `listaRef` va destrutturato con QUESTO nome nel setup: e' il
//       template ref (`ref="listaRef"`) della shell.
//       ⚠️ `modificato` legge l'expose della shell, che i ref li scarta gia'
//       (defineExpose auto-unwrap): e' un booleano, non un ref.
// ------------------------------------------------------------

import { computed, ref, toValue } from 'vue'

export function useDrawerListaConForm({ visible, padre }) {
  const listaRef = ref(null)
  const formAperto = ref(false)

  const padreAperto = computed(() => (toValue(visible) ? toValue(padre) : null))
  const modificato = computed(() => !!listaRef.value?.modificato)
  const footer = computed(() => (formAperto.value ? 'nessuno' : 'chiudi'))

  // Scopo: l'uscita dal drawer passa dalla conferma del form della voce.
  //        Senza la shell montata non c'e' niente da confermare.
  function chiudiConConferma(chiudi) {
    if (listaRef.value) listaRef.value.chiudiConConferma(chiudi)
    else chiudi()
  }

  function onFormAperto(aperto) {
    formAperto.value = aperto
  }

  return {
    listaRef, formAperto, padre: padreAperto,
    modificato, chiudiConConferma, footer, onFormAperto,
  }
}
