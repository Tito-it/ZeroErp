# Task di pipeline di fatturazione (contratto BE)

## Scopo

Il contratto di un **task di pipeline**: cos'è, quali cinque pezzi servono
perché esista, che forma ha il suo handler Python, e come si aggiunge un task
nuovo senza lasciare una pipeline armata a vuoto.

Non è un endpoint HTTP: i task non si invocano dal client. Girano dentro uno
**step** della pipeline di fatturazione, che a sua volta è mosso dai verbi del
cockpit ([api_fatturazione](api_fatturazione.md)) o dai worker/cron. Gli esiti
si leggono da [api_lotto_task_runs](api_lotto_task_runs.md).

## Contesto

Uno **step** è la coppia `(stato_doc_fiscale, tipo_lotto)`: DRAFT, EMESSA,
DEFINITIVA, INVIATA. La riga di `vendite.fatturazione_pipeline` che risolve
quello step porta, nella colonna `processi`, l'**elenco ordinato dei task** da
eseguire — ed è configurazione, non codice:

```json
[{"task": "numera_fatture", "fase": "Numerazione fatture",
  "params": {"implementation_key": "default"}}, …]
```

`PipelineStepExecutor.execute_step` legge quell'elenco e per ogni voce risolve
l'handler Python. ⚠️ **I task girano in sequenza, ciascuno nella propria
transazione**: non c'è un `atomic` che avvolga lo step. Il fallimento del terzo
task non annulla i primi due — è il motivo per cui l'ordine, più sotto, è una
cosa seria.

## I cinque pezzi di un task

Un task esiste solo se ci sono **tutti e cinque**. Ne mancasse uno, il difetto
si vede in momenti diversi — e il peggiore si vede in esercizio.

| # | Pezzo | Dove | Se manca |
| --- | --- | --- | --- |
| 1 | `task_code` a registro | `dbops.pipeline_task_registry` (CSV `80_data`) | l'implementazione non si risolve |
| 2 | `handler_code` | `dbops.pipeline_task_registry_impl`, `implementation_key='default'`, **`is_default=true`** | l'implementazione esiste e non viene scelta |
| 3 | **handler Python** | `PipelineStepExecutor.handler_registry` | 🔴 `E_TASK_IMPLEMENTATION_NOT_FOUND` **a runtime**, dopo che i task precedenti hanno già scritto |
| 4 | il task nel JSON `processi` | `vendite.fatturazione_pipeline` (CSV `80_data`) | il task non gira mai (e nessuno lo segnala) |
| 5 | `task_policy` | `vendite.fatturazione_pipeline_task_policy` | nessun tracing: niente `task_run`, niente resume — il task gira «cieco» |

🔴 **La coppia 1+4 e il pezzo 3 sono due metà dello stesso cambiamento, e
possono essere applicate separatamente.** Il seed DB è verde e corretto in sé, e
nel frattempo arma una pipeline che nessun test copre. È successo il 2026-08-18
con `popola_fatture_rettifiche`: il task era nelle pipeline **vive** con
l'handler ancora da scrivere, e il primo giro DEFINITIVA avrebbe **numerato** —
irreversibile — per poi morire prima della stampa.

✅ **Dal 2026-08-19 c'è un cancello**, e il presidio non è più ricordarsene:
`apps/vendite/tests/db/test_pipeline_task_handler_guardrail.py` confronta ciò
che le **pipeline attive chiedono** (database) con il **dizionario Python vivo**
`PipelineStepExecutor.handler_registry`, e nomina il task, la pipeline e
l'`handler_code` che manca. Opt-in `ZEROERP_TEST_DB_E2E=1`, acceso in CI.

⚠️ Legge gli **oggetti reali**, non una mappa-specchio dei fixture: uno specchio
non prova che l'originale esista, ed è esattamente il modo in cui il difetto era
passato. Stessa idea, a grana di slice, in
`test_popola_fatture_rettifiche_agganciata_al_registry_reale`.

## Input dell'handler

Firma unica, tutti keyword-only:

```python
def _handle_<task>_task(
    self, *, task, fn_name, lotto_id, stato_doc_fiscale_id,
    context: LottoContext, params: dict, dry_run: bool,
) -> TaskEsitoParziale | None
```

- `params` — il dict `params` della voce JSON. Convenzioni: `implementation_key`
  (risoluzione handler), `batch_size`, `fn` (override della funzione SQL);
- `fn_name` — il valore di `params["fn"]`, **validato** contro
  `VenditePipelineRepository.ALLOWED_TASK_FUNCTIONS`: una funzione non ammessa
  è `E_TASK_NOT_ALLOWED`, non una chiamata. La whitelist è per `task_code`, e
  `None` significa *task Python-only* (nessuna fn SQL);
