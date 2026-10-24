# Zero ERP – Policy Ricerca e Paginazione (API/DB)

> **Ultimo aggiornamento**: 26 settembre 2026
>
> **Destinatari**: chi scrive un endpoint di lista, di ricerca o di export (backend) e chi
> lo mostra a video (frontend).
>
> **Vedi anche** — dove sta il meccanismo (i numeri e le funzioni si leggono **lì**):
>
> * [api.md](api.md) §«Paginazione» — parametri, tetti, forma della risposta, il `count` indipendente
> * [api.md](api.md) §«Ricerca e throttling» — la soglia di ricerca e `is_search_endpoint`
> * [api.md](api.md) §«Endpoint attivi», voce «UI — Export liste» — l'export CSV/XLSX
> * [catalogo BB backend](backend/catalogo-building-block-backend.md) §«Ordinamento SQL — direzione e tiebreak»
> * [API pagination (core)](../backend/core/manual/api_pagination.md) — `pagina_da_query`, l'envelope da offset e le classi DRF (non usate)
> * [frontend-standards](frontend/frontend-standards.md) — `<ListaConfigurabile>`, che consuma tutto questo

---

Questa pagina dice **quali regole valgono e perché**. I valori (tetto di pagina,
soglia di ricerca, tetto dell'export, frequenza del throttling) non si ricopiano
qui: stanno nel codice e nei documenti elencati sopra. *Un numero scritto in due
posti ne ha sempre uno stantio.*

## Il principio

Una lista a video non consegna mai «tutto»: consegna **una pagina**, filtrata e
in un ordine stabile. Chi vuole tutto usa l'**export**, che ha un canale suo e un
tetto suo. Lo scopo è che nessuna richiesta — neanche una ricerca di una lettera
— possa produrre un carico imprevedibile sulla rete, sul browser o sul database.

---

## 1) Paginazione — obbligatoria, con un tetto deciso dal server

* Ogni lista a video è paginata, in **una forma sola**: `limit`/`offset`,
  letti da `pagina_da_query` (api.md §«Paginazione»). ⛔ Dal 2026-10-21
  `page`/`page_size` in query sono un 400 su ogni lista (prima erano la seconda
  forma in uso, di una ventina di liste). La risposta conserva `page` e
  `page_size`, ricavati dall'offset.
* Il **tetto di pagina lo decide il server**, il client non lo supera.
* Il `count` della risposta è calcolato **indipendentemente** dalle righe
  consegnate, con lo stesso perimetro della lista (api.md, «Il `count` non si
  deriva MAI dalle righe»). `<ListaConfigurabile>` se ne serve per accorgersi di
  una lista troncata senza dirlo.
* La forma in uso è a **offset**: la lista configurabile mostra il totale e il
  numero di pagine, che una paginazione a cursore non sa dare. Le classi DRF
  `StandardCursorPagination` / `StandardPageNumberPagination`, che nessuna
  view usava, sono state rimosse il 2026-10-21. Se una lista avrà bisogno
  del cursore (un registro che cresce mentre lo si scorre), va deciso **per
  quella lista**, perché cambia il contratto verso il frontend.

⛔ **Fuori tetto è un 400, su ogni lista** (decisione di Tid del 2026-10-21).
`pagina_da_query` rifiuta con `E_VALIDATION_INPUT` un `limit` fuori da
1..tetto (`limit_fuori_limiti_1_<tetto>`), un `offset` negativo
(`offset_negativo`) e un valore non intero: il client che chiede 500 righe e ne
riceve 200 senza un segnale crede di averle tutte. ✅ Il debito dichiarato qui —
la riduzione silenziosa, che fino a quel giorno valeva per le liste
offset-based e, col dialetto unico, per tutte — è chiuso. Il clamp
`limiti_pagina` resta solo come difesa interna dei repository, non come
risposta all'utente.

## 2) Ordinamento — sempre deterministico

* Ogni `ORDER BY` di lista termina con uno **spareggio univoco** (`id`), nello
  stesso verso della colonna scelta: senza, due pagine consecutive possono
  ripetere una riga o perderne una. Il building block è `sql_order_clause`
  (catalogo BB backend §«Ordinamento SQL»), che applica anche la regola «le date
  si leggono dalla più recente».
* L'operatore può ordinare solo per le colonne in **whitelist**, chiavata sul
  `campo_sorgente` fisico: si ordina la colonna che si vede (api.md, «La
  whitelist di ordinamento si chiava sul `campo_sorgente` FISICO»).

## 3) Ricerca testuale

* **La forma è «contiene»**: `ILIKE '%termine%'`, in OR sulle colonne della
  lista. Non c'è una ricerca «per inizio parola» di default.
* ⛔ **Il pattern si costruisce solo con il BB `pattern_contiene`**
  (`apps/core/db/_helpers.py`), che neutralizza `%` e `_` scritti dall'utente.
  Un `f"%{termine}%"` scritto a mano non dà errore: fa da jolly e restituisce
  righe in più.
* **Un termine troppo corto non genera carico.** La soglia minima dipende da
  dove si cerca:
  * **liste configurabili**: la soglia è **della lista**, dichiarata a catalogo
    (`ui.lista_definizione.ricerca_min_caratteri`) e letta dal building block
    `add_ricerca_full_condition`. Sotto la soglia il termine **non filtra** e non
    c'è errore;
  * **ricerche dedicate e lookup** (la ricerca universale `GET /api/v1/search/`,
    i lookup): soglia di progetto `RICERCA_MIN_CARATTERI`, e sotto soglia un
    `400 E_SEARCH_VALIDATION`.
* **Throttling**: una view di ricerca o di lista si dichiara con
  `is_search_endpoint = True` e da lì la conta `SearchBurstRateThrottle`. La
  frequenza si configura con `DJANGO_API_SEARCH_THROTTLE_RATE`. Il throttle sta
  nei default DRF, ma **conta solo le view che si dichiarano**: una view senza
  il flag non ha limite.
* **Dal lato DB**: una ricerca «contiene» su una tabella che cresce la regge un
  indice trigram (`pg_trgm` + GIN). Quali colonne lo hanno si legge dalla doc
  auto-generata della tabella (per esempio
  [anagrafiche.soggetti](../dbzero/anagrafiche/tabelle/soggetti.md): ragione
  sociale, codice, identificativo fiscale). La ricerca a parole con ranking (FTS)
  non è in uso.

## 4) Export — un canale suo, mai «tutte le pagine»

* Nessun client ricostruisce un export scorrendo le pagine della lista.
* Ogni lista esportabile ha la sua rotta `…/export/?formato=csv|xlsx` accanto,
  con **lo stesso `lista_codice`** e gli stessi filtri: il file ha le colonne che
  l'operatore vede.
* L'export è **sincrono, con un tetto di righe**: sopra il tetto la risposta è
  un errore che chiede di restringere i filtri (`E_UI_EXPORT_LIMIT_EXCEEDED`),
  non un file troncato.
* L'export **asincrono** (job + download quando pronto) non esiste: è rinviato
  finché un caso non lo chiede (nota nel renderer
  `apps/ui/services/lista_export_service.py`).

## 5) Regole senza un meccanismo — dichiarate

Due regole restano valide ma **nessun codice le applica ancora**. Le scrivo
qui perché nessuno le dia per fatte.

* **Filtro temporale di default** sulle liste che crescono col tempo (fatture,
  movimenti, log): non c'è un meccanismo generico che le apra su un periodo. La
  paginazione limita la risposta, ma non il lavoro del database per contare e
  ordinare tutto lo storico.
* **Tetto sulla finestra navigabile** («oltre N righe filtra o esporta»): non
  esiste. Una pagina lontanissima si può chiedere, e il tetto c'è solo
  sull'export.
