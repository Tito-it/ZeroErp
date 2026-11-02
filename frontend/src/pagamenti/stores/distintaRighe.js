// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista RIGHE DI UNA DISTINTA CONTABILE
//        (`pagamenti.distinta_righe`, lista 69), consumata dal drawer della
//        distinta attraverso `useDrawerTabLista`.
//
// PERCHE' ESISTE (2026-09-18, rilievo in-app di Tid). Il drawer teneva le
// righe dentro il dettaglio (`dettaglio.righe`) e le disegnava con una
// `DataTable` grezza: la lista non paginava, non si ricaricava da sola, non si
// potevano scegliere le colonne e non si poteva scaricare niente — nessuna
// delle caratteristiche di una lista standard. La ragione scritta era «sono le
// righe di un documento», ma le righe contabili hanno endpoint propri, una
// macchina a stati propria e una coda propria (`pagamenti.righe`): sono
// un'entita' con vita propria, cioe' la prima domanda del criterio in tre
// domande (piano PrimeVue 5 §Gruppo B), come i titoli IVA il 02/09.
//
// ⭐ NON E' SCRITTO A MANO. Il corpo — filtri, fetch paginata, cancello
//    empty-state, sospensione, reset, e la distinzione fra «vuota» e «non
//    letta» — vive in `useListaStoreCore`, chiamato qui dentro il `defineStore`
//    (la forma ammessa da frontend-standards quando lo store ha stato SUO):
//    restano quale endpoint, come si chiama il padre, come si legge, e
//    l'interruttore delle scartate.
//
// ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI: `contabileId` e' il contesto
//    (arriva dal path dell'endpoint), i filtri sono le scelte dell'operatore —
//    e al cambio padre i secondi si azzerano mentre il primo si riscrive.
//
// ⛔ NESSUN `orderBy` di partenza, ed e' voluto: senza indicazioni il backend
//    ordina `id DESC`, cioe' l'ULTIMA RIGA DIGITATA IN CIMA — la scelta di Tid
//    del 02/09 sugli atti di sistemazione, per la stessa ragione: da quando la
//    lista impagina, una riga appena scritta in ordine crescente finirebbe
//    nell'ultima pagina e chi l'ha appena digitata non la vedrebbe. Scrivere
//    qui una colonna cambierebbe l'ordine di apertura senza che nessuno
//    l'abbia chiesto, e lo farebbe divergere dal default del backend.
//
// ⭐ «MOSTRA SCARTATE (N)» (D20-c, 2026-09-19): la riga SCARTATA — «non e'
//    nostra» — resta nella distinta e nella quadratura ma esce dal lavoro:
//    nascosta di DEFAULT, e il backend dichiara quante ne nasconde
//    (`scartate_count`, la forma di `archiviate_count`). Il filtro e'
//    `scartate: null | true` — `null` e non `false`, perche' il core manda ogni
//    filtro `!= null` e un `false` sul filo sarebbe un parametro letto per
//    niente (regola di `bindToggle`). L'export segue la lista: `paramsFiltro`
//    lo porta come ogni altro filtro.
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { listRigheDistinta } from '../api/pagamenti'
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useDistintaRigheStore = storePerIstanza('pagamenti-distinta-righe', (id) => defineStore(id,
  () => {
    // Quante scartate il perimetro corrente sta NASCONDENDO. A interruttore
    // acceso vale 0: non c'e' niente di nascosto.
    const scartateCount = ref(0)

    const base = useListaStoreCore({
      fetchPage: listRigheDistinta,
      parentField: 'contabileId',
      // La distinta e' gia' scelta quando il drawer si apre: non e' una lista
      // che parte vuota in attesa di una ricerca.
      startsEmpty: false,
      orderDir: null,
      filterDefaults: { scartate: null },
      // ⛔ `true` NON RESTRINGE, e va dichiarato (2026-09-23): acceso,
      //    l'interruttore CHIEDE le scartate, cioe' apre l'elenco a tutte le
      //    righe della distinta. Senza questa riga il segno contava un filtro
      //    attivo proprio nello stato piu' largo — lo stesso verso sbagliato di
      //    «mostra archiviate» sulle code e di «mostra annullati» sui lotti.
      filtriNeutri: { scartate: true },
      onPayload: (payload) => { scartateCount.value = payload.scartate_count ?? 0 },
    })

    // ⚠️ Il reset del core non conosce lo stato di dominio: al cambio di
    //    distinta il numero delle scartate di quella prima non deve restare a
    //    video sotto la prossima.
    function reset() {
      base.reset()
      scartateCount.value = 0
    }

    return { ...base, reset, scartateCount }
  },
  { userScoped: true },
))
