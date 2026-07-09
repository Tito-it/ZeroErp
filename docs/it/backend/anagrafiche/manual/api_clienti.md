# API Clienti

> Dominio: `anagrafiche` · Base view: `DomainAPIView` (`area_funzionale = "anagrafiche"`)
> Codice: `apps/anagrafiche/api/views_clienti.py` · Service: `apps/anagrafiche/services/clienti_service.py`

## Scopo

Gestione dei **clienti** (pricing v5 STADIO 2). Un cliente è la catena
**istanza utility → billing account (BA) → cliente**: il BA è il ponte commerciale
(categoria cliente, fatturazione, valuta), il cliente porta i parametri operativi
(pagamento, PA/split, garanzia, servizio da fatturare). La creazione compone l'intera
catena in **una transazione atomica**; l'aggiornamento è delegato a una **funzione madre
DB** atomica.

Glossario: **cliente = billing_account** (mai "soggetto": il soggetto anagrafico è
un'altra entità, legata via `soggetti_ruoli`).

## Endpoint

| Metodo | Path | Azione |
| --- | --- | --- |
| `GET` | `/api/v1/anagrafiche/clienti/` | Lista paginata (search + filtri, scope emittente) |
| `POST` | `/api/v1/anagrafiche/clienti/` | Crea cliente completo (istanza + BA + cliente) |
| `GET` | `/api/v1/anagrafiche/clienti/{id}/` | Dettaglio completo |
| `PATCH` | `/api/v1/anagrafiche/clienti/{id}/` | Aggiorna campi editabili + categoria BA |
| `GET` | `/api/v1/anagrafiche/clienti/export/?formato=csv\|xlsx` | Export lista (DEF-1) |
| `GET` | `/api/v1/anagrafiche/utilities/manual-lookup/` | Utility ammesse per creazione manuale |

> Gli endpoint di invito/accesso portale e shop
> (`/{id}/invita-portale/`, `/{id}/invita-shop/`, `/{id}/stato-accessi/`,
> `/{id}/disattiva-portale/`, `/{id}/disattiva-shop/`) sono documentati in
> [api_invito_portale_shop.md](/backend/core/manual/api_invito_portale_shop). La **categoria
> cliente** (lookup per il pricing) è in [api_categorie_clienti.md](/backend/anagrafiche/manual/api_categorie_clienti).

---

## Lista — `GET /clienti/`

Endpoint di ricerca (`is_search_endpoint = True`, throttling). Paginazione offset-based
via `parse_list_params`.

| Query param | Tipo | Note |
| --- | --- | --- |
| `search` | str | ILIKE su ragione sociale / CF / P.IVA / codice BA / codice soggetto (min 3 char) |
| `utility_id` | int | Filtra per utility |
| `stato_cliente_id` | int | Filtra per stato cliente |
| `limit`/`offset`/`order_by`/`order_dir` | — | Paginazione/ordinamento standard |

**Scope emittente (RLS).** La lista restituisce solo i clienti i cui BA appartengono agli
emittenti fiscali autorizzati per l'operatore (`PermissionResolver.get_emittenti_sr_ids`
→ filtro applicativo su `emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id`,
con fallback gestore globale `is_default`). Difesa-in-profondità sommata alla RLS DB.

Risposta: envelope paginato standard (`count`, `page`, `page_size`, `total_pages`, `results`).

---

## Creazione — `POST /clienti/`

Compone la catena **istanza → BA → cliente** in **una `transaction.atomic()`** (via
`crea_cliente`). Se un qualsiasi step fallisce, nulla viene committato (no orfani).

**Payload**

| Campo | Obblig. | Note |
| --- | --- | --- |
| `soggetto_id` | ✅ | UUID del soggetto (ruolo CLIENTE get-or-create) |
| `utility_id` | ✅ | Utility del cliente; per creazione manuale deve avere `richiede_pdp = false` |
| `ba_categoria_cliente_id` | ✅¹ | Categoria cliente sul BA. Obbligatoria quando si crea un **nuovo** BA (nessun default implicito) |
| `istanza_utility_id` | — | Istanza pre-esistente (flusso pratiche); se assente ne crea una fittizia |
| `billing_account_id` | — | BA pre-esistente da riusare; se assente lo crea |
| `indirizzo_dettaglio_id`, `ba_fatturazione_ordini`, `ba_parent_account_id` | — | Dati istanza/BA opzionali |
| `termine_pagamento_id`, `modalita_pagamento_id`, `iva_id`² | — | Parametri pagamento |
| `tipo_gg_scadenza_ft`, `nr_giorni_scadenza`³ | — | Scadenza fattura (coppia vincolata, vedi sotto) |
| `cliente_pa`, `split_payment`, `codice_cig`, `codice_cup`, `codice_commessa` | — | PA / commessa |
| `servizio_da_fatturare`, `garanzia_tipo`, `garanzia_importo` | — | Servizio / garanzia |
| `contatto`, `indirizzi` | — | Contatto + indirizzi ruolo inline (opzionali, da drawer) |

¹ Solo se `billing_account_id` è assente (BA nuovo). Se il BA è pre-esistente la categoria
è già sul BA e il valore qui è ignorato.
² `iva_id` è NOT NULL: se non fornito è risolto dal default DB (`DEFAULT_IVA_ID`).
³ Vedi **Coppia scadenza** in fondo.

