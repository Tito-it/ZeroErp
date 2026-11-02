// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Lo store della lista UNITA' DI MISURA OPERATIVE di un articolo
//        (`catalogo.articolo_uom`, lista 111), consumato da `ArticoloUomDrawer`
//        attraverso `ListaConFormInline` (2026-10-31, brief-db-liste-datatable-
//        grezze-secondo-giro riga 4: prima una `DataTable` grezza sulla
//        collezione intera).
// Note: ⭐ Il padre (`padreId`) e' l'articolo (uuid), nel path.
//       ⭐ La busta porta anche `non_editable_fields` (i campi che dopo la
//       creazione non si cambiano, dalla vista DB): li trattiene lo store, e
//       il form li legge. Sono metadati del modello, non dati dell'utente.
//       ⭐ Uno store PER ISTANZA del drawer (`storePerIstanza`): due drawer
//       UoM vivi insieme non si scrivono addosso la lista.
//       ⛔ Fino al 2026-10-31 `nonEditableFields` era un `ref` di MODULO:
//       condiviso fra tutte le istanze e mai azzerato, sotto l'articolo nuovo
//       restavano i campi bloccati di quello prima finche' la lettura non
//       tornava. Ora e' stato dello store, scritto da `onPayload` (dopo il
//       guard di versione: le risposte scartate non lo toccano) e azzerato
//       da `reset()` al cambio di padre.
// ------------------------------------------------------------

import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { listArticoloUom } from '../api/catalogo'

export const useArticoloUomStore = storePerIstanza('catalogo-articolo-uom', (id) => defineStore(id,
  () => {
    const nonEditableFields = ref([])

    const base = useListaStoreCore({
      fetchPage: listArticoloUom,
      parentField: 'padreId',
      // L'articolo e' gia' scelto quando il drawer si apre.
      startsEmpty: false,
      onPayload: (payload) => { nonEditableFields.value = payload.non_editable_fields || [] },
    })

    // ⚠️ Il reset del core non conosce lo stato di dominio: al cambio di
    //    articolo i campi bloccati di quello prima non restano sul form.
    function reset() {
      base.reset()
      nonEditableFields.value = []
    }

    return { ...base, reset, nonEditableFields }
  },
  { userScoped: true },
))
