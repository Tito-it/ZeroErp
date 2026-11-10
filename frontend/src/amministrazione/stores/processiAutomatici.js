// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista dei PROCESSI AUTOMATICI (`dbops.processi`) e dello
//        stato dei presidi: le viste che il catalogo `dbops.presidi` marca
//        di natura ZERO — quelle che devono restare vuote.
//
// ⭐ `createListaStore` e non `createCrudStore`: questa lista NON possiede
//    l'entità che mostra. Il registro dei processi è CATALOGO — nasce da un
//    seed, non da questa schermata — e uno store con `create`/`update` che
//    nessuno chiama sarebbe un contratto che non descrive niente.
// ⚠️ `startsEmpty: false`: il registro è corto e chiuso (una ventina di righe).
//    Una lista che parte vuota ha senso dove i dati sono tanti e la ricerca è il
//    filtro; qui l'elenco intero È l'informazione.
import { computed, ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import { listProcessi, getProcessiPresidi } from '../api/amministrazione'
import { adottaTestataPresidi } from '../../core/composables/usePresidiPolling'

export const useProcessiAutomaticiStore = createListaStore(
  'amm-processi-automatici',
  {
    fetchPage: listProcessi,
    startsEmpty: false,
    // I filtri di pannello: sempre inviati quando valorizzati.
    // `vivo` e non `attivo`: il ritiro e' `obsoleto_dal`, lo decide il DB (BE12).
    filterDefaults: { classe: null, canale: null, vivo: null },
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
      // ⛔ E il QUARTO caso, che è il peggiore: presidi letti a metà. Un
      //    controllo che non si è potuto interrogare non è «zero righe», ma
      //    senza questo numero la testata resterebbe VERDE mentre non si è
      //    visto niente — cioè direbbe «tutto a posto» proprio perché è cieca.
      const presidiNonLetti = ref(0)
      // ⭐ LA TESTATA come la consegna il backend (`{totale, con_righe,
      //    non_letti}`, stessa forma di `presidi/conteggi/`): la leggono la
      //    testata del pannello e il pallino della topbar, che la ADOTTA quando
      //    il pannello ricarica. Un getter solo, o si ricompone a mano in due
      //    posti e le due copie smettono di coincidere al primo campo nuovo.
      // ⛔ `null` quando l'ultima lettura e' FALLITA: una testata a zeri qui
      //    direbbe «tutto verde» proprio mentre non si e' visto niente.
      const presidiTestata = computed(() => (
        presidiErrore.value
          ? null
          : {
              totale: presidi.value.length,
              con_righe: presidiConRighe.value,
              non_letti: presidiNonLetti.value,
            }
      ))

      async function caricaPresidi() {
        presidiLoading.value = true
        presidiErrore.value = false
        try {
          const res = await getProcessiPresidi()
          presidi.value = res.data.data.presidi
          presidiConRighe.value = res.data.data.con_righe
          presidiNonLetti.value = res.data.data.non_letti ?? 0
          // Il pallino della topbar adotta la testata appena letta.
          adottaTestataPresidi(presidiTestata.value)
        } catch {
          presidi.value = []
          presidiConRighe.value = 0
          presidiNonLetti.value = 0
          presidiErrore.value = true
        } finally {
          presidiLoading.value = false
        }
      }

      return {
        presidi, presidiConRighe, presidiNonLetti, presidiLoading, presidiErrore,
        presidiTestata, caricaPresidi,
      }
    },
  },
)