- `context` — `LottoContext` (competenza, utility, tipo doc, emittente);
- `dry_run` — il gate sta in `_run_validated_task`: si valida e **non** si
  esegue.

## Output dell'handler

`None` = giro completato. `TaskEsitoParziale(error_code, error_message, meta)` =
giro completato **con una parte delle fatture in errore**.

⚠️ **`TaskEsitoParziale` non solleva, ma chiude il `task_run` in ERRORE** — e la
differenza non è formale (D-Q p.3):

* con **COMPLETATO** il resolver darebbe **SKIP** al rilancio, e la correzione
  dei dati non verrebbe mai riletta;
* con un **raise** il rollback cancellerebbe anche il lavoro delle fatture sane.

## Regole

### Fail-fast oppure esito parziale: si decide da CHI STA A VALLE

Non è una preferenza di stile, ed è la scelta che i task per-fattura sbagliano
più spesso.

| Comportamento | Quando | Esempi |
| --- | --- | --- |
| **Esito parziale** | nessuno consuma l'uscita del task **nello stesso step**: la fattura rotta è una riga da rilavorare | `snapshot_indirizzi_lotto`, `genera_scadenze_lotto` |
| **Fail-fast** per fattura | un task successivo **consuma** ciò che questo produce: proseguire non lascerebbe una riga da rilavorare, produrrebbe un documento incompleto | `numera_fatture`, `popola_fatture_rettifiche` (la stampa legge il legame per il blocco `DatiFattureCollegate` di una TD04) |

Il fail-fast per-fattura si scrive con `_run_per_fattura_task`, che logga
l'errore con scope FATTURA e poi rilancia.

#### Il codice del database non si perde nel rilancio (2026-08-21)

Un task che delega a una madre DB solleva un `DatabaseError` che porta il
**codice di dominio** nel campo strutturato (`CONSTRAINT` su `SQLSTATE P0001`,
vedi `apps/core/services/db_error_fields.py`). Fino al 2026-08-21
`_run_per_fattura_task` lo appiattiva su `E_TASK_FATTURA` — sia nel log FATTURA
sia nella risposta.

🔴 **Misurato sul caso che l'ha fatto emergere**: la guardia nuova sulla
numerazione delle note di credito (`E_FATTURA_RETTIFICATA_SENZA_NUMERO`, 937)
dice *«numera prima la fattura NNN»*, e all'operatore arrivava *«Errore su
singola fattura durante task pipeline»*. La guardia funzionava; era
illeggibile.

Ora l'helper legge il codice **una volta** e con quella risposta decide tre
cose: il codice del `ServiceError`, il messaggio (`diag.message_primary`, il
solo `RAISE` senza lo stack PL/pgSQL) e se scrivere nel diario
(`log_to_db=False` quando il codice viene dal campo strutturato: in quel caso
`script.fn_log_and_raise_error` **ha già scritto** la sua riga — decisione
DB+BE del 2026-08-19). `E_TASK_FATTURA` resta il ripiego per tutto ciò che il
database non ha nominato: errori Python, `RuntimeError`, guasti tecnici.

⚠️ È lo stesso difetto già corretto in `_fail_task_run_safely` per il **diario
dei task run**, che era rimasto aperto sulla strada che l'operatore **vede**.
Vale per ogni task per-fattura, non solo per la numerazione.

### L'ordine dentro lo step si DICHIARA

`PipelineStepExecutor._TASK_ORDER_DEPENDENCIES` mappa `task → task che devono
precederlo`, e la verifica gira **prima che il primo task dello step scriva**.

Il perimetro è stretto di proposito: ci vanno solo le coppie in cui invertire
l'ordine produce un risultato **sbagliato** invece di un errore. Due esclusioni,
entrambe legittime: se il predecessore non è in questo step non si fallisce (può
vivere in uno step precedente), e in **rollback** non si verifica (la catena di
annullamento percorre i passi a ritroso).

⚠️ **Non basta l'ordine del seed.** La configurazione la scrive un altro team, e
una riga girata deve fermarsi prima, non scoprirsi a documenti numerati.

Oggi ci sono tre dipendenze: `genera_scadenze_lotto → ricalcola_iva_lotto` (la
base delle rate è `totale_a_pagare`, che nasce dal ricalcolo),
`popola_fatture_rettifiche → numera_fatture` e `numera_fatture →
consuma_plafond_lotto` (il consumo del plafond spezza le righe, e dopo la
numerazione il documento è oltre la soglia di congelamento: la scrittura verrebbe
rifiutata). ⚠️ Finché `consuma_plafond_lotto` non è nel seed della pipeline la
terza non scatta (predecessore assente = configurazione valida).

