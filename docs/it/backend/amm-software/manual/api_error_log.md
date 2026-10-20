# API error-log — la consultazione di `dbops.error_log` (Django)

## Scopo

Esporre via HTTP, ai tecnici, il registro degli errori: **quale funzione ha
sollevato quale codice, quando, in quale transazione** — con la frase, la
causa e la soluzione **a catalogo** e gli appunti (`context`) **com'erano**.
È il pezzo **E** del piano BE/FE dell'osservabilità
([piano-be-fe-osservabilita-pallino-e-superfici](../../../dev/work-done/piano-be-fe-osservabilita-pallino-e-superfici.md) §4),
l'altra metà del Passo B di [analisi-osservabilita-log](../../../dev/work-done/analisi-osservabilita-log.md).

## Contesto

`dbops.error_log` è il registro **append-only** scritto da
`script.fn_log_and_raise_error` (e dal backend via `ErrorManager`). Fino al
2026-09-19 si leggeva solo con `psql`. Questa consultazione è una **lista
configurabile** (`dbops.error_log`, id 78) dietro la porta dei tecnici, che
oggi è `AdminAPIView` — la stessa di `audit-log/` ed `email-log/` (decisione
D-E1: un livello «tecnici» non esiste ancora; il giorno che nascerà, le tre
si spostano insieme).

Tre layer:

- view `ErrorLogListView` / `ErrorLogExportView` in `apps/amm_software/api/views.py`;
- service `fn_list_error_logs` in `apps/core/services/tracciamento_service.py`
  (accanto a `fn_list_audit_logs`);
- repository `DbopsRepository.list_error_logs` in `apps/core/db/dbops_repository.py`
  (accanto a `list_audit_logs`, whitelist `ERROR_LOG_SORT_COLUMNS`).

## Input

### `GET /api/v1/amm-software/error-log/`

| Query param | Tipo | Note |
| --- | --- | --- |
| `area` | text | **esatto**. ⚠️ Testo libero, non un codice di `config.aree_funzionali`: `error_log.area` non ha FK ed è il primo argomento di `fn_log_and_raise_error` — porta anche `database`, `script`, `dbops`, `backend` |
| `function_name` | text | **prefisso**, `LIKE 'x%'` (non `ILIKE`: l'indice è `text_pattern_ops`, i nomi sono minuscoli per convenzione). `_`, `%` e `\` nel prefisso sono **escapati** (`_prefisso_like`): senza, `fn_get_lotto` avrebbe come prefisso fisso `fn` e scandirebbe la tabella |
| `codice` | text | esatto, normalizzato MAIUSCOLO; risolto **prima** a `messaggio_errore_id` (tutte le lingue del codice) |
| `tx_id` | uuid | esatto — il **ponte** dal giornale di dominio (`script.vw_giornale_entita.tx_id`) agli appunti tecnici della stessa transazione. Non uuid → `400 E_VALIDATION_INPUT` |
| `data_da` / `data_a` | date ISO | su `occurred_at`, giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09), `data_a` incluso. Malformate → `400`. Il floor standard (oggi−60gg al 1° del mese) lo mette il **frontend**: è consultazione, non coda di lavoro |
| `order_by` | text | whitelist `ERROR_LOG_SORT_COLUMNS` (campi fisici del catalogo): `occurred_at` · `area` · `function_name` · `codice` · `classe` · `tx_id`. Fuori whitelist → `400 E_CORE_VALIDATION` (lista ed export; `validate_order_params` nel service). Assente → `occurred_at`. ⛔ `messaggio`, `causa`, `soluzione`, `context` **non ordinano** (frasi) e a catalogo sono `ordinabile = f` |
| `order_dir` | `asc` \| `desc` | assente ⇒ `occurred_at` ripiega **DESC** (regola del 02-09), le altre `ASC` |
| `limit` / `offset` | int | paginazione offset-based (default 25, max 200) |

### `GET /api/v1/amm-software/error-log/export/?formato=csv|xlsx`

