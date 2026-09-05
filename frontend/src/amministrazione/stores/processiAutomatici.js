// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista dei PROCESSI AUTOMATICI (`dbops.processi`) e dello
//        stato dei sei presidi del cantiere «nessun processo senza operatore».
//
// ⭐ `createListaStore` e non `createCrudStore`: questa lista NON possiede
//    l'entità che mostra. Il registro dei processi è CATALOGO — nasce da un
//    seed, non da questa schermata — e uno store con `create`/`update` che
//    nessuno chiama sarebbe un contratto che non descrive niente.
// ⚠️ `startsEmpty: false`: il registro è corto e chiuso (una ventina di righe).
//    Una lista che parte vuota ha senso dove i dati sono tanti e la ricerca è il
//    filtro; qui l'elenco intero È l'informazione.
import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import { listProcessi, getProcessiPresidi } from '../api/amministrazione'

export const useProcessiAutomaticiStore = createListaStore(
  'amm-processi-automatici',
  {
    fetchPage: listProcessi,
    startsEmpty: false,
    // I filtri di pannello: sempre inviati quando valorizzati.
    filterDefaults: { classe: null, canale: null, attivo: null },
    // ⭐ L'ordine di partenza lo decide il backend (canale, poi codice): qui non
    //    si dichiara, così non ci sono due ordinamenti di default da tenere
    //    allineati.
    extend: () => {
      // Lo stato dei presidi vive accanto alla lista ma NON è la lista: si
      // carica una volta e si ricarica col «Ricarica» della pagina.
      const presidi = ref([])
      const presidiConRighe = ref(0)
      const presidiLoading = ref(false)
      // ⛔ Il terzo caso: «nessun presidio acceso» e «non sono riuscito a
      //    leggerli» si assomigliano (l'array è vuoto in entrambi) e dicono
      //    cose opposte. Su un pannello che serve a dire «va tutto bene» la
      //    differenza è tutto.
      const presidiErrore = ref(false)

      async function caricaPresidi() {
        presidiLoading.value = true
        presidiErrore.value = false
        try {
          const res = await getProcessiPresidi()
          presidi.value = res.data.data.presidi
          presidiConRighe.value = res.data.data.con_righe
        } catch {
          presidi.value = []
          presidiConRighe.value = 0
          presidiErrore.value = true
        } finally {
          presidiLoading.value = false
        }
      }

      return {
        presidi, presidiConRighe, presidiLoading, presidiErrore, caricaPresidi,
      }
    },
  },
)
