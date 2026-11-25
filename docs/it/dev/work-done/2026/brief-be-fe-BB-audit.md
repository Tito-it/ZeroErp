# Brief BE/FE — Audit dei building block: i BB che fanno la stessa cosa

## ⏭️ Chi riparte — aggiornato al 2026-11-25

**Chiuso e archiviato il 2026-11-25.** Riparte nessuno: tutto il lavoro BE/FE è fatto e committato. L'unico seguito, la richiesta al team DB (E1-6), vive in [brief-db-emittente-del-super-admin](../../work-in-progress/brief-db-emittente-del-super-admin.md). La suite intera prima dell'archiviazione la lancia Tid.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team BE/FE | ✅ Audit del backend (2026-11-24) | §1 | — |
| 2 | team BE/FE | ✅ Audit del frontend (2026-11-24) | §7 | — |
| 3 | Tid | ✅ Decisioni D-1…D-6 prese il 2026-11-24: D-4 per prima (sì a F-1…F-4), poi D-1, D-2, D-3, D-5, D-6 secondo le raccomandazioni | §8 | — |
| 3-bis | team BE/FE | ✅ Lavoro F (2026-11-24): F-1…F-4, catalogo FE, E-3 ed E-4 guardati | §7.7 | — |
| 3-quater | Tid | ✅ Collaudo a video del giro F (2026-11-24): tutto ok | §7.8 | — |
| 3-ter | team BE/FE | ✅ Prova a mano dei filtri vuoti sul server (2026-11-24): 200 sui filtri vuoti, 400 col nome del parametro su quelli sbagliati | §2.4 | — |
| 4 | team BE/FE | ✅ Catalogo BE (2026-11-24): voci vecchie ritirate, righe doppie fuse, indice rigenerato | §5 | — |
| 5 | team BE/FE | ✅ Lavoro A (2026-11-24): query string e header ai `qp_*`, funzioni del corpo che delegano a `PayloadValidator`, service sul validator del dominio; il FE non aveva niente da correggere | §2.3 | — |
| 6 | team BE/FE | ✅ Lavoro B (2026-11-24): `pagina_con_totale`, forma lunga e copie ritirate, `offset_effettivo` sui cruscotti, presidio | §3.3 | — |
| 7 | team BE/FE | ✅ Lavoro C (2026-11-24): `TemplateService` legge lo scope da `_scope`, la copia è ritirata | §4 | — |
| 8 | team BE/FE | ✅ E-2 (2026-11-24, BB `lista_paginata` nel core, copie ritirate). ✅ E-1 (2026-11-25): E1-1…E1-5 fatti e rivisti (§6.3-6.6); E1-6 passa al team DB nel suo brief | §6 | — |
| 10 | team BE/FE | ✅ D-3 (2026-11-24): `validate_order_params_ricerca`, call-site, test e catalogo | §5 | — |
| 11 | team BE/FE | ✅ D-5 (2026-11-24): `livelloAccessoSeverity` in `severity.js`, LETTURA arancio, le due copie ritirate | §7.10 | — |
| 11-bis | Tid | ✅ Collaudo a video del giro B–C–D (2026-11-24): tutto ok | §3.4 | — |
| 12 | team BE/FE | ✅ D-6 (2026-11-24, alla revisione): il motivo dei 300 ms in `useServerAutocomplete` e nella sua voce di catalogo; il polling in background dichiarato voluto nella voce di `useJobPolling` | §7.9 | — |
| 13 | team BE/FE | ✅ Revisione del giro A e del giro F (2026-11-24): quattro difetti corretti | §2.5, §7.9 | — |
| 9 | team BE/FE | ✅ Archiviazione in `work-done/` (2026-11-25) | — | — |

**Decisioni aperte di Tid:** nessuna. Le tre proposte dell'audit del backend sono accettate (Tid,
2026-11-24): A, B, e la pulizia del catalogo; lo stesso giorno D-4 (F-1…F-4) e poi D-1, D-2, D-3,
D-5, D-6, tutte secondo la raccomandazione di §8.
**Da committare:** niente. A, il catalogo BE, F e le revisioni sono nel commit `9e25fe7fa`; il giro
B–C–D (§3.3–3.5, §4, §5, §7.10) nel `b179d1bce`; E-2, E1-1…E1-5 e la `/verifica` (§6.1-6.6) nel
`9511ed0f6`.

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-11-24. **A chi:** team BE/FE e Tid.
> **Origine:** la domanda di Tid «chi mi dice che i building block stessi non siano stati doppiati?».
> La regola del 2 confronta il codice nuovo col catalogo, mai un BB con un altro BB, e il
> pre-commit (`gen_indice_bb.py --check`) controlla solo che l'indice sia allineato al catalogo.
> **Brief vicini verificati:** nessuno copre il tema.
> [piano-migrazione-primevue-5](../../work-in-progress/piano-migrazione-primevue-5.md) nomina `paginated_envelope` e
> `parse_list_params` solo come BB già esistenti; i brief di `work-in-progress/` non toccano
> `optional_*`, `risposta_paginata` né `envelope_da_offset`.
> **Guide verificate** (`scripts/guide_coinvolte.py` sui sette file toccati): le 45 guide e le 12
> note di dominio trovate nascono dagli oggetti DB che quei moduli condivisi nominano. Il lavoro
> non cambia nessun oggetto DB e nessuna regola di dominio: cambia il trasporto in Python. Due sono
> pertinenti (giro A). Per il giro B–C–D (2026-11-24) lo script sul diff restituisce le guide degli
> endpoint toccati: nessuna descrive la forma dell'envelope di una lista (`configurazione-liste`
> compresa), quindi **coerenti**; per C vedi §4. Due sono pertinenti al giro A:
> [Messaggi-di-Errore-e-Generazione-Log](../../../guide/Messaggi-di-Errore-e-Generazione-Log.md) è
> **coerente**: chiede che un dato errato esca col suo campo (`DATO_ERRATO`, «il nome del campo si
> dichiara»), e il lavoro A ci porta le letture che oggi non lo danno.
> [configurazione-liste](../../../guide/configurazione-liste.md) è **coerente**: non descrive la forma
> dell'envelope. Le altre guide non sono toccate.

## 1. L'audit del backend (2026-11-24)

**Metodo.** L'indice del catalogo letto per intero (595 voci) e raggruppato per argomento: lettura
dei parametri, paginazione, ordinamento, errori del DB, scope emittente, formattazione, ricerca.
Dove le voci si somigliavano si sono aperti il catalogo e il codice. **Limite:** le voci non sono
state confrontate tutte a coppie, ma solo dentro i gruppi.

**Esito.** Tre doppioni nel codice (§2, §3, §4), quattro voci doppie nel catalogo (§5), due punti
da chiarire (§6). I falsi allarmi, verificati e distinti, si scrivono qui perché non si rifaccia la
stessa strada:

* `map_integrity_error`, `create_with_constraint_mapping`, `rifiuto_integrita` e
  `listini_service._translate_integrity_error` condividono il riconoscimento del vincolo
  (`vincolo_violato`). È la decisione su cosa fare che cambia, ed è voluto.
* `_prefisso_like` (dbops) delega a `escape_ilike`.
* `format_date_it` / `format_date_iso` (documenti) hanno un contratto diverso da
  `locale_formatters.format_date`: un valore assente resta `None`. Usano lo stesso `in_ora_locale`.
* `fetch_paged_with_total` (pagina chiesta) e `query_paged_view` (pagina effettiva) hanno due
  semantiche dichiarate.

## 2. Lavoro A — I campi opzionali del corpo: due famiglie, risposte diverse

### 2.1 Il fatto

Le funzioni della view in
[payload_validators.py](../../../../../backend/apps/core/api/payload_validators.py) (`optional_int`,
`optional_iso_date`, `optional_uuid`) e i metodi di `PayloadValidator` in
[payload_helpers.py](../../../../../backend/apps/core/services/payload_helpers.py) (`optional_uuid`,
`optional_date`, `optional_positive_int`…) rispondono alla stessa domanda. Allo stesso input
danno risposte diverse (codice letto il 2026-11-24):

| Input | Funzione della view | Metodo di `PayloadValidator` |
| --- | --- | --- |
| uuid `""`, `0`, `"0"` | `None` | 400 |
| data `""` | `None` | 400 |
| data `" 2026-01-01"` | 400 (niente `strip`) | accettata |
| errore | `ValueError` → `E_VALIDATION_INPUT` **senza il campo** | codice del dominio, **col campo** |

Dal 2026-10-20 `optional_bool` delega già a `PayloadValidator`. Per le altre tre la delega non è
stata fatta.

**Le usano anche i service**, dove il codice d'errore dovrebbe essere quello del dominio
(fatto datato, 2026-11-24):

* anagrafiche: `geo_service`, `soggetti_service`, `clienti_service`, `emittenti_fiscali_service`,
  `conti_bancari_service`, `contatti_service`, e `_validators.extract_optional_fields`. Lì un
  rifiuto esce come `E_VALIDATION_INPUT` e non come `E_ANAG_VALIDAZIONE`;
* `ui/services/lista_colonna_admin_service.py`, `amm_software/services/amm_software_service.py`.

### 2.2 Il piano

* **A1 — Una regola sola.** `optional_int`, `optional_iso_date` e `optional_uuid` della view
  delegano a `PayloadValidator(validation_code=E_VALIDATION_INPUT)`, come `optional_bool`.
  ⚠️ `optional_int` non ha un gemello esatto: accetta lo zero e ha `zero_as_none`. Prima si scrive
  la tabella della sua semantica. Se nessun metodo la copre, si aggiunge il metodo a
  `PayloadValidator`, e la funzione della view delega a quello: mai due regole.
  ⚠️ Anche `optional_istante` è nella stessa famiglia: si verifica se ha un gemello e si tratta
  allo stesso modo.
