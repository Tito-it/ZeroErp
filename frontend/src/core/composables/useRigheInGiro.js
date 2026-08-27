// Copyright (C) 2026 Michele Carlo Titini
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// Scopo: sapere QUALI RIGHE di una lista sono dentro un giro asincrono ancora
//        vivo, per poterle marcare a video e tenerle fuori dalla selezione.
//
// Serve dove il verbo ACCODA un job e la riga resta a video: senza un segno, la
// lista resta identica per tutta la durata del giro — spunta compresa — e
// l'operatore ri-sottomette lo stesso lavoro credendo che il primo non sia
// partito.
//
// ⚠️ SI USA QUANDO LA RIGA NON SA DA SÉ DI ESSERE IN LAVORAZIONE. Se la riga è
//    essa stessa il lavoro (le liste di `dbops.coda_lavori` /
//    `vendite.fatture_stampa_coda`), lo stato è NEL DATO e questo composable
//    non serve: là si legge `rigaCodaViva(row.stato)`, che è più forte perché
//    sopravvive a un ricarico di pagina e vede anche i giri di altri operatori.
//    Qui si ricorda ciò che ha lanciato QUESTA scheda, e solo finché è aperta.
//
// ⛔ DUE TRAPPOLE, ed è il motivo per cui questo non è un `Set` e basta.
//
// 1. **La mappa è per GIRO, non un insieme piatto.** Con più giri in volo, la
//    conclusione del primo deve togliere le marcature SOLO sue: un insieme
//    unico si potrebbe unire all'avvio ma non sottrarre selettivamente alla
//    fine, e il secondo giro resterebbe senza segno mentre è ancora vivo.
//
// 2. **La mappa si SOSTITUISCE, mai si muta in place.** Un `.set`/`.delete`
//    sull'istanza dentro il ref non cambia l'identità dell'oggetto: Vue non
//    riesegue i computed che ne dipendono, e le righe restano senza rotellina
//    con lo stato interno già avanti. È un difetto silenzioso — nessun errore,
//    solo una cosa che non compare.
//
// Uso:
//   const { chiaviInGiro, marca, smarca, inGiro } = useRigheInGiro()
//   marca(res.job_id, chiaviDelGiro)     // dopo l'accodamento
//   smarca(context.jobId)                // in onDone / onTimeout
//   // template: v-if="inGiro(data.gruppo_key)"
//
// ⚠️ `smarca` va chiamata anche su TIMEOUT e su ERRORE, non solo sul successo:
//    una riga marcata da un giro che non si conclude resta con la rotellina per
//    sempre e fuori dalla selezione — cioè non più lavorabile.

import { computed, ref } from 'vue'

export function useRigheInGiro() {
  // jobId → chiave[] delle righe di QUEL giro.
  const perGiro = ref(new Map())

  // Scopo: marca le righe di un giro appena accodato.
  function marca(jobId, chiavi) {
    const mappa = new Map(perGiro.value)
    mappa.set(jobId, chiavi)
    perGiro.value = mappa
  }

  // Scopo: toglie le marcature del solo giro indicato. Idempotente.
  function smarca(jobId) {
    if (!perGiro.value.has(jobId)) return
    const mappa = new Map(perGiro.value)
    mappa.delete(jobId)
    perGiro.value = mappa
  }

  // Scopo: azzera tutto (reset di contesto, cambio perimetro).
  function azzera() {
    if (perGiro.value.size === 0) return
    perGiro.value = new Map()
  }

  // Vista piatta per il template e per i predicati: chi la usa non sa che
  // sotto c'è una mappa per giro.
  const chiaviInGiro = computed(() => {
    const piatto = new Set()
    for (const chiavi of perGiro.value.values()) {
      for (const chiave of chiavi) piatto.add(chiave)
    }
    return piatto
  })

  // Scopo: questa riga è dentro un giro vivo?
  function inGiro(chiave) {
    return chiaviInGiro.value.has(chiave)
  }

  // ⚠️ `perGiro` NON si espone di proposito: e' la mappa che la trappola 2 qui
  //    sopra vieta di mutare in place, e un riferimento in mano al chiamante e'
  //    l'invito a farlo. Fuori escono la vista piatta e i tre comandi.
  return { chiaviInGiro, inGiro, marca, smarca, azzera }
}
