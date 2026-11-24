# Brief BE/FE — Audit dei building block: i BB che fanno la stessa cosa

## ⏭️ Chi riparte — aggiornato al 2026-11-24

**Riparte: Tid**, con le decisioni D-1…D-4. Le parti che non le aspettano (A e il catalogo, §5) può già prenderle il team BE/FE.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team BE/FE | ✅ Audit del backend (2026-11-24) | §1 | — |
| 2 | team BE/FE | ✅ Audit del frontend (2026-11-24) | §7 | — |
| 3 | Tid | D-1 (forma dell'envelope delle liste), D-2 (scope di documenti), D-3 (nome dei due `validate_order_params`), D-4 (le proposte F del frontend) | §8 | 1, 2 |
| 3-bis | team BE/FE | Lavoro F: F-1…F-4, catalogo FE, E-3 ed E-4 | §7 | 3 (D-4) |
| 4 | team BE/FE | Catalogo BE: ritirare la voce vecchia, fondere le righe doppie, rigenerare l'indice | §5 | — |
| 5 | team BE/FE | Lavoro A: le funzioni della view delegano a `PayloadValidator`, i service lasciano le funzioni della view, il FE manda `null` al posto di `""` | §2 | — |
| 6 | team BE/FE | Lavoro B: un BB core per l'envelope delle liste, le copie si ritirano | §3 | 3 (D-1) |
| 7 | team BE/FE | Lavoro C: lo scope di `template_service` passa da `_scope` | §4 | 3 (D-2) |
| 8 | team BE/FE | I due punti da chiarire, guardati nel giro che tocca quei file | §6 | — |
| 9 | team BE/FE | Archiviazione in `work-done/` | — | 3-bis, 4–8 |

**Decisioni aperte di Tid:** D-1, D-2, D-3, D-4 (§8). Le tre proposte dell'audit del backend sono
accettate (Tid, 2026-11-24): A, B, e la pulizia del catalogo. **Da committare:** questo brief.

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
modello: **D-1**.

### 3.2 Il piano (dopo D-1)

* **B1 — Il BB.** Una sede core per la forma decisa, accanto a `collezione_completa` in
  `core/services/list_helpers.py`, con un nome che dice la natura (lista paginata, col totale
  della query).
* **B2 — Le copie si ritirano nello stesso giro**: i punti di §3.1, e `risposta_paginata` di
  magazzino. Se D-1 sceglie la forma corta, anche `paginated_envelope` / `envelope_da_offset`
  passano alla forma decisa, e la pagina effettiva dei cruscotti resta solo dove serve.
* **B3 — FE.** Se D-1 toglie `page` dalla risposta dei cruscotti, `usePagedDashFetch` si allinea
  alla forma che la sostituisce. Altrimenti al FE non serve niente.
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
`_scope` e si ritira. Questo punto non era fra le tre proposte accettate: entra con **D-2**.

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
righe vecchie nel catalogo, due punti da chiarire. Le proposte F aspettano l'ok di Tid (**D-4**).

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

## 8. Decisioni di Tid

* **D-1 — La forma dell'envelope di una lista paginata.** Raccomandazione: una forma sola,
  `{count, results}`, dove `count` è il totale della query. La finestra si chiede con
  `limit`/`offset` (un dialetto solo, Tid 2026-10-21), quindi `page`/`page_size`/`total_pages`
  nella risposta ripetono una finestra in una lingua che la richiesta non parla più. Fa eccezione
  la pagina **effettiva** dei cruscotti, che è un dato vero (il BE ha spostato la finestra). Si
  dichiara con un campo proprio, per esempio `offset` effettivo, solo dove `query_paged_view` la
  produce. In alternativa: si tengono le due forme, e il BB nuovo dà la sede alla forma corta
  accanto a `paginated_envelope`.
* **D-2 — Lavoro C dentro questo brief?** È un doppione nello stesso dominio, piccolo, della stessa
  natura degli altri.
* **D-3 — I due `validate_order_params`.** Raccomandazione: si rinomina quello della ricerca
  universale (per esempio `validate_order_params_ricerca`), in modo che l'omonimia non possa più
  far importare la funzione sbagliata. In alternativa: resta com'è, documentato.
* **D-4 — Le proposte del frontend (§7).** F-1 (`useServerAutocomplete` sopra `useDebouncedAction`
  e `useFetchVersion`), F-2 (`InputMaiuscolo` con `senzaSpazi`, ritiro di `normalizeUpper*`, il
  `codice` dell'emittente con `app-codice-input`), F-3 (ritiro di `usePagination`), F-4 (ritiro
  dell'alias `resolveTabLabel`, o lasciarlo dichiarato). Raccomandazione: tutte e quattro. F-1 e F-2
  correggono difetti che si vedono a video.