* **A2 — Cambio di comportamento, dichiarato.** Con la delega `""` su un uuid o su una data
  diventa un **400 col campo**, e così `0`/`"0"` su un uuid. Il commento attuale parla di
  «compatibilità input legacy/UI»: prima di attivare la delega lo dice A4. Il lavoro non tiene
  il ripiego.
* **A3 — I service lasciano le funzioni della view.** I service elencati in §2.1 leggono col
  proprio `PayloadValidator` (in anagrafiche `E_ANAG_VALIDAZIONE`). `extract_optional_fields` si
  riscrive sopra il `PayloadValidator` del dominio, oppure si ritira se le sue chiamate diventano
  `campi_per_presenza` / `campi_del_gesto`. Si decide leggendo i chiamanti.
* **A4 — FE.** Si cercano i form che mandano `""` o `0` per un campo uuid o data opzionale (le
  rotte delle view di §2.1, a partire da pratiche, vendite, preventivi e anagrafiche), e si
  correggono perché mandino `null`. Si fa nello stesso giro di A2, prima del push BE.
* **A5 — Presidio.** Un test di tabella per ogni funzione della view: per ogni input di §2.1, la
  stessa risposta del metodo di `PayloadValidator`. In più un test per ogni punto che traduce
  (`feedback_bb_legge_non_trasporta`). Un presidio che rifiuta `from apps.core.api.payload_validators
  import optional_*` sotto `*/services/`.
* **Catalogo:** le voci L84 (funzioni della view) e L381 (`PayloadValidator`) dicono che una
  delega all'altra; nelle voci dei service di anagrafiche si toglie il rimando alle funzioni della
  view.

### 2.3 Il giro del 2026-11-24 (team BE/FE)

