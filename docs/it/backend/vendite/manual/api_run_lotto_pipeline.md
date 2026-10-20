# API run_lotto_pipeline (Django)

## Scopo

Esporre via HTTP l'avvio della pipeline lotto vendite.

## Contesto

Endpoint applicativo che invoca il servizio Python `run_lotto_pipeline`.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/pipeline/run/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Permesso: `post_permission = "genera_fatture_lotti"` (area `vendite`)
- Body JSON (tutti i campi opzionali):
  - `lotto_id` (int) — `0`/`null` = crea/risolvi lotto
  - `competenza_mese` (date `YYYY-MM-DD`) — mese di competenza
  - `tipo_doc_fiscale_id` (int) — tipo documento fiscale
  - `utility_id` (int) — filtro utility
  - `billing_account_id` (int) — filtro billing account
  - `emittente_soggetto_ruolo_id` (int) — emittente fiscale (ruolo `anagrafiche.soggetti_ruoli`)
  - `lock_batch_id` (uuid) — correlatore lotto (vedi Regole)
  - `meta` (object) — metadati liberi del run
  - `dry_run` (bool JSON) — esegue senza effetti reali. Solo `true`/`false`:
    una stringa (`"true"`, `"1"`) o un numero → `400 E_VALIDATION_INPUT` col
    campo (2026-10-20: prima si accettavano stringhe)
  - `tipo_lotto` (string) — `MASSIVO` (default) o `GIORNALIERO`

> **Esegue UN solo step per chiamata.** Per concatenare gli step fino alla
> conclusione della catena (driver), usare
> [`pipeline/run-until-done/`](api_run_lotto_pipeline_until_done.md).

## Output

- `200`: `{ "data": { "lotto_id": <id>, "status": "ok" }, "meta": { ... } }`
- `400`: payload non valido o errore applicativo pipeline
- `409`: `E_PIPELINE_STATO_LOTTO` — il lotto indicato **non è dentro la propria
  catena di step**: il suo stato fiscale non compare fra quelli configurati per
  la sua combinazione (`tipo_lotto`, `utility_id`, `tipo_doc_fiscale_id`).
  Messaggio: *«Il lotto non è in uno stato da cui la pipeline possa
  proseguire.»*
  ⚠️ *Fatto datato 2026-09-08*: tutte e sei le combinazioni registrate hanno la
  catena `DRAFT → EMESSA → DEFINITIVA → INVIATA`, quindi gli stati fuori catena
  sono `ANNULLATA` e `REGISTRATA`. È la **configurazione di oggi**, non il
  criterio: il criterio è l'appartenenza alla catena, e la catena la decide
  `vendite.fn_list_fatturazione_pipeline_steps` per ogni combinazione.

## Regole

- Valida JSON e formato date (`YYYY-MM-DD`).
- `dry_run` letto con `optional_bool` (booleano JSON stretto, assente = `false`).
- Converte `0` in `null` sugli ID opzionali (`lotto_id`, `tipo_doc_fiscale_id`, `utility_id`, `billing_account_id`, `emittente_soggetto_ruolo_id`).
- **Validazione lookup ID** — `tipo_doc_fiscale_id` e `utility_id`, se valorizzati, sono validati pre-flight contro le rispettive tabelle config (`config.tipi_doc_fiscale`, `config.utilities`) con filtro `attivo = true`. ID inesistenti o non attivi restituiscono `E_PIPELINE_VALIDATION` con dettaglio esplicito.
- `lock_batch_id` è il correlatore del lotto: se passato è **RIUSO** lotto; per creare un lotto nuovo **ometterlo** o passare `null` (il DB lo genera). Riutilizzare un `lock_batch_id` di un lotto `COMPLETATO` produce errore.
- **Risoluzione emittente fiscale** — delegata a `vendite.fn_get_or_create_lotto` nel DB (via helper condiviso `vendite.fn_resolve_lotto_utility_emittente`) con questa priorità:
  1. `emittente_soggetto_ruolo_id` esplicito nel payload → validato e usato direttamente.
  2. Dedotto dal mapping `billing_account_id` → emittente fiscale, se `billing_account_id` valorizzato.
  3. Unico emittente fiscale attivo nel sistema → usato come default.
  4. Se non determinabile → errore bloccante.
