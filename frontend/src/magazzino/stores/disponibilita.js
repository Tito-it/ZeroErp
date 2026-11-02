// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I due store della DISPONIBILITA' — per (articolo, magazzino), lista
//        `magazzino.disponibilita` su `vw_disponibilita`, e per articolo
//        (somma sui magazzini visibili), lista `magazzino.disponibilita_
//        articoli` — le due schede della vista «Disponibilita'».
// Note: ⭐ Sono DUE store e non uno con un flag: le due liste hanno colonne
//       diverse a catalogo (75 e 76), filtri diversi (il magazzino ha senso
//       solo sulla prima) e pagine indipendenti — chi cambia pagina «per
//       articolo» non deve trovarsi a pagina 3 «per magazzino».
//       ⭐ Partono PIENE e senza floor temporale: la disponibilita' e' una
//       fotografia di OGGI, non un archivio — non c'e' una data da cui partire.
//       ⚠️ `solo_negativa` / `solo_con_giacenza` nascono `null`, non `false`:
//       il core manda ogni filtro `!= null`, e un `false` sul filo sarebbe un
//       parametro che il backend legge e che non filtra niente. L'interruttore
//       scrive `true` o torna a `null`.
//       ⛔ Sola lettura per costruzione: nessun verbo, nessun evento cross-tab.
//       La disponibilita' cambia quando cambia il REGISTRO, e chi la guarda la
//       ricarica col «Ricarica» della barra.
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { listDisponibilita, listDisponibilitaArticoli } from '../api/magazzino'

// I filtri comuni alle due letture.
const FILTRI_COMUNI = {
  articolo_id: null,
  solo_negativa: null,
  solo_con_giacenza: null,
}

export const useDisponibilitaStore = createListaStore('magazzino-disponibilita', {
  fetchPage: listDisponibilita,
  startsEmpty: false,
  filterDefaults: { magazzino_id: null, ...FILTRI_COMUNI },
  // Il default del backend: articolo, poi magazzino. Non si dichiara qui, cosi'
  // la lista si apre com'e' e il primo click su una colonna e' il primo.
  orderDir: null,
})

export const useDisponibilitaArticoliStore = createListaStore('magazzino-disponibilita-articoli', {
  fetchPage: listDisponibilitaArticoli,
  startsEmpty: false,
  filterDefaults: { ...FILTRI_COMUNI },
  orderDir: null,
})