### E dentro un task, l'ordine delle FATTURE (2026-08-21)

⚠️ Cosa diversa dalla precedente: quella ordina i **task** dentro lo step,
questa le **fatture** dentro un task.

`numera_fatture` numera in **id crescente** — `sorted()` esplicito in
`_handle_numera_fatture_task`, non l'`ORDER BY` del repository. È un
**requisito**, da quando `fn_numera_fattura_opz_emessa` rifiuta di numerare un
documento le cui righe rettificano righe di una fattura ancora senza numero
(`E_FATTURA_RETTIFICATA_SENZA_NUMERO`): il giro è fail-fast, quindi una nota di
credito incontrata **prima** della sua fattura fermerebbe l'intero step.

L'id crescente **è** l'ordine di dipendenza, e non per caso: perché un accredito
sia possibile la merce dev'essere già stata fatturata
(`E_ACCREDITO_ATTIVITA_NON_FATTURATA`), quindi la fattura rettificata nasce
sempre prima della nota che la corregge.

📌 **Perché `sorted()` e non l'`ORDER BY` della query.** Non è una ripetizione:
rende il task **indipendente** dal repository. `list_fatture_by_lotto` ha due
chiamanti e il suo ordinamento è lì per la stabilità del risultato — chi un
giorno lo cambiasse per un'altra ragione non ha modo di sapere che qui dentro ci
si appoggia, e il guasto sarebbe uno step fermo a metà lotto con un codice che
parla d'altro.

⛔ Il caso **cross-lotto** non è coperto da nessun ordinamento e non deve
esserlo: se la fattura rettificata sta in un lotto ancora in bozza, il rifiuto
della madre DB è la risposta giusta.

### Anche i task FALLITI finiscono nel diario (2026-08-21)

`fn_fail_lotto_task_run` gira **dentro** la transazione dello step, che il
fallimento annulla: la riga «questo task è andato in errore» spariva insieme al
task. Il diario registrava quindi solo ciò che era andato bene — misurato prima
del fix: **128 COMPLETATO, 56 ANNULLATO, zero ERRORE** su 184 run, mentre i
fallimenti c'erano.

Ora il gestore d'eccezione del runner (`_persist_task_run_error_safely`, fuori
dalla transazione) **riscrive** il run fallito: rifà la coppia `start` + `fail`,
perché `fn_start_lotto_task_run` è la sola che sa calcolare il `tentativo` e
ricrearlo a mano significherebbe copiarne la regola in un secondo posto.

⚠️ Solo dove il **tracing è attivo**: le coordinate viaggiano sull'eccezione e
vengono attaccate solo se il task aveva un `task_run` aperto. Dove non c'è
`task_policy` non c'è diario, ed è una scelta di configurazione — non va
aggirata scrivendo righe che il giro riuscito non scriverebbe.

📌 A differenza della marcatura sulla fattura, i run **si accumulano**: la
bandiera racconta l'ultimo tentativo, lo storico dei tentativi li racconta
tutti.

### Tracing e resume (`task_policy`)

Il tracing esiste **solo se** c'è una riga in
`vendite.fatturazione_pipeline_task_policy` per la coppia `(pipeline_id,
task_code)`. Quando c'è, prima di eseguire si risolve la modalità con
`fn_resolve_lotto_task_execution_mode`:

| Modalità | Effetto |
| --- | --- |
| `RUN` | esegue e apre un `task_run` |
| `SKIP` | non esegue (il task ha già chiuso COMPLETATO) |
| `RESUME` | riesegue: è ciò che produce un `task_run` chiuso in ERRORE |
| `RESET_REQUIRED` | 🔴 solleva `E_TASK_RESET_REQUIRED`: serve un reset prima |