Stessi filtri e ordinamento; `limit = EXPORT_MAX_ROWS + 1` per il guard del
troncamento. Colonne dalla configurazione lista dell'operatore
(`build_export_response`, costante di modulo `_LISTA_CODICE_ERROR_LOG = "dbops.error_log"`,
la stessa forma dell'export delle famiglie documento).

## Output

Envelope paginato standard (`count`, `page`, `page_size`, `total_pages`, `results`),
`count` da `COUNT(*) OVER ()` nella stessa valutazione (`fetch_paged_with_total`).

```json
{
  "id": 459005,
  "occurred_at": "2026-09-19T08:44:12.572904+00:00",
  "area": "vendite",
  "function_name": "fn_escludi_documento_da_giro",
  "codice": "E_PARAMETRO_INVALIDO",
  "classe": "DATO_ERRATO",
  "messaggio": "Parametro non valido: %s",
  "causa": "Un parametro obbligatorio e' nullo o ha un valore non ammesso.",
  "soluzione": "Verificare i parametri passati alla funzione.",
  "tx_id": "01a0b8d6-6151-7e64-813a-a007a9873b29",
  "context": {"parametro": "p_motivo"}
}
```

- `codice`, `messaggio`, `causa`, `soluzione` arrivano dal catalogo
  (`config.messaggi_errore`, JOIN sull'id della riga); **`classe`** da
  `config.codici_errore` (LEFT JOIN sul codice): è il dato che distingue un
  **guasto** (`TECNICO`) da un **rifiuto legittimo** — la domanda che il
  registro, letto da solo, non sapeva fare.
- ⚠️ `messaggio` è la frase **a catalogo**, coi suoi `%s`: i valori con cui è
  stata composta non sono nel registro. Non si ricostruisce.
- ⚠️ **`context` si espone com'è.** Sono gli appunti del tecnico e «non va
  ripulito o riscritto per renderlo presentabile» (vincolo del Passo A): un
  tentativo di renderlo leggibile è il loop che il vincolo esiste per spezzare.

## Regole

- ⭐ **Ogni filtro della whitelist ha un indice da cui partire** (P-3,
  `20260919-06`; `dbops/manual/error_log.md` §indici), ed è stato **provato
  con `EXPLAIN` sul DB vero il 19-09** (fatto datato, 147.716 righe dal 16-08):
  `function_name` → `ix_error_log_function_name_occurred_at` con
  `~>=~`/`~<~` (il `text_pattern_ops` lavora, l'escape del `_` tiene);
  `tx_id` → `ix_error_log_tx_id`; `area + data` → bitmap su
  `ix_error_log_area_occurred_at`; una finestra di date stretta →
  `ix_error_log_occurred_at`. ⚠️ `area` o `codice` da soli, e una finestra che
  copre quasi tutto il registro, vanno in `Seq Scan` **per scelta del
  planner** (la selettività non giustifica l'indice), non per un indice
  mancante — e il `COUNT(*) OVER ()` deve comunque attraversare il perimetro.
- La lista **è esente** dal cancello di perimetro emittente
  (`perimetro_emittente = false` a catalogo, esenzione dichiarata in
  `core/tests/test_perimetro_emittente_copertura.py`): un errore tecnico non
  ha un'azienda da cui arrivare. ⛔ Per questo la view **non** dichiara
  `lista_codice` (che su `AdminAPIView` sarebbe un cancello inerte spacciato
  per copertura): il codice della lista è una **costante di modulo**
  (`_LISTA_CODICE_ERROR_LOG`) letta dal solo export — la forma già in uso per
  `famiglie/`, l'altro export su `AdminAPIView`. ⚠️ Ne discende che la coppia
  lista/export è **fuori** dal perimetro di `test_export_lista_codice_pari`
  (che legge `lista_codice`), come `famiglie/`: il presidio della coppia è
  `test_error_log_api` (test 2).
- Sola lettura: nessun `Idempotency-Key`; JWT + `SUPER_ADMIN`.

## Dipendenze DB

- `dbops.error_log` (+ i quattro indici di lettura del `20260919-06`)
- `config.messaggi_errore`, `config.codici_errore`
- `ui.lista_definizione` / `ui.lista_colonna` / `ui.lista_preset*` — lista
  `dbops.error_log` (id 78, colonne 875-884, seed CSV `80_data/sql/ui/`)

## Frontend

`ErrorLogListView` (`/strumenti/diagnostica/error-log`, voce «Errori tecnici»
del gruppo Strumenti → Diagnostica, accanto ad Audit Log ed Email log; fino al
2026-10-06 stava in Amm. software): `<ListaConfigurabile codice="dbops.error_log">`,
store `amministrazione/stores/errorLog.js` (`createListaStore`, `userScoped`),
toolbar con i sei filtri, export. Kebab di riga: **Dettaglio**
(`ErrorLogDettaglioDrawer` — testata, frase/causa/soluzione, `context` reso dal
BB `JsonBlocco`), **Giornale di questa transazione** (deep-link
`/vendite/giornale?tx_id=…`, visibile se l'area vendite è raggiungibile: è
un'offerta, non una promessa), **Copia tx_id**. Il deep-link in ingresso
(`?tx_id=`) si legge in `onActivated` e azzera il floor temporale: un filo
attraversa qualunque data.

## Test

- `apps/amm_software/tests/api/test_error_log_api.py` (6): porta, rotte,
  normalizzazione dei filtri, `400` su uuid/data malformati, envelope.
- `apps/core/tests/db/test_dbops_error_log_repository.py` (6): whitelist e
  ripiego dell'ordinamento, escape del prefisso `LIKE`, valori nei `params`;
  **una lettura vera** sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`) che
  attraversa ogni filtro della whitelist e verifica il JOIN col catalogo.
- I presidi trasversali delle liste (`test_liste_configurabili_seed`,
  `test_perimetro_emittente_copertura`, `test_export_lista_codice_pari`).

## Note di migrazione

- 2026-09-19: nasce con il pezzo E. La lista a catalogo è **dato** nei CSV di
  `80_data/sql/ui/` (mirror `runOnChange`): sul DB di sviluppo compare al
  prossimo `db-migrate`; fino ad allora `export/` risponde
  `E_UI_LISTA_NON_TROVATA` e la pagina non ha colonne.
