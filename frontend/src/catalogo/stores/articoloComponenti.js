// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della DISTINTA BASE di un articolo come lista configurabile
//        (`catalogo.articolo_componenti`, lista 101), consumata da
//        `ArticoloBomDrawer` attraverso `useDrawerTabLista`
//        (brief-db-liste-righe-documento, lotto C, 2026-09-28).
// Note: ⭐ L'articolo e' il PADRE (path), non un filtro.
//       ⭐ `valido_al` e' il filtro «in vigore al»: nasce a OGGI (si leggono
//       le versioni in vigore), `null` = «tutte le versioni». Il segno dei
//       filtri e' grigio finche' vale oggi, blu se l'operatore sceglie
//       un'altra data, spento a «tutte le versioni» (null non restringe).
//       Prima era un filtro LOCALE sulle righe gia' caricate: con la
//       paginazione avrebbe filtrato la sola pagina.
//       ⚠️ Il default e' calcolato quando lo store nasce, come il floor delle
//       altre liste (`movimenti`): il BB dei filtri congela i default alla
//       nascita, e un «oggi» ricalcolato a mezzanotte non ha ancora una sede.
//       Un drawer aperto a cavallo della mezzanotte parte dalla data di ieri
//       finche' non si ricarica la pagina.
//       ⛔ Nessun ordinamento di partenza qui: lo dichiara il preset della
//       lista (`valido_dal` DESC), e senza richiesta il backend fa lo stesso.
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { addDaysToToday, toDateString } from '../../core/utils/date'
import { listArticoloComponentiLista } from '../api/catalogo'
import { USO_MISURA } from '../../core/misurePagina'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`): due drawer vivi
//    insieme non si scrivono addosso la lista.
export const useArticoloComponentiStore = storePerIstanza('catalogo-articolo-componenti', (id) => createListaStore(id, {
  fetchPage: listArticoloComponentiLista,
  parentField: 'articoloId',
  filterDefaults: { valido_al: toDateString(addDaysToToday(0)) },
  // Dentro un drawer la lista parte piena: l'articolo c'e' gia'.
  startsEmpty: false,
  orderBy: null,
  orderDir: null,
  misura: USO_MISURA.COMPATTA,
}))