`resume_mode` della policy dice **cosa** si riprende: `RESUME_TASK` (dal task
fallito), `RESUME_STEP` (dall'inizio dello step), `RESET_STEP`. `annullabile`
dice se il task ammette il rollback.

⭐ **Idempotenza**: un task con `RESUME_TASK` verrà rieseguito, quindi deve poter
girare due volte senza raddoppiare. `popola_fatture_rettifiche` lo ottiene con
`ON CONFLICT DO NOTHING`; chi scrive un task nuovo deve dire **come** lo
ottiene.

## Catalogo dei task (misurato il 2026-08-19)

Registro: 21 task. In pipeline: **12**.

| Step (pipeline) | Task, in ordine |
| --- | --- |
| **DRAFT** (1 massivo, 8 giornaliero) | `pull_attivita_da_commessa` · `select_attivita` · `generate_fatture_righe` · `snapshot_indirizzi_lotto` |
| **EMESSA** (3, 2) | `genera_fondi_source_lotto` · `applica_fondi_lotto` · `ricalcola_iva_lotto` · `genera_scadenze_lotto` |
| **DEFINITIVA** (4, 6) | `numera_fatture` · `popola_fatture_rettifiche` · `stampa_documenti_lotto` |
| **INVIATA** (5, 7) | `prepare_sdi_payload_lotto` |
| **rollback** (3) | `reset_lotto_draft` |

⚠️ **Sette task sono a registro, hanno un `handler_code`, e NON hanno un handler
Python**: `acquisisci_preventivi`, `acquisisci_contratti`, `acquisisci_ordini`,
`acquisisci_attivita_consumi`, `normalizza_attivita`, `valida_attivita`,
`deduplica_attivita`. Oggi **non sono in nessuna pipeline**, quindi dormono e
non fanno danno. 🔴 Ma il giorno in cui qualcuno ne mette uno in un JSON
`processi` il giro muore con `E_TASK_IMPLEMENTATION_NOT_FOUND` **dopo** che i
task precedenti hanno scritto: sono esattamente la trappola descritta sopra, già
armata a metà. Prima di usarne uno: scrivere l'handler, oppure ritirare la riga
di registro.

`close_lotto` ha l'handler ed è `attivo=false` a registro: spento di proposito.

⛔ **I sette non sono una lista di eccezioni: sono un registro del DEBITO**, e
vivono in `DEBITO_TASK_SENZA_HANDLER` dentro il cancello. Può solo calare, ed è
sorvegliato nei tre versi: uno nuovo → rosso; uno che **ottiene** il suo handler
→ rosso finché la riga non viene tolta; uno **ritirato** dal registro → rosso
come riga orfana.

## Come si aggiunge un task

1. **DB** (team DB): riga in `pipeline_task_registry`, riga in
   `pipeline_task_registry_impl` (`is_default=true`), il task nel JSON
   `processi` della/e pipeline giuste, riga di `task_policy` con `resume_mode`;
2. **BE**: l'handler `_handle_<task>_task`, registrato in `handler_registry` con
   il **`handler_code` esatto** del punto 1;
3. **whitelist**: la fn SQL ammessa in `ALLOWED_TASK_FUNCTIONS` (o `None` se il
   task è Python-only);
4. **ordine**: se invertirlo produce un risultato sbagliato, la dipendenza in
   `_TASK_ORDER_DEPENDENCIES`;
5. **test**: quelli sul comportamento — dry-run, esito parziale o fail-fast,
   ordine rifiutato se invertito. L'aggancio (registro → handler → policy) lo
   verifica già il cancello, che diventa verde da sé quando i cinque pezzi ci
   sono tutti;
6. **consegna**: 1 e 2 vanno **insieme**. Se il seed arriva prima dell'handler,
   la pipeline è armata a vuoto.

## Dipendenze DB

- `dbops.pipeline_task_registry`, `dbops.pipeline_task_registry_impl`
- `vendite.fatturazione_pipeline` (`processi`, `rollback`),
  `vendite.fatturazione_pipeline_task_policy`
- `vendite.fn_resolve_lotto_task_execution_mode`,
  `vendite.fn_start_lotto_task_run`, `vendite.fn_complete_lotto_task_run`,
  `vendite.fn_fail_lotto_task_run`
- `vendite.fatturazione_lotti_task_runs` (gli esiti, letti da
  [api_lotto_task_runs](api_lotto_task_runs.md))

## Riferimenti

- Esecutore: `apps/vendite/services/pipeline_step_executor.py` · Repository:
  `apps/vendite/db/pipeline_repository.py` (`ALLOWED_TASK_FUNCTIONS`, i
  `run_*_task`, il tracing) · Runner: `pipeline_runner.py`.
- Test: `apps/vendite/tests/services/test_pipeline_step_executor.py`
  (comportamento, con mock) · `apps/vendite/tests/db/test_pipeline_task_handler_guardrail.py`
  (il cancello configurazione ↔ handler, su DB reale).
- Segnaposto senza handler: `TASK_SENZA_HANDLER` in `pipeline_step_executor.py`
  (`noop`, `log_only`) — costante e non literal, perché la legge anche il
  cancello.
- Fan-out isolato (savepoint per elemento, esito a tre stati):
  `apps/core/services/fan_out.py`.