**Errori**

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `soggetto_id`/`utility_id`/`ba_categoria_cliente_id` mancanti; utility con PDP in creazione manuale |
| `E_ANAG_NOT_FOUND` | 404 | `istanza_utility_id`/`billing_account_id` pre-esistenti non trovati |
| `E_BA_ADMIN_GLOBALE_VIETATO` | 403 | Admin globale che crea BA con emittenti fiscali presenti (operare come operatore di un emittente) |
| `E_ANAG_DUPLICATO` | 409 | Esiste già un cliente per l'istanza (`uq_clienti_istanza_utility`) |

Risposta `200`: `{ id, istanza_utility_id, billing_account_id, soggetto_ruolo_id }`.

---

## Dettaglio — `GET /clienti/{id}/`

Dettaglio completo: campi cliente + BA (`ba_codice`, `ba_categoria_cliente_id`/codice/
descrizione, `ba_fatturazione_ordini`, `ba_parent_account_id`, validità), istanza,
soggetto (ragione sociale, CF, P.IVA), descrizioni FK (utility, stato, iva, modalità/
termine pagamento) e **stato-evento corrente** (`data_evento_stato`, `tipo_evento_stato`)
risolto data-driven dalla fn DB. `404 E_ANAG_NOT_FOUND` se inesistente o **fuori scope**
emittente (identico a inesistente, fail-closed RLS).

---

## Aggiornamento — `PATCH /clienti/{id}/`

Aggiorna i campi editabili del cliente e/o la categoria cliente sul BA. Delega diretta al
service (no `handle_post_json`, vedi api.md §PATCH).

**Semantica transazionale (fix analisi-fix-transazioni #1, 2026-07-08).** La categoria vive
sul BA, i campi editabili sul cliente: le **due scritture** sono fuse in **un'unica**
`SELECT anagrafiche.fn_update_cliente(...)` (funzione madre, `SECURITY INVOKER`), atomica
per costruzione. Prima erano due UPDATE separati in autocommit → il fallimento del secondo
lasciava la categoria BA committata su uno stato parziale.

**Campi editabili** (delta: solo le chiavi presenti vengono scritte; chiave presente con
valore vuoto/`null` → campo azzerato dove nullable):
`iva_id`, `modalita_pagamento_id`, `termine_pagamento_id`, `tipo_gg_scadenza_ft`,
`nr_giorni_scadenza`, `cliente_pa`, `split_payment`, `codice_cig`, `codice_cup`,
`codice_commessa`, `servizio_da_fatturare`, `garanzia_tipo`, `garanzia_importo`, più
`ba_categoria_cliente_id` (scritto sul BA). Le stringhe vuote sono **normalizzate a NULL**
lato BE per i campi che lo ammettono.

**Errori**

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Cliente inesistente o fuori scope emittente |
| `E_ANAG_VALIDAZIONE` | 400 | `ba_categoria_cliente_id` non intero positivo; **oppure nessun campo valido da aggiornare** (il cliente esiste → validazione, non not-found)⁴ |

⁴ Contratto aggiornato il 2026-07-08 (review): il caso "niente da aggiornare" era `404
E_ANAG_NOT_FOUND`; poiché l'esistenza è già garantita dal guard, ora è `400
E_ANAG_VALIDAZIONE`.

Risposta `200`: `{ "updated": true }`.

---

## Utility per creazione manuale — `GET /utilities/manual-lookup/`

Elenco delle utility ammesse per la creazione manuale del cliente (`richiede_pdp = false`,
attive). Risposta: `{ "results": [ { id, codice, descrizione } ] }`. Le utility con PDP
richiedono il **motore pratiche**, non la creazione manuale.

## Export — `GET /clienti/export/?formato=csv|xlsx`

Export della lista (DEF-1) che rispetta ordine/visibilità/permessi colonne della
configurazione lista utente + i filtri applicati (search/utility/stato tradotti in
etichette leggibili). Hard cap 10.000 righe. Vedi [api_soggetti.md](/backend/anagrafiche/manual/api_soggetti)
per il pattern export condiviso.

---

## Note di dominio

- **Coppia scadenza `tipo_gg_scadenza_ft` / `nr_giorni_scadenza`.** Vincolata dal trigger
  `anagrafiche.trgfn_clienti_normalize_giorni_scadenza`: combinazioni valide `('G', >0)`,
  `('F', >0)`, `('N', NULL)`, `('M', NULL)`. Con `tipo NOT IN ('G','F')` il DB **forza**
  `nr_giorni_scadenza = NULL`; con `tipo IN ('G','F')` e `nr_giorni` NULL/≤0 solleva
  `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`. Impostare la coppia insieme.
- **Categoria cliente** = dimensione commerciale del pricing, vive sul BA
  (`billing_account.categoria_cliente_id`, NOT NULL). Non ha default implicito in creazione.
- **Stati cliente** (`config.stati_cliente`): il cliente nasce ATTIVO; sospensione/
  riattivazione/chiusura sono eventi data-driven (`fn_get_evento_stato_corrente_cliente`).