* **Un caso che §2.1 non aveva visto: le funzioni del corpo leggevano la query string e un header.**
  44 letture della forma `optional_int({"v": qp.get("utility_id")}, "v")` (pratiche, anagrafiche,
  vendite, preventivi, form defaults, amm-software, email, lookup, l'audit dei permessi) e
  l'`X-Request-ID` del middleware. Due difetti già vivi: l'errore diceva `v_invalid` al posto del
  parametro, e `?utility_id=` era un 400 invece di «nessun filtro» (api.md §Query params: il vuoto è
  l'assente). Portate tutte ai BB `qp_*` (`qp_int_optional(…, min_val=0)`, che tiene l'insieme dei
  valori accettati di prima, ma con il tetto bigint; `qp_iso_date_optional`; `qp_uuid_optional` per
  l'header). Era il prerequisito di A1: con la regola rigida, una data di filtro vuota sarebbe
  diventata un 400.
* **A1 ✅** — `PayloadValidator.optional_int` è nuovo, e condivide con `optional_smallint` la
  coercizione `_coerce_int_in_range`. Le quattro funzioni della view delegano a un validator
  `_CORPO` (`E_VALIDATION_INPUT`). Decisioni del giro:
  * un intero in stringa ora può essere **negativo**, come lo era già un intero JSON (`-3` passava,
    `"-3"` no). Il tetto è bigint: oltre era un 500;
  * **difetto trovato nel BB del core**: `_SIGNED_INT_RE` usava `\d`, che in Python accetta ogni
    cifra Unicode, e `"٣"` passava come 3 da `optional_smallint`. Ora è `[0-9]`: la funzione della
    view lo rifiutava già, e il test esistente lo ha fatto vedere;
  * `optional_istante` non ha gemelli né copie: resta della view.
* **A2 ✅** — Il cambio di comportamento è attivo: `""` su data e uuid, `0`/`"0"` su uuid sono un 400
  col campo.
* **A3 ✅** — I service non importano più le funzioni della view: `soggetti`, `clienti`, `fornitori`,
  `emittenti_fiscali`, `conti_bancari`, `titoli_iva`, `geo`, `contatti` e `_validators`
  (`extract_optional_fields`) col loro `E_ANAG_VALIDAZIONE`, `amm_software_service` col suo, e la
  data di competenza di `commesse_service` (`fn_list_commessa_attivita`) col validator di vendite.
  Un `null` esplicito su un flag dei conti bancari resta `False`, come prima.
  ⚠️ **Fuori dal giro:** `ui/services/lista_colonna_admin_service.py` ha modifiche non committate di
  un'altra sessione, e non è stato toccato. Non importa le funzioni della view, quindi il presidio
  è verde. `vendite/db/pipeline_repository.py` e `pipeline_step_executor.py` leggono con
  `optional_bool` i parametri JSON di un task, che hanno già la regola del corpo.
* **A4 ✅, niente da correggere** — Il FE non manda `""` né `0` per i campi uuid e data del corpo
  (`soggetto_id`, `lock_batch_id`, `competenza_mese`, `data_attivita`, `data_documento`,
  `qualifica_scadenza`, `data` del reso): le date passano da `toDateString`/`toMeseString`, che per
  il vuoto danno `null`. È una ricerca sul sorgente, non una prova a video.
* **A5 ✅** — `core/tests/api/test_optional_int.py` riscritto: valori, cifre non ASCII, rifiuti col
  campo, la tabella «la funzione della view risponde come il metodo» per int, data e uuid, e il
  presidio che nessun file sotto `*/services/` importi `optional_int`/`optional_iso_date`/`optional_uuid`.
* **Documentazione ✅** — api.md §Validazione parametri (la regola sola, e il divieto di avvolgere la
  query string) e §Query params (i token booleani: la riga elencava ancora `1/yes/on`, ritirati il
  2026-10-20); catalogo: funzioni della view, `qp_uuid_optional`, `PayloadValidator.optional_int`,
  `extract_optional_fields`.
* **Prove:** i test toccati sono verdi (167); la suite intera è in §2.4.

### 2.4 Prove (2026-11-24)

⚠️ La suite di questa sezione è quella del giro A. Dopo la revisione (§2.5) è stata rilanciata.

* Suite BE intera (`./manage-test.sh --parallel 4`): **6794 test, OK** (341 saltati, 1 expected
  failure). La suite gira sul working tree, che porta anche le modifiche non committate di
  un'altra sessione.
* ✅ `kill -HUP` sul master di gunicorn (2026-11-24, 19:22): tre worker nuovi, servizio vivo.
* ✅ **Prova a mano sul server** (2026-11-24, dopo l'HUP), con `dev.smoke` e la password di
  `backend/env.sh` (`SMOKE_USER`/`SMOKE_PASSWORD`, letta dal file e mai stampata), login da
  `_smoke_auth.sh`:

  | Chiamata | Esito |
  | --- | --- |
  | `GET /api/v1/anagrafiche/clienti/?utility_id=` | **200**, senza filtro |
  | `GET /api/v1/anagrafiche/clienti/?utility_id=abc` | **400** `E_VALIDATION_INPUT`, `utility_id_invalid` |
  | `GET /api/v1/vendite/preventivi/?data_da=` | **200**, senza filtro |
  | `GET /api/v1/vendite/preventivi/?data_da=ieri` | **400** `E_VALIDATION_INPUT`, `data_da_invalid` |

  L'errore nomina il parametro, non più `v`. Il primo tentativo di Tid era un 401: in
  `SMOKE_PASSWORD` era rimasto il segnaposto `'…'`, quindi quel 401 non diceva niente della modifica.
  ⚠️ Per chi riprova: `_smoke_auth.sh` legge la password dal **primo argomento** dello script che
  lo include, prima di `SMOKE_PASSWORD`. Un'opzione passata come primo argomento (per esempio
  `--senza-prompt`) diventa la password e dà 401.

### 2.5 La revisione del giro A (2026-11-24)

* ⚠️ **Corregge §2.3**, dove diceva che `qp_int_optional(…, min_val=0)` «tiene l'insieme dei valori
  accettati di prima». Non era vero: `qp_int_optional` e `qp_int_strict` leggevano con `int()`, che
  accetta anche `"+3"`, `"1_000"` e `"٣"`, e le 44 letture portate lì li accettavano. Ora la forma
  è una sola per corpo e query string: `SIGNED_INT_RE` di `payload_helpers` (cifre ASCII, segno
  meno facoltativo), resa pubblica. Lo stesso difetto stava in `_coerce_positive_int`
  (`isdecimal`, che ammette `"٣"`) e nella copia locale `_INT_RE` di `core/api/views_parameters.py`
  (ancora con `\d`): la prima usa ora la regex senza segno, la seconda è ritirata a favore del BB.
  Test: `test_qp_int_optional` (forme rifiutate) e `test_payload_helpers` (19c), provati per
  mutazione.
* **`competenza_mese` della lista attività di una commessa** (vista e export) era l'unico
  avvolgimento rimasto, contro la regola appena scritta in api.md: la view passava il testo e il
  service lo avvolgeva in un dizionario per il lettore del corpo (`?competenza_mese=%20` era un
  400). Ora la legge la view con `qp_iso_date_optional`, e `fn_list_commessa_attivita` riceve una
  `date`. Test: `test_commesse_api` (vuoto = nessun filtro, malformato = 400 col parametro, sulla
  vista e sull'export), provato per mutazione.
* **`zero_as_none` giudicava il grezzo** (`value in (0, "0")`): `" 0"`, `"-0"` e `"00"` diventavano
  0 mentre `"0"` era None, e `0.0` era None mentre `1.0` era un 400. Ora lo zero si riconosce sul
  valore letto. Test: `test_optional_int`, provato per mutazione.
* **Gli altri due lettori con `isdigit()`** (ok Tid, 2026-11-24): `emittente_esplicito_da_query`
  di `core/services/perimetro_emittente.py` (`?e=²` era un 500 di `int()`, `?e=٣` fissava
  l'emittente 3) e `_parse_resi_riga_ids` di `vendite/services/resi_service.py` (stessa cosa sugli
  id riga del corpo). Ora leggono con `SIGNED_INT_RE`; il primo tiene fuori i negativi, come prima.
  Test: `test_perimetro_emittente` (18-bis) e `test_resi_service` (`ResiParseRigaIdsTests`), provati
  per mutazione: col codice di prima i casi `"²"` sono ERROR, cioè il 500.
* Commenti rimasti alla regola di prima: `qp_uuid_optional` (diceva che `optional_uuid` prende
  0/`"0"` per NULL) ed `emittente_attivo_views` (`ValueError`).
* **Prove:** suite BE intera **6797 test, OK** (341 saltati, 1 expected failure); ruff verde sui
  file toccati. Rilanciata dopo i due lettori `isdigit()`: **6800 test, OK** (341 saltati, 1 expected
  failure). ✅ La prova a mano è in §2.4 (riga 3-ter di «Chi riparte»); il `kill -HUP` delle
  23:11 (§3.4) è successivo a queste modifiche.

## 3. Lavoro B — L'envelope delle liste: tre forme, una senza sede

### 3.1 Il fatto

Una lista paginata risponde oggi in una di queste forme:

| Forma | Sede |
| --- | --- |
| `{count, page, page_size, total_pages, results}` | `paginated_envelope` / `envelope_da_offset` (core) |
| `{count: len(results), results}` (collezione consegnata per intero) | `collezione_completa` (core) |
| `{count: total, results}` | **nessuna sede nel core**: scritta a mano |

La terza forma è scritta a mano in circa dodici punti: `magazzino/services/_helpers.risposta_paginata`,
`pagamenti/services/saldi_service.py`, `core/services/processi_service.py` (due volte),
`vendite/db/commesse_repository.py`, `amm_software/api/views.py` (due volte), `core/api/views_lookup.py`,
`core/api/email_views.py` (due volte), `pratiche/api/views.py`, i tool di `ai_assistant`. Magazzino e
pagamenti la tengono come «materiale interno del dominio». La stessa logica, però, sta in sei domini.

Il frontend, letto il 2026-11-24, usa `count` e `results`. Legge `page` dalla risposta solo in
`usePagedDashFetch` (la pagina **effettiva** dei cruscotti, che `query_paged_view` riporta
all'ultima). `page_size` e `total_pages` non li legge nessuno. È un fatto, non il motivo della
scelta: il motivo è in D-1.

[api.md](../../api.md) §Envelope risposte non dice se le forme siano ammesse tutte. È una scelta di
modello: **D-1**, ✅ decisa il 2026-11-24: la forma corta.

### 3.2 Il piano (D-1 decisa: `{count, results}`)

⚠️ Eseguito il 2026-11-24: il giro è in §3.3, con due varianti al piano (il nome del campo della
finestra effettiva, e quattro endpoint con una chiave fuori forma).

* **B1 — Il BB.** Una sede core per la forma decisa, accanto a `collezione_completa` in
  `core/services/list_helpers.py`, con un nome che dice la natura (lista paginata, col totale
  della query).
* **B2 — Le copie si ritirano nello stesso giro**: i punti di §3.1, e `risposta_paginata` di
  magazzino. D-1 ha scelto la forma corta: anche `paginated_envelope` / `envelope_da_offset`
  passano alla forma decisa, e la pagina effettiva dei cruscotti resta solo dove serve.
* **B3 — FE.** `page` esce dalla risposta dei cruscotti e la pagina effettiva passa al campo suo
  (D-1): `usePagedDashFetch` si allinea a quel campo, nello stesso giro del BE. Al resto del FE non
  serve niente.
* **B4 — Presidio.** Un test che rifiuta il letterale `{"count": …, "results": …}` fuori dal BB:
  le eccezioni stanno in un elenco, ognuna col suo motivo.
* **Documentazione:** api.md §Envelope risposte dice la regola; il catalogo aggiorna L46, L408 e
  L1299.

### 3.3 Il giro del 2026-11-24 (team BE/FE)

* **B1 ✅ — Il BB.** `pagina_con_totale(results, totale)` in `core/services/list_helpers.py`, accanto
  a `collezione_completa`: `{count, results}`, con `count` il totale della query. I campi propri di
  una lista stanno accanto (`{**pagina_con_totale(…), "stati": …}`).
* **B2 ✅ — Le copie.** Ritirati `paginated_envelope`, `envelope_da_offset`, `pagina_di` e la chiave
  `page` di `parse_list_params`. Riscritti i call-site in 47 file (riscrittura meccanica, ruff verde).
  Passano al BB anche le copie a mano: `risposta_paginata` di magazzino (ritirata, con i tre service),
  saldi, sistemazioni, titoli IVA, processi, email, lookup comuni, giornale delle pratiche,
  amm_software, commesse, coda lavori, pagamenti e i tool AI. Le collezioni intere fatte a mano
  (`len(...)`) passano da `collezione_completa`. Gli schemi OpenAPI perdono `page`/`page_size`/
  `total_pages`.
  * Variante: **quattro endpoint avevano una chiave fuori forma**, e passano alla forma unica.
    L'audit dei permessi (`events` → `results`, nessun consumatore FE), il registro di una commessa
    (`rows` → `results`; `CommessaRegistroDialog` legge `results`), la coda delle approvazioni prezzo
    (non ripete più `limit`/`offset`; la legge lo store-lista generico), la lista dei run di un lotto
    (via la terna, resta l'alias `task_runs`).
  * **Restano fuori, con motivo** (eccezioni del presidio): le quattro liste admin di `ui`
    (collezione intera col conteggio di controllo da una query sua, per `troncamentoSospetto`) e il
    lookup di catalogo con `troncato`, col suo tool AI.
* **La finestra effettiva dei cruscotti** (variante sul nome): il campo è **`offset_effettivo`**,
  nel dialetto della richiesta, e non una pagina. Lo producono le liste di situazione aperta,
  backlog, competenza (cinque) e fondi fattura, con lo stesso calcolo della `OFFSET LEAST(…)` di
  `query_paged_view`. **B3 ✅** `usePagedDashFetch` ne ricava la pagina; senza il campo resta la
  pagina chiesta, col rientro in pagina 1. Spec nuovo `usePagedDashFetch.spec.js` (4), provato per
  mutazione.
* **B4 ✅ — Presidio.** `core/tests/test_envelope_lista_forma_unica.py`, su AST: nessun dizionario con
  `count` e `results` fuori da `list_helpers` (gli schemi OpenAPI sono esclusi: descrivono la forma,
  non la costruiscono), eccezioni elencate col motivo e verificate vive; nessuna chiave `page_size`/
  `total_pages`.
* **Documentazione ✅** — api.md §Paginazione (la forma unica, `offset_effettivo`, il presidio) e
  §Envelope risposte (il rimando), la tabella degli helper e la checklist della view; catalogo BE:
  voce nuova `pagina_con_totale`, voce ritirata della forma lunga, `query_paged_view`, magazzino,
  lookup codici, giornale; catalogo FE: `usePagedDashFetch`. Pagine `manual/` del backend: §3.5.
* **Test:** 34 test asserivano la forma lunga (`page`, `total_pages`, `events`), più i mock che la
  simulavano: riscritti sulla forma unica, e sui cruscotti su `offset_effettivo`.

### 3.4 Prove (2026-11-24)

* Suite BE intera: **6804 test, OK** (341 saltati, 1 expected failure), dopo B; i test di C e D-3
  rilanciati a parte, verdi. ruff verde.
* FE: vitest intero **205 file, 1302 test, verdi**; lint, guard e build verdi.
* ✅ `kill -HUP` sul master di gunicorn (23:11): worker nuovi, servizio vivo.
* ✅ **A video (Tid, 2026-11-24): tutto ok.** Le prove: un cruscotto (situazione aperta o competenza) sull'ultima pagina, che si
  accorcia mentre lo si guarda (un documento della pagina cambia fase in un'altra scheda), poi
  «Ricarica lista»: il paginatore deve portarsi sull'ultima pagina vera. ⚠️ Corretto il 2026-11-24:
  diceva «poi un filtro», ma un cambio di filtro riparte già dalla pagina 1 (`onFiltriChange`) e non
  esercita la finestra effettiva. Prova diretta: in DevTools la risposta di
  `/vendite/dashboard-aperto/documenti/` porta `count`, `results`, `offset_effettivo` e nient'altro
  della paginazione; con `?offset=100000` `offset_effettivo` è l'inizio dell'ultima pagina. Il registro
  di una commessa (il dialog mostra gli eventi); la coda delle approvazioni prezzo; i Tag del livello
  d'accesso (LETTURA arancio) nei permessi dell'operatore, nei reparti e nei permessi colonna delle
  liste; la lista dei modelli di documento.

### 3.5 Le pagine `manual/` del backend (2026-11-24)

* ✅ 51 pagine di `docs/it/backend/**/manual/` e `frontend-standards.md` descrivevano la forma lunga:
  esempi JSON senza `page`/`page_size`/`total_pages`, la prosa rimanda a `pagina_con_totale` e ad
  api.md §Paginazione, le quattro dashboard dichiarano `offset_effettivo`, l'audit dei permessi e il
  registro della commessa `results`, la coda delle approvazioni senza `limit`/`offset`. Le righe di
  storia vecchie restano, con una riga nuova del 2026-11-24 dove la pagina ha un changelog. Restano,
  volute, le frasi sul dialetto della richiesta (`page`/`page_size` in query sono un 400).
* Indici di `docs/it/backend/core/` rigenerati (`scripts/gen_bk_docs.py --areas core --ci`).

## 4. Lavoro C — Lo scope emittente di documenti, due copie

`documenti/services/template_service.py` ha una copia propria della lettura dello scope. Accanto
c'è `documenti/services/_scope.resolve_emittente_scope`, che delega a
`PermissionResolver.get_emittenti_pk_ids`. Le due copie divergono sull'utente anonimo: la prima
restituisce `[]`, la seconda dal 2026-11-24 solleva `E_SCOPE_SENZA_UTENTE`. Oggi è difficile
arrivarci, perché la view chiede già il JWT. Il piano: la copia di `template_service` passa da
`_scope` e si ritira. Questo punto non era fra le tre proposte accettate: entra con **D-2**, ✅ decisa il 2026-11-24 (sì, in
questo brief).

✅ **Fatto il 2026-11-24.** `TemplateService` legge lo scope con `_scope.resolve_emittente_scope`, e il
suo `_resolve_emittente_scope` è ritirato: per l'anonimo o l'utente assente la risposta è ora il
rifiuto dichiarato `E_SCOPE_SENZA_UTENTE`, come nel resto del dominio. Test:
`test_list_templates_anonymous_user_rifiutato` (al posto di quello che si aspettava `[]`), provato per
mutazione; i patch dei test passano da `_scope`. Catalogo: `TemplateService` e `_scope`. Guida
[architettura-permessi-e-autorizzazioni](../../../guide/architettura-permessi-e-autorizzazioni.md)
§scope **coerente**: descrive già il rifiuto di un perimetro chiesto senza utente.

## 5. Il catalogo del backend: voci doppie

* **L120** (`DEFAULT_LIMIT`/`MAX_LIMIT`, `core/api/constants.py`) è **vecchia e contraddice L882**:
  dice 50 e un «difetto aperto» su `amm_software/constants.py`. Nel codice il valore è 25 e
  amm_software riesporta le costanti del core. Si ritira L120 e la voce vive in L882.
* **L76 / L78 / L80**: `qp_bool_optional` e `qp_int_strict` sono scritte in due righe ciascuna. Si
  fondono in una riga per BB.
* **L416 / L746**: `create_with_constraint_mapping` è scritta in due sezioni. Si tiene la riga della
  sezione di anagrafiche, con la nota «non è un doppione di `map_integrity_error`».
* **L86 / L401**: due funzioni diverse con lo stesso nome, `validate_order_params` di
  `search_validators` (direzione maiuscola, `ASC` se manca) e quella di `list_helpers` (minuscola,
  `None` se manca). È documentato, ma un import sbagliato non dà errore: **D-3**.
* Poi `python3 scripts/gen_indice_bb.py` nello stesso giro.
* ✅ **Fatto il 2026-11-24**: ritirate la riga vecchia di `DEFAULT_LIMIT`/`MAX_LIMIT`, la seconda riga
  di `qp_int_strict` e quella di `qp_bool_optional` (diceva ancora `1/yes/y/on`, ritirati il
  2026-10-20: era vecchia, non doppia), e la riga di `create_with_constraint_mapping` nella sezione
  degli errori di integrità. La riga di anagrafiche resta. L'indice è rigenerato. D-3 ✅ decisa il 2026-11-24: si rinomina quello della ricerca universale
  (riga 10 di «Chi riparte»). ✅ **Fatto il 2026-11-24**: `validate_order_params_ricerca` in
  `search_validators`, con `search_view`, il test e le due righe di catalogo; l'altro omonimo resta
  `list_helpers.validate_order_params`.

## 6. Da chiarire (si guardano nel giro che tocca quei file)

* **E-1 — L'emittente dell'utente.** `ParameterService.get_emittente_fiscale_id_for_user` legge
  `config.user_emittenti_fiscali` in Python. `PermissionResolver.get_emittente_for_user` passa da
  `script.fn_resolve_emittente_for_user`, che probabilmente legge la stessa tabella. Il catalogo
  dice che la semantica è diversa (il primo ha il ripiego sul gestore globale). Da verificare se
  la lettura della tabella è doppia: se lo è, il ripiego resta in Python e la lettura passa dalla
  funzione del DB, oppure è una richiesta al team DB.
  🔵 **Guardato il 2026-11-24: non è un doppione, è una regola diversa, e la regola sbagliata è
  quella del BE.** Il dettaglio sta in §6.1. **Decisione di Tid (2026-11-25): le incoerenze del super
  admin si risolvono.** Il piano è in §6.2.
* **E-2 — `magazzino/db/_helpers.lista_paginata`.** Dalla descrizione del catalogo (L1301) fa lo
  stesso lavoro di `fetch_paged_with_total`, cioè `COUNT(*) OVER ()` più il conteggio di ripiego
  sulla pagina stantia.
  ✅ **Guardato e chiuso il 2026-11-24.** Non era un doppione di `fetch_paged_with_total`: lo
  chiamava, e ci metteva sopra l'avvolgimento della SELECT. Il doppione era un altro:
  `PagamentiRepository._lista_paginata`, la stessa funzione salvo la parola `ORDER BY` dentro
  `order_clause` e l'aggancio `dopo_pagina`. Regola del 2, **ok Tid** (2026-11-24): il BB
  `lista_paginata` sta in `core/db/_helpers.py`, con `order_clause` come corpo senza `ORDER BY`
  (la forma di `sql_order_clause`) e `dopo_pagina` facoltativo, che riceve l'ordine intero. Le due
  copie sono ritirate; i 17 call-site di magazzino non cambiano, gli 8 di pagamenti perdono
  `ORDER BY`. Il conteggio di ripiego resta esplicito: con `dopo_pagina` la query non finisce più
  con `LIMIT/OFFSET` e non saprebbe rileggersi. Catalogo (voce nuova accanto a
  `fetch_paged_with_total`, voce di magazzino corretta) e indice rigenerato.
  **Guide** (`guide_coinvolte.py` sui tre file): restituisce le guide degli oggetti DB che i
  repository nominano; nessuna descrive come si compone la pagina in Python, quindi **coerenti**.
  **Prove:** `test_lista_paginata` (4, nuovo) + `test_fetch_paged_with_total` + le suite
  `magazzino` e `pagamenti`: 333 test, OK (23 saltati); ruff verde.

### 6.1 E-1, l'approfondimento (2026-11-24)

> Lettura del codice e della doc DB generata, nessuna misura a DB. [V] = verificato nel codice,
> [I] = ipotesi da confermare nel giro che tocca il punto. I casi 1, 2 e 4 dell'elenco
> delle incoerenze sono stati riletti a mano dopo l'agente che ha fatto il censimento.

**La regola dichiarata dalle guide.**

* Il super admin non ha un'azienda sua: lavora sull'emittente che sceglie (GUC
  `app.current_emittente_id`), e senza scelta il DB rifiuta le creazioni
  ([pgtap-come-si-scrive-un-test](../../../guide/pgtap-come-si-scrive-un-test.md) L213-221;
  [risorse-umane-e-accessi](../../../guide/risorse-umane-e-accessi.md) L292, L421;
  [architettura-permessi-e-autorizzazioni](../../../guide/architettura-permessi-e-autorizzazioni.md) L394).
* La scelta **restringe, non allarga mai**: in `script.fn_check_user_emittente_scope` il ramo
  «emittente diverso da quello attivo → FALSE» viene prima del bypass del super admin
  (architettura-permessi L758-771).
* «Tutti gli emittenti» è **sola lettura per costruzione**: il FE spegne le creazioni, il DB le
  rifiuta con `E_EMITTENTE_NON_RISOLTO` (`emittente_attivo_service.py` L39-45, COMMENT di
  `script.fn_resolve_emittente_for_user`: «NULL = admin globale in modalità tutti»).
* **Nessun ripiego sul default dell'installazione per attribuire qualcosa**
  (`pagamenti_service.py` L581-590: «attribuirebbe denaro a un emittente che nessuno ha scelto»).
* Il ripiego sul **gestore globale** (G: la riga di `emittenti_fiscali_billing_account` con BA
  NULL e `is_default`) è scritto solo nel commento di `ParameterRepository`
  (`parameter_repository.py` L390-407, «comportamento storico») e nel blocco emittente di
  `script.fn_get_user_profile`. **Nessuna guida lo descrive** [V].

**Il blocco «serve un emittente scelto».** Non c'è un meccanismo unico [V]:

1. il trigger `script.trgfn_default_emittente_fiscale('SOLLEVA')` in INSERT (preventivi, ordini,
   contratti, offerte, pratiche, magazzini, lotti, assets, template documenti e asset, titoli IVA;
   sui DDT `LASCIA_NULL` + `SALTA_CON_SORGENTE`);
2. guard BE espliciti: `email_views.py` L167-182, coda approvazioni
   (`approvazioni_prezzo_service.py` L644-653), BA (`clienti_service.py` L188-199 +
   `fn_check_user_can_create_ba`), distinta (`fn_get_emittente_distinta`), coda lavori per azienda
   (`coda_lavori/scope.py` L83);
3. il FE (`frontend/src/stores/auth.js` L366-394, `modalita_globale` / `emittenteScritturaId`).

La difesa di fondo è `fn_check_user_emittente_scope`, nelle policy RLS e in
`trgfn_guard_emittente_scope`.

**I risolutori di «l'emittente di chi agisce».**

| Punto | Guarda l'emittente attivo | Ripiega su G | Restituisce |
| --- | --- | --- | --- |
| `script.fn_resolve_emittente_for_user` (BE: `PermissionResolver.get_emittente_for_user`) | sì, validato | no: NULL in «tutti» | PK |
| `ParameterRepository.get_emittente_fiscale_id_for_user` | **no** | **sì** | PK |
| `EmittenteAttivoRepository.get_emittente_di_permesso` | no, voluto (circolare) | no | PK |
| `script.fn_get_user_profile`, blocco emittente | **no** | **sì** | PK + SR |
| `script.fn_get_ba_emittente_sr_id` (BA, poi chi agisce, poi `is_default`) | sì, al 2° livello | sì, al 3° | SR |
| `anagrafiche.fn_get_emittente_fiscale_id` (senza BA ripiega su `is_default`) | no, senza BA | sì | SR |
| `script.fn_get_parameter_di_sessione` (cascata parametri dentro il DB) | **GUC** | **no**: vuota = livello saltato | PK |
| `ai_assistant/services/user_context.get_emittente_fiscale_id` (profilo, poi `get_emittenti_pk_ids[0]`) | no | **sì**, dal profilo | PK |
| `email_views.py` L169, `coda_lavori/scope.py` L83 | claim del JWT | no | PK |

Copie della lettura della tabella in Python: `ParameterRepository` e `EmittenteAttivoRepository`
(stesso SQL); quella di `amm_software_repository.py` L274 è una descrizione, innocua. La query di G
in Python sta solo in `ParameterRepository` [V].

**Le incoerenze, dalla più grave.** Per l'operatore tutte le strade danno lo stesso emittente
(al login l'emittente attivo è quello del permesso, `emittente_attivo_service.py` L66-69): le
divergenze sono **solo del super admin**.

1. **Alta, scrittura sbagliata.** Gli override dei parametri «per emittente» si scrivono sempre su
   G, anche con X scelto: `_require_admin_emittente_id` (`views_parameters.py` L60-71) prende
   l'emittente da `get_emittente_fiscale_id_for_user`, e il super admin non ha riga in
   `user_emittenti_fiscali`. `config.parameter_overrides` non ha un guard di scope
   sull'emittente: passa in silenzio. Dalla UI non si imposta un override per un emittente
   diverso da G [V; I che non ci sia un'altra strada].
2. **Alta, scrittura attribuita a G.** In «tutti» l'assistente AI crea pratiche su G
   (`pratiche_tools.py` L264 → `user_context.py` L22-50): la GUC è vuota e il guard di scope
   passa [V]. Con X ≠ G la creazione la rifiuta `trg_pratiche_a10_guard_emittente_scope` [V]. La
   ricerca pratiche del tool filtra su G [I sull'esito RLS], mentre l'API vuole l'emittente
   esplicito (`pratiche/api/views.py` L65).
3. **Media, controllo fatto con l'emittente sbagliato.** Il gate prezzi L2 delle righe (preventivi,
   ordini, DDT, contratti) prende la soglia dall'utente, cioè da G, e non dal documento
   (`_pricing_gate_helpers.py` L141-162). Dal 2026-11-24 il super admin passa davvero dal gate [V].
4. **Media, cascata dei parametri divergente BE/DB.** Con X scelto il DB risponde X, il BE G; in
   «tutti» il DB salta il livello, il BE risponde G [V]. Ci ricadono `ParameterDefaultsView` e
   `ParameterSettingsView` (`views_parameters.py` L127-133, L139, L183, L252: mostrano i valori di
   G come «i tuoi»; in «tutti» `ParameterSettingsView` è sbarrata dal cancello della lista
   `config.parametri_impostazioni`, `ParameterDefaultsView` e le due view di override no) e
   `PricingLimitiUtenteView` (`views_pricing.py` L366-372: l'hint di sconto e
   maggiorazione del drawer riga).
5. **Bassa/media.** La valuta di default proposta senza BA è quella di G anche con X scelto
   (`valuta_resolver.py` L80-82, consumato dai form-defaults dei cinque documenti), mentre il
   trigger scriverà X sul documento.
6. ~~**Bassa, incoerenza d'area.** La coda approvazioni è bloccata in lettura in «tutti».~~
   ❌ **Smentita (Tid e verifica, 2026-11-25): non è un'eccezione.** La coda dichiara
   `lista_codice = "vendite.approvazioni_prezzo"` e passa dal BB `perimetro_emittente`
   (`guard_lista_per_codice`, 422 `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`), come le altre liste con
   `perimetro_emittente` e senza `multi_emittente` nel seed di `ui.lista_definizione` (79 su 113 il
   2026-11-25, fatto datato). Il guard dentro `lista_coda` (`E_APPROVAZIONE_PREZZO_NON_AMMESSA`)
   copre un altro caso: l'operatore senza emittente, che il cancello lascia passare (scope vuoto,
   nessuna ambiguità).
7. **Bassa.** I form-defaults (`vendite_form_defaults_service.py` L165, L458…) e la config ruoli
   (`views_ruoli_config.py` L96) risolvono i parametri **senza** livello emittente, per tutti:
   una terza variante della cascata.
8. **Bassa.** Il ripiego di `_iva_contesto_documento.py` L180 non scatta mai:
   `emittente_fiscale_id` è NOT NULL su preventivi, ordini e DDT; il commento L242-245 è rimasto
   indietro rispetto allo schema [V sullo schema; I che i loader proiettino sempre la colonna].
9. **Bassa.** `email_views` e `coda_lavori` leggono il claim del JWT e non la GUC, che il
   middleware rivalida a ogni richiesta (contratto-guc-app L107-110).
   ❌ **Il rischio ipotizzato cade (Tid, 2026-11-25): un emittente non si disattiva più.** Lo
   impediscono i `trgfn_prevent_deactivate_if_children` su `anagrafiche.emittenti_fiscali` (documenti,
   magazzino, email, override, mapping BA, permessi degli operatori). Resta solo il fatto che la
   stessa informazione si legge da due fonti: allineamento facoltativo, non un difetto.
10. **Nota, non un accesso.** L'operatore senza riga (non configurato) riceve G da
    `fn_get_user_profile` e da `ParameterRepository`: il FE gli mostra G come emittente corrente
    (`auth.js` L301-306), mentre lo scope è fail-closed.

### 6.2 Il piano (decisione di Tid del 2026-11-25: si risolvono)

**La regola unica.** L'emittente su cui si legge un **valore operativo** (parametro, soglia,
valuta, emittente di una scrittura) è quello **del documento** quando c'è un documento, altrimenti
quello **di chi agisce**, cioè `script.fn_resolve_emittente_for_user`: emittente attivo validato,
poi la riga del permesso. In «tutti» la risposta è **NULL**: la lettura salta il livello emittente
(come `fn_get_parameter_di_sessione`), la scrittura si rifiuta. G non è un ripiego operativo:
resta, al più, un'etichetta da mostrare.

| # | Chi | Che cosa | Incoerenza |
| --- | --- | --- | --- |
| E1-1 | team BE/FE | ✅ 2026-11-25 — Override per emittente sull'emittente scelto; in «tutti» 400 `E_EMITTENTE_NON_RISOLTO`. Il FE non cambia: in «tutti» la lista `config.parametri_impostazioni` è sbarrata e i comandi partono dalle sue righe | 1 |
| E1-2 | team BE/FE | ✅ 2026-11-25 — `crea_pratica` sull'emittente di chi agisce (in «tutti» 400), `cerca_pratiche` su quello di chi agisce; ogni tool applica il cancello della lista del gemello | 2 |
| E1-3 | team BE/FE | ✅ 2026-11-25 — Gate L2 con l'emittente del documento (riga e variazione globale del contratto), hint con quello di chi agisce | 3, 4 |
| E1-4 | team BE/FE | ✅ 2026-11-25 — `get_emittente_fiscale_id_for_user` ritirata (service e repository); valuta di default sull'emittente di chi agisce. `get_emittente_di_permesso` resta la sola lettura diretta della tabella | 4, 5 |
| E1-5 | team BE/FE | ✅ 2026-11-25 — (8) ramo morto IVA tolto; (7) BB `contesto_cascata`, ok Tid (§6.5). Il 6 e il rischio del 9 sono smentiti; claim → GUC fatto col BB di §6.3 | 7, 8 |
| E1-6 | team DB | ✍️ Brief scritto il 2026-11-25: [brief-db-emittente-del-super-admin](../../work-in-progress/brief-db-emittente-del-super-admin.md) (R-DB-1 guard di scope su `config.parameter_overrides`, R-DB-2 profilo senza il gestore globale). Sostituisce la richiesta di una funzione «PK del gestore globale», che con questa regola non serve più | 1, 10 |

Prima di scrivere: `scripts/guide_coinvolte.py` sui file di ogni riga; il FE di E1-1 ed E1-4 si
apre con gli indici BB di tutti e due i lati.

### 6.3 Il giro E1-1 / E1-2 (2026-11-25, team BE/FE)

* **BB nuovo, regola del 2 (ok Tid 2026-11-25)**: `emittente_per_scrivere(user, *, function_name)` in
  `core/services/perimetro_emittente.py`. L'emittente di chi agisce
  (`PermissionResolver.get_emittente_for_user`), altrimenti 400 `E_EMITTENTE_NON_RISOLTO`, il codice
  del trigger DB delle creazioni. Nessun ripiego sul gestore globale. Tre consumatori:
  * la bozza email, che lo leggeva dal claim del token (l'allineamento facoltativo del punto 9);
  * gli override dei parametri per emittente (E1-1);
  * `crea_pratica` dell'assistente (E1-2).
* **E1-1, letture.** `get_user_context` (view parametri, default dei form di catalogo e di
  amministrazione software) prende l'emittente da `get_emittente_for_user`: la cascata BE coincide
  con quella del DB, e in «tutti» il livello emittente si salta. Ritirato il ripiego di
  `ParameterSettingsView` su `get_emittente_fiscale_id_for_user`. È un anticipo di E1-4 sullo
  stesso file.
* **E1-2, più largo del previsto.** I tool ereditavano dal gemello il permesso ma non il cancello
  della lista: in «tutti» leggevano dove la schermata sbarra. Sono i tool con gemello di
  dominio e lista a perimetro: `cerca_pratiche`, `crea_pratica`, `cerca_flussi_pratica`,
  `cerca_soggetti`, `cerca_contratti`, `cerca_preventivi`, `cerca_promo_articoli`,
  `cerca_listini`, `cerca_documenti_generati` (registro del 2026-11-25, 18 tool; `cerca_operatori`
  è su una `AdminAPIView`, esente). Ora `AITool.cancello_del_gemello` chiede
  alla view gemella il suo `_cancello_di_lista`, prima di anteprima ed esecuzione e di nuovo alla
  conferma. Le porte esenti (`AdminAPIView`) restano esenti. `user_context.get_emittente_fiscale_id`
  (attributo → profilo → primo emittente visibile) è ritirato. Resta `emittente_di_lettura`, che
  per l'operatore senza emittente risponde con un rifiuto che spiega il motivo.
* **Guide** (`guide_coinvolte.py` sui file toccati):
  [configurazione-e-gestione-parametri](../../../guide/configurazione-e-gestione-parametri.md) e
  [gestione-pratiche](../../../guide/gestione-pratiche.md) sono **coerenti**: nessuna delle due dice su
  quale emittente scrive il backend. Le altre arrivano da `anagrafiche.billing_account` e non sono
  toccate.
* **Catalogo**: voci nuove `emittente_per_scrivere` e `AITool.cancello_del_gemello`;
  `ParameterService.get_emittente_fiscale_id_for_user` segnato «da ritirare» (E1-4), con i
  consumatori che restano. Indice rigenerato.
* **Prove**: test nuovi `ParameterOverrideEmittenteTests` (5),
  `test_tool_emittente_di_chi_agisce` (7) e il caso 7 delle email; i test dei parametri e
  `test_tools_fase4` sono passati alla nuova fonte dell'emittente. **Suite BE intera: 6821 test,
  OK** (341 saltati, 1 expected failure); ruff verde.

### 6.4 Il giro E1-3 / E1-4 / E1-5 (2026-11-25, team BE/FE)

* **E1-3, il gate L2.** `check_limite_variazione_prezzo` e `check_limite_variazione_globale`
  ricevono `emittente_fiscale_id` come keyword **obbligatoria, senza default**: un chiamante che
  la dimentica non compila. La riga la prende dalla testata (`testata["emittente_fiscale_id"]`,
  indicizzato: una testata senza emittente è un difetto del loader, e con `.get()` il livello
  salterebbe in silenzio). Le letture di testata dei cinque documenti la portano: preventivo,
  offerta, contratto, ordine e DDT. La variazione globale del contratto prende l'emittente del
  contratto; alla nascita senza emittente nel payload prende quello che il trigger gli darà
  (`get_emittente_for_user`).
* **E1-3, l'hint** (`PricingLimitiUtenteView`). Usa l'emittente di chi agisce: con un emittente
  scelto si vedono solo i suoi documenti, e in «tutti» le liste dei documenti sono sbarrate.
* **E1-4.** `ParameterService` e `ParameterRepository.get_emittente_fiscale_id_for_user` sono
  **ritirati**. `resolve_valuta_default`, al livello 3, usa l'emittente di chi agisce; in «tutti»
  si scende al livello 4, il gestore dell'installazione, come `vendite.fn_get_valuta_id`.
* **E1-5 (8).** `contesto_da_testata` non ripiega più sull'operatore: `emittente_fiscale_id` è NOT
  NULL su preventivi, ordini e DDT (verificato nella doc DB), e una testata senza emittente si
  ferma (`P3`). Tolti `usa_auth_user` dalla factory e `auth_user_id` dalla view di anteprima IVA.
* **E1-5 (7), fermo.** I default dei form di vendite (`vendite_form_defaults_service`: contratto,
  preventivo, versioni di listino) passano alla cascata **solo l'utente**: mancano gruppi ed
  emittente. La config ruoli (`get_config_resolver`) passa **solo l'emittente** (oggi None). Il
  contesto completo, cioè utente, gruppi ed emittente di chi agisce, lo costruisce oggi solo
  `get_user_context` nelle view dei parametri. Darlo anche a questi punti ne farebbe una seconda
  copia. **Proposta per Tid:** un BB `contesto_cascata(user) -> {django_user_id, group_ids,
  emittente_fiscale_id}` in `ParameterService`. `get_user_context` gli delega, e lo usano i form
  e la config ruoli.
* **Guide** (`guide_coinvolte.py` sui quattro file): gestione-listini, gestione-preventivi,
  gestione-ordini, gestione-contratti, gestione-ddt e iva-risolutore-di-riga sono **coerenti**:
  nominano la soglia L2 e il risolutore, ma non dicono di quale emittente. Le altre arrivano da
  `emittenti_fiscali` e `config.sorgenti` e non sono toccate.
* **Catalogo**: le due voci della funzione segnate «ritirato»; il gate L2 e `resolve_valuta_default`
  aggiornati. Indice rigenerato.
* **Prove**: test nuovi `test_gate_l2_alla_nascita_emittente_di_chi_agisce` e
  `test_limiti_utente_emittente_di_chi_agisce`; asserzioni sull'emittente del documento nei test
  del gate di preventivi e contratti; i test di valuta e del contesto IVA passati alla regola
  nuova. **Suite BE intera: 6820 test, OK** (341 saltati, 1 expected failure); ruff verde.

### 6.5 E1-5 (7), il contesto della cascata (2026-11-25, team BE/FE)

* **BB nuovo, regola del 2 (ok Tid 2026-11-25)**: `contesto_cascata(user)` in
  `core/services/parameter_service.py` → `{django_user_id, group_ids, emittente_fiscale_id}` di chi
  agisce, con l'emittente da `get_emittente_for_user`; senza utente `{}`. È una funzione di modulo
  e non un metodo: i test che sostituiscono `ParameterService` con un mock non la spengono.
* **Consumatori:**
  * `get_user_context` delle view dei parametri, che ora delega al BB;
  * le cinque letture di `vendite_form_defaults_service` (contratto, preventivo, versione di
    listino nuova, clonata e chiusa), che prima passavano il solo utente;
  * `RuoliConfigResolverView` → `SoggettiRepository.get_config_resolver(contesto_cascata=)`, che
    prima riceveva il solo emittente e la view non lo passava.
* **Guide**: [configurazione-e-gestione-parametri](../../../guide/configurazione-e-gestione-parametri.md)
  è **coerente**: descrive la cascata a cinque livelli, che ora arriva intera anche a questi punti.
* **Prove**: test nuovi `ContestoCascataTests` (2), `FormDefaultsCascataTests` (1) e
  `test_config_resolver_cascata_di_chi_agisce` (1). **Suite BE intera: 6824 test, OK** (341
  saltati, 1 expected failure); ruff verde. Catalogo: voce nuova `contesto_cascata`, indice
  rigenerato.

### 6.6 /verifica del giro E-1 / E-2 (2026-11-25, sessione nuova)

* **Il tool dei flussi era più severo della sua schermata.** `ApiPraticaFlussiList` dichiara
  `lista_emittente_param`: il tab Flussi le passa l'emittente della pratica e in «tutti» passa il
  cancello. `AITool.cancello_del_gemello` leggeva quel parametro dalla query della richiesta di
  chat, che non lo porta mai: in «tutti» `cerca_flussi_pratica` rifiutava (422) i flussi che la
  schermata mostra. **Corretto (ok Tid):** `cancello_del_gemello(request, params)` passa a
  `_cancello_di_lista(emittente_esplicito=)` l'emittente che il tool fissa (`emittente_fissato`,
  default `None`), mai la query della chat. Vale solo dove la view dichiara il parametro. Lo
  sovrascrive `cerca_flussi_pratica` con l'emittente della pratica. Il default di
  `_cancello_di_lista` resta la lettura dalla query (`EMITTENTE_DALLA_RICHIESTA`).
* **Regola del 2 (ok Tid):** `PermissionResolver.get_emittente_for_user_id(auth_user_id)`. La
  coppia `utente_per_id` + `get_emittente_for_user` stava in `valuta_resolver` e nel gate L2 del
  contratto alla nascita. La funzione del DB vuole solo l'id, quindi la lettura dell'utente era una
  query in più.
* **Doc indietro:** il docstring di `get_emittente_for_user` e la sua voce di catalogo dicevano
  «`None` per admin globale», mentre dal 2026-08-04 la funzione DB risponde l'emittente attivo
  validato anche al super admin: è il comportamento su cui poggiano `emittente_per_scrivere` e
  `contesto_cascata`. Allineati; voce `cancello_del_gemello` aggiornata; indice rigenerato.
* **Guide:** nessuna nomina `fn_resolve_emittente_for_user`; la regola «la scelta restringe, non
  allarga» di architettura-permessi-e-autorizzazioni è **coerente** col docstring nuovo.
* **Prove:** 4 test nuovi in `test_tool_emittente_di_chi_agisce` (8-10); il test 8 va in errore
  (422) con il codice di prima. Test dei moduli toccati (ai_assistant, cancello e perimetro del
  core, parametri, email, permessi, valuta, config ruoli, flussi, liste di vendite e catalogo,
  pricing, contratti, form-defaults): **667 test, OK** (2 saltati). Ruff verde su tutti i file
  Python del perimetro. Suite intera non lanciata (regola del 2026-11-25: alla chiusura del brief).

## 7. Audit del frontend (2026-11-24)

**Metodo.** Lo stesso di §1: l'indice del catalogo del frontend letto per intero (556 voci),
raggruppato per argomento (lookup e autocomplete, paginazione e liste, polling e debounce, anti-race,
maiuscolo, severity, note, etichette delle tab). Dove le voci si somigliavano si sono aperti il
catalogo e il codice. Stesso limite: le voci si sono confrontate solo dentro i gruppi.

**Esito.** Due doppioni nel codice (F-1, F-2), un BB senza consumatori (F-3), un alias (F-4), due
righe vecchie nel catalogo, due punti da chiarire. ✅ Le proposte F sono accettate da Tid (**D-4**, 2026-11-24).

### 7.1 Doppioni nel codice

* **F-1 — Il debounce di `useServerAutocomplete` è una seconda copia di `useDebouncedAction`.**
  [useServerAutocomplete.js](../../../../../frontend/src/core/composables/useServerAutocomplete.js)
  ha un `setTimeout` suo. Le due copie divergono già:
  * lo spegne solo su `onUnmounted`, mai su `onDeactivated`. È il difetto che `useDebouncedAction`
    dichiara di chiudere: una ricerca digitata appena prima di cambiare scheda (KeepAlive) parte con
    la scheda in background;
  * non ha la guardia anti-race (`useFetchVersion`): una risposta lenta a «ros» può arrivare dopo
    quella a «rossi» e scriverci sopra i suggerimenti;
  * il ritardo è 300 ms contro `SEARCH_DEBOUNCE_MS` (400). Questo può essere voluto per un
    autocomplete: va scritto.

  Tutti gli autocomplete del progetto passano da qui (`BillingAccountLookup`, `IstanzaUtilityLookup`,
  `SoggettoRuoloLookup`, `ArticoloLookup`, `FatturaLookup`, comune, stradario, conto bancario, canale
  d'incasso). Correggere il BB li corregge tutti. **Piano:** il timer passa da `useDebouncedAction`
  (`detailed: true`, il `cancel` sul percorso «troppo corto»), la fetch passa da `useFetchVersion`, e
  il ritardo diventa una costante con nome accanto a `SEARCH_DEBOUNCE_MS`. Ci vuole un test per il
  cambio di scheda e uno per la risposta fuori ordine.
* **F-2 — Il maiuscolo mentre si digita: `InputMaiuscolo` e `normalizeUpper*`.**
  [InputMaiuscolo.vue](../../../../../frontend/src/core/components/InputMaiuscolo.vue) (codice SDI,
  estensione del civico) e `normalizeUpperNoSpaces` di
  [string.js](../../../../../frontend/src/core/utils/string.js) (`@input` su IBAN, codice fiscale e
  `codice` dell'emittente) dicono la stessa cosa. Divergono già:
  * `InputMaiuscolo` rimette il cursore dov'era, `normalizeUpperNoSpaces` no. Chi corregge una
    lettera in mezzo a un IBAN o a un codice fiscale si ritrova il cursore in fondo, proprio il
    difetto che `InputMaiuscolo` ha chiuso;
  * `normalizeUpper` (che tiene gli spazi) non ha consumatori;
  * in `EmittenteFiscaleDrawer` il `codice` passa da `normalizeUpperNoSpaces`: è il maiuscolo del
    `codice` ricopiato in JavaScript, che la voce `app-codice-input` vieta (la regola sta nel DB,
    la classe la mostra solo a video; due copie sono state ritirate il 2026-11-04).

  **Piano:** `InputMaiuscolo` prende un'opzione `senzaSpazi`, e IBAN e codice fiscale lo usano. Il
  `codice` dell'emittente torna `InputText` con `app-codice-input`, e `normalizeUpper*` si ritirano.
  ⚠️ Togliere gli spazi dall'IBAN è un aiuto di digitazione, come il maiuscolo: la forma la decide il
  DB.

### 7.2 Un BB senza consumatori, un alias

* **F-3 — `usePagination`** (catalogo L51) non ha consumatori: lo nomina solo un commento di
  `core/misurePagina.js`. La paginazione delle liste in drawer è `useListaDrawerPaginata`, quella
  degli store-lista `useListaStoreCore`. **Piano:** si ritira il file e la voce diventa «ritirato»,
  con la data. Prima si cerca anche negli spec e nei componenti `.vue` caricati dinamicamente.
* **F-4 — `resolveTabLabel`** in [navigation.js](../../../../../frontend/src/core/navigation.js) è un
  alias di `resolveNavigationLabel` (lo restituisce e basta). Due nomi per la stessa regola, accanto
  a `resolveTabDisplayLabel`, che è un'altra cosa (l'etichetta a video). **Piano:** i due chiamanti
  (router e `AppBreadcrumb`) chiamano `resolveNavigationLabel` e l'alias si ritira. In alternativa
  l'alias resta, dichiarato come tale nel catalogo. È un dettaglio.

### 7.3 Il catalogo del frontend

* **L1095** («`PreventivoNoteDrawer` / `ContrattoNoteDrawer` wrapper note») è vecchia: i sei wrapper
  sono stati ritirati il 2026-10-31 (L760). Si ritira.
* **L944** (`ArticoloNoteDrawer`) dice «pattern simmetrico a `PreventivoNoteDrawer`/`ContrattoNoteDrawer`»,
  che non esistono più. Si corregge: l'articolo è oggi l'unico wrapper sopra `NoteDrawer`, mentre
  vendite monta `VenditeNoteDrawer`.
* Le voci di F-1…F-4 si aggiornano nel giro che le tocca. Poi `python3 scripts/gen_indice_bb.py`.

### 7.4 Da chiarire

* **E-3 — `useJobPolling`** ha un ciclo suo (`setTimeout` ricorsivo con backoff per job) e non usa
  `useRefreshPeriodico`. Dal 2026-08-27 riprende da solo su `onActivated`, ma non ascolta
  `visibilitychange`: con il tab del browser in background il polling continua. Il contratto è
  diverso (segue un job fino allo stato finale), e può essere voluto. Va deciso e scritto nella voce.
* **E-4 — Severity fuori da `severity.js`.** `getLivelloSeverity` / `getAuditOpSeverity`
  (`amministrazione/constants.js`) e `parameterLevelSeverity` (`core/utils/parameterLevel.js`)
  non passano da `resolveSeverity`. Da guardare se ripetono una mappa che esiste già.

### 7.5 Falsi allarmi (verificati, distinti)

* `useLookup` (per istanza) e `useGlobalLookup` (condiviso) hanno due contratti dichiarati.
  `useLookupCodici` e `useLookupEtichettato` stanno sopra `useGlobalLookup`.
* `useQueueCountsPolling` e `usePresidiPolling` stanno sopra `useRefreshPeriodico`.
* `usePagedDashFetch` e `useDashRiepilogo` stanno sopra `useFetchVersion`.
* `useSearchTable` sta sopra `useDebouncedAction`.
* Le funzioni `*Severity` di `severity.js` passano tutte da `resolveSeverity`.
* Nessun autocomplete scrive un suo debounce: tutti passano da `useServerAutocomplete` (per questo
  F-1 si corregge in un punto).


### 7.6 Il piano del giro F (D-4, 2026-11-24)

Lato frontend soltanto. Il BE non cambia.

1. **F-1** — `useServerAutocomplete`: il timer passa a `useDebouncedAction` (`detailed: true`, il
   `cancel` sul percorso «troppo corto» e al cambio di scheda, come fa già il BB). La fetch passa da
   `useFetchVersion`: una risposta superata si scarta. Il ritardo diventa una costante con nome
   accanto a `SEARCH_DEBOUNCE_MS`, col motivo per cui un autocomplete usa un valore suo. Test: la
   risposta fuori ordine non scrive, il timer muore su `onDeactivated`. Consumatori da riprovare con
   vitest: i nove autocomplete di §7.1.
2. **F-2** — `InputMaiuscolo` prende la prop `senzaSpazi`. IBAN (`ContoBancarioForm`) e codice
   fiscale (`SoggettoForm`) lo usano al posto di `@input="normalizeUpperNoSpaces(…)"`. Il `codice` di
   `EmittenteFiscaleDrawer` torna `InputText` con `app-codice-input`. `normalizeUpper` e
   `normalizeUpperNoSpaces` si ritirano da `core/utils/string.js` insieme ai loro test. Test di
   `InputMaiuscolo`: con `senzaSpazi` gli spazi spariscono e il cursore resta al suo posto.
3. **F-3** — `usePagination.js` si cancella, col suo spec se c'è. Il commento di `core/misurePagina.js`
   che lo nomina si corregge. Prima, una ricerca anche sugli import dinamici.
4. **F-4** — Il router e `AppBreadcrumb` chiamano `resolveNavigationLabel`. `resolveTabLabel` si
   ritira, e il commento di `AppTopbar` che lo nomina si corregge.
5. **Catalogo FE** — Le voci di F-1…F-4 si aggiornano (F-3 e F-4 diventano «ritirato», con la
   data). L1095 si ritira, L944 si corregge (§7.3). Poi `python3 scripts/gen_indice_bb.py`.
6. **E-3 / E-4** — Si guardano nello stesso giro, senza toccare il codice. L'esito si scrive qui:
   è voluto, oppure è una proposta per Tid.
7. **Prove** — vitest intero, lint del FE, build.


### 7.7 Il giro F del 2026-11-24 (team BE/FE)

* **F-1 ✅** — `useServerAutocomplete` usa `useDebouncedAction` per il timer e `useFetchVersion` per
  scartare le risposte superate. Un tasto nuovo invalida anche la risposta già in volo; una query
  troppo corta, il cambio di scheda e lo smontaggio abbandonano la ricerca in attesa e quella in
  volo, e spengono la rotellina. Il ritardo è la costante `AUTOCOMPLETE_DEBOUNCE_MS` (300): resta
  quello di sempre, e la differenza dai 400 delle liste è scritta ma non motivata (§8, D-6). Spec
  nuovo, `useServerAutocomplete.spec.js` (5 test, montato con KeepAlive). Provato per mutazione:
  senza la guardia due test diventano rossi, con un timer a mano senza `onDeactivated` uno.
* **F-2 ✅, con una variante al piano.** L'IBAN di `ContoBancarioForm` è un `AutoComplete` e non può
  essere un `InputMaiuscolo`. La forma e il cursore sono quindi estratti in `core/utils/maiuscolo.js`
  (`formaMaiuscola`, `riscriviDigitato`), con due consumatori: `InputMaiuscolo` (prop nuova
  `senza-spazi`, usata dal codice fiscale di `SoggettoForm`) e l'IBAN. Il cursore conta solo i
  caratteri che restano, quindi gli spazi tolti prima di lui lo spostano indietro. Il `codice` di
  `EmittenteFiscaleDrawer` non si riscrive più in JavaScript: lo alza il DB
  (`trgfn_emittenti_fiscali_guard_codice_forma`, forma di `fn_codice_normalizzato`), e
  `app-codice-input` lo mostra soltanto. Il commento del drawer, che attribuiva il maiuscolo al
  JavaScript, è corretto. `normalizeUpperNoSpaces` e `normalizeUpper` sono ritirati da `string.js`.
  Test: `maiuscolo.spec.js` (4) e due casi nuovi in `InputMaiuscolo.spec.js`. Provato per mutazione:
  il cursore calcolato sul testo con gli spazi fa diventare rossi due test.
* **F-3 ✅** — `core/composables/usePagination.js` è cancellato. Non c'erano consumatori, nemmeno
  dinamici, né uno spec. Corretti il commento di `misurePagina.js` e la riga di frontend-standards,
  che lo dava usato da `SearchDrawer` (non lo era).
* **F-4 ✅** — router e `AppBreadcrumb` chiamano `resolveNavigationLabel`; `resolveTabLabel` è
  ritirato da `navigation.js`. Corretti i commenti di `AppTopbar` e `AppBreadcrumb` e la riga di
  frontend-standards.
* **Catalogo FE ✅** — `usePagination`, `normalizeUpper*` e `resolveTabLabel` sono «ritirato», con la
  data. Voce nuova `formaMaiuscola` · `riscriviDigitato`. Aggiornate `useServerAutocomplete` e
  `InputMaiuscolo`. L1095 ritirata, L944 corretta. L'indice è rigenerato.
* **E-3, esito: voluto, ma non scritto.** `useJobPolling` segue un job fino allo stato finale, col
  suo tetto di sicurezza, e si sospende su `onDeactivated`. Non ascolta `visibilitychange`, quindi
  con il tab del browser in background continua a interrogare. Ha senso per un lavoro che finisce
  (chi torna trova l'esito), ma non è dichiarato. Proposta: una riga nella voce di catalogo, senza
  cambiare il codice (D-6).
* **E-4, esito: un doppione vero, con due colori.** Il livello d'accesso (TUTTO / LETTURA / BLOCCATO)
  ha due mappe di colore: `getLivelloSeverity` di `amministrazione/constants.js` (LETTURA = `warn`,
  arancio) e `severityForLivello` di `ui/components/ListaColonnaPermessoPanel.vue` (LETTURA = `info`,
  azzurro). Lo stesso livello ha due colori secondo la pagina. Proposta: una sede sola in
  `core/utils/severity.js` (`livelloAccessoSeverity`, su `resolveSeverity`), perché `ui` non importa
  `amministrazione`. Il colore di LETTURA è arancio (**D-5**, decisa il 2026-11-24). `getAuditOpSeverity` e
  `parameterLevelSeverity` non hanno copie: restano dove sono.
* **Prove:** in §7.8.

### 7.8 Prove del giro F (2026-11-24)

* vitest intero: **202 file, 1294 test, verdi**. Guard (`npm run guards`) verdi. Build verde.
* Lint: il primo giro ha trovato due nomi di componente di una parola nello spec nuovo
  (`vue/multi-word-component-names`). Corretti, e `npm run lint` è verde.
* ✅ **A video (Tid, 2026-11-24): tutto ok.** Le prove: un autocomplete (cliente in un documento) con una digitazione veloce e un
  cambio di scheda subito dopo; l'IBAN e il codice fiscale, correggendo una lettera in mezzo (il
  cursore deve restare lì) e incollando un valore con gli spazi; il codice di un emittente nuovo
  scritto in minuscolo (si vede in maiuscolo, e il DB lo salva in maiuscolo).

### 7.9 La revisione del giro F (2026-11-24)

* **Difetto di F-2: il Salva dell'emittente nuovo restava spento con un codice minuscolo.** `canSave`
  provava il valore con `^[A-Z0-9]{2,10}$`; finché il JavaScript alzava il maiuscolo la regola
  reggeva, tolto quello chi scriveva `acme` vedeva `ACME` (`app-codice-input`) e non poteva
  salvare. Il predicato è ora `codiceEmittenteInForma` in `amministrazione/codiceEmittente.js`,
  senza distinzione di maiuscole (le alza il guard DB, che è stato riletto dalla doc auto-generata:
  `fn_codice_normalizzato`, poi la forma). Test: `codiceEmittente.spec.js`, provato per mutazione.
* **D-6 scritta** (riga 12): il commento di `useServerAutocomplete` e la voce di catalogo dicono il
  motivo dei 300 ms; la voce di `useJobPolling` dice che il polling col tab in background è voluto.
  Indice FE rigenerato.
* `guida-sviluppo-frontend.md` (work-in-progress) nominava ancora `resolveTabLabel`: corretto.
* **Guide verificate** (`scripts/guide_coinvolte.py` sul diff del giro A e F): le guide trovate
  nascono dagli oggetti DB che le view e i service toccati nominano; il giro cambia la lettura dei
  parametri, non il dominio. Le pertinenti a F-2:
  [numerazione-documenti-e-codici](../../../guide/numerazione-documenti-e-codici.md) (la sigla:
  maiuscole e cifre, salvata così) **coerente**;
  [automazione-db](../../../guide/automazione-db.md) §4.8 (il codice lo alza il DB) **coerente**;
  [soggetti-e-ruoli-anagrafici](../../../guide/soggetti-e-ruoli-anagrafici.md) (codice fiscale in
  forma sola, dal DB) e [gestione-conti-bancari](../../../guide/gestione-conti-bancari.md) (IBAN
  normalizzato dal trigger) **coerenti**: il maiuscolo del FE resta un aiuto di digitazione.
* **Prove:** vitest intero **203 file, 1296 test, verdi**; lint, guard, classi morte e build
  verdi. Il controllo i18n segnalava una chiave emessa dal DB e assente dai locales
  (`anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna`), che non nasceva da questo giro: è la
  voce 3 di §20.7 di [brief-db-revisione-anagrafiche](../../work-in-progress/brief-db-revisione-anagrafiche.md), e su
  richiesta di Tid è aggiunta in `it.json` ed `en.json` (2026-11-24). Con l'ok di Tid è tolta la chiave
  ritirata `senza_natura_con_titoli_iva`, che non citava più nessuno. Ora il controllo i18n è pulito.
  ⚠️ Nello stesso momento un'altra mano ha alzato in `frontend/package.json` chart.js, oxlint ed
  eslint-plugin-oxlint: lint e build di questa sezione girano sulle versioni di prima.

### 7.10 D-5, il colore del livello d'accesso (2026-11-24)

* ✅ `livelloAccessoSeverity` / `LIVELLO_ACCESSO_MAP` in `core/utils/severity.js`, su
  `resolveSeverity`: TUTTO verde, LETTURA arancio, BLOCCATO rosso. Ritirati `getLivelloSeverity`
  (`amministrazione/constants.js`, tre consumatori) e `severityForLivello`
  (`ListaColonnaPermessoPanel`, dove LETTURA era azzurro). Un valore fuori vocabolario è ora neutro
  (`secondary`), come per ogni mappa di `severity.js`; prima era rosso in amministrazione.
* Spec `livelloAccessoSeverity.spec.js`: i colori, e nessuna mappa del livello fuori da
  `severity.js`. Provato per mutazione con la copia vecchia del pannello.
* Catalogo FE: voce nuova. Prove in §3.4.

## 8. Decisioni di Tid

* **D-1 — La forma dell'envelope di una lista paginata.** Raccomandazione: una forma sola,
  `{count, results}`, dove `count` è il totale della query. La finestra si chiede con
  `limit`/`offset` (un dialetto solo, Tid 2026-10-21), quindi `page`/`page_size`/`total_pages`
  nella risposta ripetono una finestra in una lingua che la richiesta non parla più. Fa eccezione
  la pagina **effettiva** dei cruscotti, che è un dato vero (il BE ha spostato la finestra). Si
  dichiara con un campo proprio, per esempio `offset` effettivo, solo dove `query_paged_view` la
  produce. In alternativa: si tengono le due forme, e il BB nuovo dà la sede alla forma corta
  accanto a `paginated_envelope`.
  ✅ **Decisa da Tid il 2026-11-24: la forma unica `{count, results}`**, con la pagina effettiva dei
  cruscotti in un campo suo. Il nome del campo si fissa nel giro B.
* **D-2 — Lavoro C dentro questo brief?** È un doppione nello stesso dominio, piccolo, della stessa
  natura degli altri.
  ✅ **Decisa da Tid il 2026-11-24: sì, il lavoro C entra in questo brief.**
* **D-3 — I due `validate_order_params`.** Raccomandazione: si rinomina quello della ricerca
  universale (per esempio `validate_order_params_ricerca`), in modo che l'omonimia non possa più
  far importare la funzione sbagliata. In alternativa: resta com'è, documentato.
  ✅ **Decisa da Tid il 2026-11-24: si rinomina quello della ricerca universale.**
* **D-4 — Le proposte del frontend (§7).** F-1 (`useServerAutocomplete` sopra `useDebouncedAction`
  e `useFetchVersion`), F-2 (`InputMaiuscolo` con `senzaSpazi`, ritiro di `normalizeUpper*`, il
  `codice` dell'emittente con `app-codice-input`), F-3 (ritiro di `usePagination`), F-4 (ritiro
  dell'alias `resolveTabLabel`, o lasciarlo dichiarato). Raccomandazione: tutte e quattro. F-1 e F-2
  correggono difetti che si vedono a video.
  ✅ **Decisa da Tid il 2026-11-24: sì a tutte e quattro.** Per F-4 vale il ritiro dell'alias. Il
  piano del giro è in §7.6.
* **D-5 — Il colore del livello LETTURA (§7.7, E-4).** Oggi è arancio (`warn`) nelle pagine di
  amministrazione e azzurro (`info`) nei permessi colonna delle liste. Con una sede sola diventa un
  colore. Raccomandazione: **arancio**. LETTURA è una limitazione, e l'arancio la segnala come
  tale; l'azzurro la fa sembrare un'informazione neutra.
  ✅ **Decisa da Tid il 2026-11-24: arancio (`warn`)**, in una sede sola (riga 11 di «Chi riparte»).
* **D-6 — Due cose da scrivere, senza cambiare il codice.** (a) Il debounce di 300 ms degli
  autocomplete contro i 400 delle liste: si tiene la differenza (motivo: una tendina risponde a chi
  sta scegliendo una voce) o si uniforma a 400? (b) `useJobPolling` che continua col tab del browser
  in background (E-3): si dichiara voluto nella voce di catalogo?
  ✅ **Decisa da Tid il 2026-11-24:** (a) si tengono i 300 ms, col motivo scritto (una tendina
  risponde a chi sta scegliendo una voce); (b) sì, il polling in background si dichiara voluto
  (chi torna trova l'esito). Riga 12 di «Chi riparte».
