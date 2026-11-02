// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store della LISTA DELLE RATE col saldo (`pagamenti.rate`, lista 68,
//        `GET /pagamenti/rate/`) — la sorgente del picker della distinta
//        (D19-c, 2026-09-17) e, domani, dello scadenzario.
// Note: ⭐ `createListaStore` e non `createCrudStore`: la lista non POSSIEDE le
//       rate che mostra — nascono col piano rate della fattura, e da qui si
//       SCELGONO. Un `create`/`update` che nessuno chiama sarebbe un contratto
//       che non descrive niente.
//
//       ⭐ PARTE VUOTA, ED E' IL CRITERIO OBBLIGATORIO del picker (D19-c): si sta
//       registrando il pagamento di QUESTO cliente, non guardando lo
//       scadenzario. Il cancello e' `startsEmpty` + `gateKeys`: senza cliente o
//       numero fattura la lista non chiede niente al backend, e lo DICE
//       (`app-empty-state` nel dialog). ⚠️ La ricerca libera (`search` >= 3,
//       che cerca il CLIENTE) conta come criterio da se', per il contratto di
//       `useListaEmptyStateFetch`: e' un terzo modo di arrivare al cliente,
//       non una scappatoia.
//
//       ⭐ ORDINE DI PARTENZA `data_scadenza ASC`, non DESC come le liste di
//       lettura: e' una CODA — la rata piu' vecchia e' quella che un pagamento
//       piu' probabilmente salda (stessa ragione dei residui di competenza). E'
//       l'`ordinamento_default` del preset a catalogo (68); il primo click
//       dell'operatore sull'intestazione resta DESC per la regola generale.
//
//       ⛔ `solo_aperte` e' un filtro del backend (`residuo <> 0`, Q-B di Tid):
//       nel picker NON si usa per nascondere le esaurite — quelle si vedono e
//       non si scelgono (brief §4.2) — ma e' qui perche' e' un filtro della
//       lista, e lo scadenzario lo accendera'.
//
//       ⛔ `solo_numerate` NON STA PIU' QUI, ED E' UNA DECISIONE (Tid,
//       2026-09-23): la rata di un documento NON numerato non e' un credito su
//       cui registrare un incasso — la bozza non e' ancora un documento fiscale
//       — ma quella e' una regola di DOMINIO, non un filtro dell'operatore.
//       Adesso vive nel backend (`list_rate` / `list_rate_paginata`, default
//       `True`) e il frontend non la manda piu': e' presentazione, e una regola
//       di dominio scritta qui sarebbe vera solo per il client che si ricorda
//       di dirla.
//       ⚠️ SI VEDEVA DA UN SINTOMO PICCOLO, ed e' il motivo per cui e' emersa:
//       stando in `filterDefaults` era anche una CHIAVE DI FILTRO, quindi il
//       segno dei filtri attivi del picker contava «1» — su un filtro che
//       nell'interfaccia non esisteva. *`filterDefaults` risponde a DUE
//       domande — «cosa mando al backend» e «cosa conto come filtro» — e per un
//       perimetro le due risposte divergono.*
//       ⭐ La via d'uscita resta, dalla parte giusta: chi vorra' vedere anche le
//       bozze passa `solo_numerate=false` (e allora sara' un filtro vero, con
//       il suo interruttore). ⏳ Il predicato di Tid e' piu' stretto — «solo le
//       definitive, inviate a SDI» — e arrivera' come regola di dominio in una
//       sede sola a DB: registrato nel piano D19, §8.
//
//       ⭐ NASCE A DIECI RIGHE (`USO_MISURA.COMPATTA`), non a 25: e' la
//       lista di un DIALOG, e il dialog ha l'altezza di dieci righe
//       (`app-dialog-lista`, main.css) — cosi' la pagina piena e la pagina
//       vuota sono alte uguali e il dialog non salta quando arrivano le
//       righe. `useSearchTable` tratta un limite diverso da 25 come eccezione
//       dichiarata e non lo adatta al viewport.
//       ⛔ E IL PRESET DICE LO STESSO NUMERO (`lista_preset` 68,
//       `pagina_dimensione = 10`), e non e' ridondanza: al primo
//       `config-loaded` lo scaffolding ALLINEA `filters.limit` alla
//       `pagina_dimensione` risolta dal catalogo (`useListaConfigurabilePage`),
//       e il DB la risolve sempre (`COALESCE(..., 25)`). Con il preset a 25 la
//       prima apertura mostrava 25 righe in un blocco alto dieci, e dalla
//       seconda — dopo il `reset()` alla chiusura, con l'allineamento gia'
//       fatto — dieci: due aperture, due passi, nessun errore (rilettura
//       critica del 18/09).
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { listRate } from '../api/pagamenti'
import { USO_MISURA } from '../../core/misurePagina'

export const useRateStore = createListaStore('pagamenti-rate', {
  fetchPage: listRate,
  filterDefaults: {
    billing_account_id: null,
    fattura_numero: null,
    serie: null,
    solo_aperte: null,
  },
  gateKeys: ['billing_account_id', 'fattura_numero'],
  startsEmpty: true,
  orderBy: 'data_scadenza',
  orderDir: 'asc',
  misura: USO_MISURA.COMPATTA,
})
