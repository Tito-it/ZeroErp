// Scopo: Store Pinia per la pagina admin "Gestione personalizzazioni liste".
//        Gestisce stato condiviso tra i tab Preset e Permessi colonne:
//          - lookup delle liste configurabili (Select header)
//          - lista corrente selezionata (`listaCorrenteId`)
//
// Userscoped: la selezione "lista corrente" e la cache lookup sono
// per-utente. Al logout vanno azzerati per evitare leak cross-user
// (regola memoria feedback_pinia_userscoped.md).

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { listAdminListaDefinizioni } from '../../core/api/ui-admin-api'

export const useUiAdminStore = defineStore('ui-admin', () => {
  const liste = ref([])
  const listaCorrenteId = ref(null)
  const loading = ref(false)
  const loaded = ref(false)
  const lastError = ref(null)

  const listaCorrente = computed(() =>
    liste.value.find((l) => l.id === listaCorrenteId.value) || null,
  )

  // Scopo: Carica lookup liste definite (idempotente single-flight).
  //        Se la lista corrente diventa orfana (es. attivo flippato a
  //        false), resetta listaCorrenteId per coerenza UX.
  async function loadListe(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    lastError.value = null
    try {
      const res = await listAdminListaDefinizioni()
      liste.value = res.data.data
      loaded.value = true
      if (
        listaCorrenteId.value != null
        && !liste.value.find((l) => l.id === listaCorrenteId.value)
      ) {
        listaCorrenteId.value = null
      }
    } catch (e) {
      lastError.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  // Scopo: Imposta la lista corrente (chiamato dal Select header).
  function selectLista(id) {
    listaCorrenteId.value = id
  }

  // Scopo: Reset stato a logout (autoResetPlugin lo invoca tramite il
  //        flag userScoped). Serve perche' liste e selezione contengono
  //        dati specifici dell'utente loggato.
  function clearUserState() {
    liste.value = []
    listaCorrenteId.value = null
    loading.value = false
    loaded.value = false
    lastError.value = null
  }

  return {
    liste,
    listaCorrenteId,
    listaCorrente,
    loading,
    loaded,
    lastError,
    loadListe,
    selectLista,
    clearUserState,
  }
}, { userScoped: true })