- **`emittente_soggetto_ruolo_id` è attributo del lotto**, non del billing account: viene persistito su `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` e usato da tutti i task pipeline (es. `select_attivita`) come fonte primaria. Il valore nei `params` JSON della config pipeline non sovrascrive quello del lotto.
- ⛔ **Il lotto dev'essere dentro la propria catena, e se non ci sta il giro si
  rifiuta** (2026-09-08). Vale solo per un lotto **esistente** (`lotto_id`
  valorizzato): uno appena creato non ha nessuna posizione da rispettare e parte
  dal primo step.
  🔴 Prima il risolutore degli step rispondeva con la catena **intera** su uno
  stato che non è un suo step, e il chiamante ne prende il primo: su un lotto
  `ANNULLATA` veniva scelto lo step `DRAFT` e il runner provava a riportarcelo —
  una **transizione retroattiva**, cioè l'esatto contrario di ciò che quel
  risolutore esiste per impedire. Non riusciva, ma per un accidente del seed:
  `config.stati_doc_fiscale_transizioni` non ha righe in uscita da `ANNULLATA`,
  quindi il guard di transizione a DB rifiutava. Fail-safe per fortuna, non per
  progetto — e il seed può cambiare.
  ⛔ **Non si risolve con «nessuno step»**, che sembra la risposta ovvia: la
  lista vuota significa già «catena esaurita» e porta a marcare il lotto
  `COMPLETATO`. Su un lotto in `ERRORE` sarebbe un errore **cancellato** da un
  giro che non ha eseguito niente.
- ⭐ **Un giro senza step non conclude «Pipeline completata»** (2026-09-08). La
  conclusione **ricalcola sempre** le segnalazioni (`evaluate_lotto_status`)
  prima di scrivere lo stato job: prima lo faceva solo quando c'erano step da
  eseguire, quindi una catena vuota concludeva `COMPLETATO` **senza aver contato
  niente**. La matrice di `set_lotto_job_stato` vieta `ERRORE → COMPLETATO`
  apposta — *«è andata bene» è una conclusione, va guadagnata con un giro* — ma
  l'avvio scrive `IN_ESECUZIONE`, che da `ERRORE` è l'unica porta aperta: il
  divieto non veniva infranto, veniva **aggirato**. Caso reale non fuori catena:
  un lotto `GIORNALIERO` in `ERRORE` fermo all'ultimo step della sua catena
  (`is_massivo_error_rerun` guarda solo i `MASSIVO`).
  ⚠️ Lo spegnimento **automatico** resta: tolte le righe rotte e rilanciato, il
  ricalcolo riporta il lotto a `COMPLETATO` da sé.
- Implementa il pattern standard core `handle_post_json(...)`.
- Endpoint write protetto con obbligo `Idempotency-Key`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_get_or_create_lotto` (creazione/risoluzione lotto + emittente)
- `vendite.fn_resolve_lotto_utility_emittente` (helper condiviso coerenza BA/utility/emittente)
- `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` (attributo lotto persistito)
- Dipendenze indirette via `services/pipeline_runner.py` e `db/pipeline_repository.py`

## Note di migrazione

- L'emittente fiscale era in precedenza dedotto a runtime dai parametri; ora è attributo esplicito del lotto (persistito in DB alla creazione).
- ⚠️ **`E_PIPELINE_STATO_LOTTO` è un riuso dichiarato** (2026-09-08): dice il vero
  all'operatore ed è della classe giusta (`CONFLITTO_STATO` → 409), ma gli altri
  tre punti che lo sollevano parlano di `stato_lotto`, cioè dell'asse del
  **lavoro**, mentre qui l'asse è quello del **documento**. Il codice suo è
  `E_LOTTO_NON_AVANZABILE`, quinto della famiglia `E_LOTTO_NON_*` — è un seed a
  catalogo (`codici_errore.csv` + `messaggi_errore.csv`) e va chiesto al team DB.
  Il giorno che c'è, cambia una stringa nel runner e una nel test.
- ⚠️ Il `message` passato da questo punto **non è decorativo**: sulle rotte
  normali l'envelope usa il testo a catalogo (`policy.user_message`), ma gli
  endpoint del *driver* rispondono `200` con l'esito nel payload e il frontend
  rende `errore.message` — quindi su quel percorso è la frase che l'operatore
  legge. Presidiata da `test_runner_rifiuta_il_giro_su_lotto_fuori_catena`.
