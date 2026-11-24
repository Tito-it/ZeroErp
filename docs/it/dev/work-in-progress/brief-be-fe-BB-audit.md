# Brief BE/FE — Audit dei building block: i BB che fanno la stessa cosa

## ⏭️ Chi riparte — aggiornato al 2026-11-24

**Riparte: team BE/FE** coi lavori B, C e le righe 10–11, che non aspettano più niente: le decisioni D-1…D-6 sono tutte prese (Tid, 2026-11-24). **Tid** in parallelo: il collaudo a video del FE (§7.8). La prova a mano del BE è fatta (§2.4). Sono fatti, e da committare, A, il catalogo BE e il lavoro F.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team BE/FE | ✅ Audit del backend (2026-11-24) | §1 | — |
| 2 | team BE/FE | ✅ Audit del frontend (2026-11-24) | §7 | — |
| 3 | Tid | ✅ Decisioni D-1…D-6 prese il 2026-11-24: D-4 per prima (sì a F-1…F-4), poi D-1, D-2, D-3, D-5, D-6 secondo le raccomandazioni | §8 | — |
| 3-bis | team BE/FE | ✅ Lavoro F (2026-11-24): F-1…F-4, catalogo FE, E-3 ed E-4 guardati | §7.7 | — |
| 3-quater | Tid | Il collaudo a video del giro F | §7.8 | 3-bis |
| 3-ter | team BE/FE | ✅ Prova a mano dei filtri vuoti sul server (2026-11-24): 200 sui filtri vuoti, 400 col nome del parametro su quelli sbagliati | §2.4 | — |
| 4 | team BE/FE | ✅ Catalogo BE (2026-11-24): voci vecchie ritirate, righe doppie fuse, indice rigenerato | §5 | — |
| 5 | team BE/FE | ✅ Lavoro A (2026-11-24): query string e header ai `qp_*`, funzioni del corpo che delegano a `PayloadValidator`, service sul validator del dominio; il FE non aveva niente da correggere | §2.3 | — |
| 6 | team BE/FE | Lavoro B: un BB core per l'envelope `{count, results}`, le copie si ritirano, la pagina effettiva dei cruscotti in un campo suo | §3 | — (D-1 ✅) |
| 7 | team BE/FE | Lavoro C: lo scope di `template_service` passa da `_scope` | §4 | — (D-2 ✅) |
| 8 | team BE/FE | I due punti da chiarire, guardati nel giro che tocca quei file | §6 | — |
| 10 | team BE/FE | D-3: il `validate_order_params` di `search_validators` si rinomina (`validate_order_params_ricerca`), call-site e catalogo nello stesso giro | §5, §8 | — |
| 11 | team BE/FE | D-5: il colore del livello d'accesso in una sede sola, `core/utils/severity.js`, LETTURA = `warn`; si ritirano `getLivelloSeverity` e `severityForLivello` | §7.7 (E-4), §8 | — |
| 12 | team BE/FE | ✅ D-6 (2026-11-24, alla revisione): il motivo dei 300 ms in `useServerAutocomplete` e nella sua voce di catalogo; il polling in background dichiarato voluto nella voce di `useJobPolling` | §7.9 | — |
| 13 | team BE/FE | ✅ Revisione del giro A e del giro F (2026-11-24): quattro difetti corretti | §2.5, §7.9 | — |
| 9 | team BE/FE | Archiviazione in `work-done/` | — | 3-bis, 3-quater, 4–8, 10–12 |

**Decisioni aperte di Tid:** nessuna. Le tre proposte dell'audit del backend sono accettate (Tid,
2026-11-24): A, B, e la pulizia del catalogo; lo stesso giorno D-4 (F-1…F-4) e poi D-1, D-2, D-3,
D-5, D-6, tutte secondo la raccomandazione di §8.
**Da committare:** il lavoro A e il catalogo BE (§2.3, §5), il lavoro F (§7.7), le correzioni della
revisione (§2.5, §7.9), e questo brief.

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-11-24. **A chi:** team BE/FE e Tid.
> **Origine:** la domanda di Tid «chi mi dice che i building block stessi non siano stati doppiati?».
> La regola del 2 confronta il codice nuovo col catalogo, mai un BB con un altro BB, e il
> pre-commit (`gen_indice_bb.py --check`) controlla solo che l'indice sia allineato al catalogo.
> **Brief vicini verificati:** nessuno copre il tema.
> [piano-migrazione-primevue-5](piano-migrazione-primevue-5.md) nomina `paginated_envelope` e
> `parse_list_params` solo come BB già esistenti; i brief di `work-in-progress/` non toccano
> `optional_*`, `risposta_paginata` né `envelope_da_offset`.
> **Guide verificate** (`scripts/guide_coinvolte.py` sui sette file toccati): le 45 guide e le 12
> note di dominio trovate nascono dagli oggetti DB che quei moduli condivisi nominano. Il lavoro
> non cambia nessun oggetto DB e nessuna regola di dominio: cambia il trasporto in Python. Due sono
> pertinenti:
> [Messaggi-di-Errore-e-Generazione-Log](../../guide/Messaggi-di-Errore-e-Generazione-Log.md) è
> **coerente**: chiede che un dato errato esca col suo campo (`DATO_ERRATO`, «il nome del campo si
> dichiara»), e il lavoro A ci porta le letture che oggi non lo danno.
> [configurazione-liste](../../guide/configurazione-liste.md) è **coerente**: non descrive la forma
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
[payload_validators.py](../../../../backend/apps/core/api/payload_validators.py) (`optional_int`,
`optional_iso_date`, `optional_uuid`) e i metodi di `PayloadValidator` in
[payload_helpers.py](../../../../backend/apps/core/services/payload_helpers.py) (`optional_uuid`,
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
  failure). ⏳ Resta la prova a mano di §2.4, e serve un `kill -HUP` dopo queste modifiche.

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

[api.md](../api.md) §Envelope risposte non dice se le forme siano ammesse tutte. È una scelta di
modello: **D-1**, ✅ decisa il 2026-11-24: la forma corta.

### 3.2 Il piano (D-1 decisa: `{count, results}`)

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

## 4. Lavoro C — Lo scope emittente di documenti, due copie

`documenti/services/template_service.py` ha una copia propria della lettura dello scope. Accanto
c'è `documenti/services/_scope.resolve_emittente_scope`, che delega a
`PermissionResolver.get_emittenti_pk_ids`. Le due copie divergono sull'utente anonimo: la prima
restituisce `[]`, la seconda dal 2026-11-24 solleva `E_SCOPE_SENZA_UTENTE`. Oggi è difficile
arrivarci, perché la view chiede già il JWT. Il piano: la copia di `template_service` passa da
`_scope` e si ritira. Questo punto non era fra le tre proposte accettate: entra con **D-2**, ✅ decisa il 2026-11-24 (sì, in
questo brief).

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
  (riga 10 di «Chi riparte»).

## 6. Da chiarire (si guardano nel giro che tocca quei file)

* **E-1 — L'emittente dell'utente.** `ParameterService.get_emittente_fiscale_id_for_user` legge
  `config.user_emittenti_fiscali` in Python. `PermissionResolver.get_emittente_for_user` passa da
  `script.fn_resolve_emittente_for_user`, che probabilmente legge la stessa tabella. Il catalogo
  dice che la semantica è diversa (il primo ha il ripiego sul gestore globale). Da verificare se
  la lettura della tabella è doppia: se lo è, il ripiego resta in Python e la lettura passa dalla
  funzione del DB, oppure è una richiesta al team DB.
* **E-2 — `magazzino/db/_helpers.lista_paginata`.** Dalla descrizione del catalogo (L1301) fa lo
  stesso lavoro di `fetch_paged_with_total`, cioè `COUNT(*) OVER ()` più il conteggio di ripiego
  sulla pagina stantia. Il codice non è stato aperto.

## 7. Audit del frontend (2026-11-24)

**Metodo.** Lo stesso di §1: l'indice del catalogo del frontend letto per intero (556 voci),
raggruppato per argomento (lookup e autocomplete, paginazione e liste, polling e debounce, anti-race,
maiuscolo, severity, note, etichette delle tab). Dove le voci si somigliavano si sono aperti il
catalogo e il codice. Stesso limite: le voci si sono confrontate solo dentro i gruppi.

**Esito.** Due doppioni nel codice (F-1, F-2), un BB senza consumatori (F-3), un alias (F-4), due
righe vecchie nel catalogo, due punti da chiarire. ✅ Le proposte F sono accettate da Tid (**D-4**, 2026-11-24).

### 7.1 Doppioni nel codice

* **F-1 — Il debounce di `useServerAutocomplete` è una seconda copia di `useDebouncedAction`.**
  [useServerAutocomplete.js](../../../../frontend/src/core/composables/useServerAutocomplete.js)
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
  [InputMaiuscolo.vue](../../../../frontend/src/core/components/InputMaiuscolo.vue) (codice SDI,
  estensione del civico) e `normalizeUpperNoSpaces` di
  [string.js](../../../../frontend/src/core/utils/string.js) (`@input` su IBAN, codice fiscale e
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
* **F-4 — `resolveTabLabel`** in [navigation.js](../../../../frontend/src/core/navigation.js) è un
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
* ⏳ **A video (Tid):** un autocomplete (cliente in un documento) con una digitazione veloce e un
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
  [numerazione-documenti-e-codici](../../guide/numerazione-documenti-e-codici.md) (la sigla:
  maiuscole e cifre, salvata così) **coerente**;
  [automazione-db](../../guide/automazione-db.md) §4.8 (il codice lo alza il DB) **coerente**;
  [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) (codice fiscale in
  forma sola, dal DB) e [gestione-conti-bancari](../../guide/gestione-conti-bancari.md) (IBAN
  normalizzato dal trigger) **coerenti**: il maiuscolo del FE resta un aiuto di digitazione.
* **Prove:** vitest intero **203 file, 1296 test, verdi**; lint, guard, classi morte e build
  verdi. Il controllo i18n segnalava una chiave emessa dal DB e assente dai locales
  (`anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna`), che non nasceva da questo giro: è la
  voce 3 di §20.7 di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md), e su
  richiesta di Tid è aggiunta in `it.json` ed `en.json` (2026-11-24). Con l'ok di Tid è tolta la chiave
  ritirata `senza_natura_con_titoli_iva`, che non citava più nessuno. Ora il controllo i18n è pulito.
  ⚠️ Nello stesso momento un'altra mano ha alzato in `frontend/package.json` chart.js, oxlint ed
  eslint-plugin-oxlint: lint e build di questa sezione girano sulle versioni di prima.

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
