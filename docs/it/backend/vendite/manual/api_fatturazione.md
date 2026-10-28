# API Fatturazione — cockpit processi (Django)

## Scopo

Documentare gli endpoint di **comando** del cockpit di fatturazione (Fase C): i
verbi «Fattura» e «Rendi definitive» del mese di competenza, la numerazione del
singolo lotto, la ristampa massiva, la **finestra di numerazione** e la lettura
degli esiti. L'approvazione massiva del mese (`POST
fatturazione/approva-competenza/`, permesso `approva_attivita_commessa`) è
documentata in [api_commessa_attivita.md](api_commessa_attivita.md). Sono le azioni che
rendono azionabile la Dashboard Competenza, riusando **le stesse primitive del
batch** (I-1: un solo processo, due modi di avvio).

## Contesto

I verbi del mese sono **non bloccanti** (I-3): non eseguono il lavoro nella
richiesta HTTP, ma **accodano un job** nella coda lavori generica
`dbops.coda_lavori` (variante DB-native del pattern task-queue, senza broker) e
rispondono subito con l'handle del job. Il worker `draina_coda_lavori` (systemd
timer) lo esegue poi sotto l'identità dell'operatore (RLS attiva). Il FE segue
l'avanzamento via **polling** dello stato del job.

La numerazione del **singolo** lotto e la **ristampa** sono invece sincrone
(cardinalità 1 / accodamento veloce). Gate fiscale **I-7**: «Fattura» (pre-fiscale,
ferma a EMESSA) e «Rendi definitive» (numerazione) hanno **endpoint e permesso
distinti**; la stampa non numera mai.

Tre layer: `views.py` (`ApiFatturazione*`) → `services/pipeline_service.py` +
`fatturazione_driver_service.py` + handler coda → repository (`VenditeRepository`,
`VenditePipelineRepository`, `CodaLavoriRepository`).

## Input

Header sicurezza su tutti: `Authorization: Bearer <access_token>`. Tutti i POST
richiedono `Idempotency-Key: <uuid>` (header). Area funzionale: `vendite`.

### 1. Giro «Fattura competenza» (C-3, non bloccante)

- `POST /api/v1/vendite/fatturazione/run/` · permesso `genera_fatture_lotti`
- Body: `{ "competenza_mese": "YYYY-MM-DD" [, "fino_a_stato": "<codice>"]
  [, "gruppi": ["<gruppo_key>", …]] [, "data_documento": "YYYY-MM-DD"] }`
- Corsia **differita**: si ferma a **EMESSA** (D-1), perimetro cumulativo
  `competenza ≤ M`. Scope emittente **catturato** all'accodamento.

#### 1-bis. Emissione mirata (`gruppi`, 2026-07-27)

Lo stesso endpoint, con `gruppi` valorizzato, fattura **solo** i gruppi
fatturabili indicati — un documento sorgente (PRV-0012, CTR-0007…) oppure gli
oneri di una commessa. Un solo verbo, due perimetri: il processo è identico
(invariante I-1), cambia solo cosa entra.

- Le chiavi arrivano da `GET /vendite/dashboard-competenza/gruppi/` e **non si
  costruiscono a mano**: le produce `vendite.fn_build_gruppo_fatturabile_key`.
- Corsia **`mirata`**: a differenza della differita **non filtra per corsia**
  (`p_fatturazione_immediata = NULL`). Non è una svista — la lista dei gruppi
  non conosce la corsia, quindi mostra anche i gruppi di commesse a
  fatturazione immediata: filtrare li renderebbe selezionabili a video e
  produttivi di **zero lotti, in silenzio**. La selezione esplicita
  dell'operatore è un perimetro più preciso dell'instradamento automatico.
  Fermata a EMESSA invariata (gate fiscale I-7).
- **Il criterio è uno stato del lotto, non un parametro**: il driver scrive le
  righe di `vendite.fatturazione_lotti_gruppi` nella **stessa transazione** in
  cui crea il lotto. Da lì in poi vive nel `LottoContext`, quindi un *rerun* o
  un *avanza step* dal `LottoDrawer` riproduce lo stesso perimetro invece di
  allargarlo.
- **Idempotenza**: la chiave di *business* della coda (forma completa in
  §Regole) include un digest dell'insieme dei gruppi — senza, due emissioni mirate sullo stesso mese e
  scope con gruppi diversi cadrebbero sullo stesso job vivo e la seconda
  verrebbe assorbita in silenzio. Senza `gruppi` il digest è vuoto: la chiave
  del giro di massa resta identica a prima.
- Validazione: `gruppi` non-lista, elemento non stringa/vuoto, lista vuota
  (ambigua fra «niente» e «tutto») o oltre 200 elementi → **400**
  `E_VALIDATION_INPUT`.
- **L'esito è una LISTA di lotti**: `result.lotti = [{lotto_id,
  tipo_doc_fiscale_id, competenza_mese}, …]`. Un gruppo con righe di
  `tipo_doc_fiscale` diverso finisce in terne — e quindi lotti — diversi. Il FE
  offre N «vai al lotto», non uno.

### 2. Polling stato job (C-3)

- `GET /api/v1/vendite/fatturazione/run/<job_id>/`
- Ownership **scope-based**: l'operatore vede i job della propria `scope_key`
  (whitelist emittenti) — due operatori con la stessa whitelist condividono il
  giro deduplicato; un job di altro scope → **404** (indistinguibile da inesistente).

### 3. «Rendi definitive competenza» (C-4 perimetro, non bloccante)

- `POST /api/v1/vendite/fatturazione/numera/` · permesso `numera_fatture_lotti`,
  dichiarato sulla view: la numerazione di perimetro non ha **un** documento da cui
  leggere la riga del passaggio. È la stessa azione della riga EMESSA → DEFINITIVA.
- Body: `{ "competenza_mese": "YYYY-MM-DD" [, "lotti": [<int>, …]] [, "data_documento": "YYYY-MM-DD"] }`
- Accoda un job `FATTURAZIONE_NUMERA`: esegue lo step DEFINITIVA sui **lotti
  EMESSA** del mese. Polling via `run/<job_id>/`.
- `lotti` (facoltativo): il perimetro **selezionato**, id interi > 0
  (deduplicati). Assente = tutti i lotti EMESSA del mese; **lista vuota → `400
  E_VALIDATION_INPUT`**, mai «tutti»: su un atto fiscale non si indovina. Non
  lista o elemento non intero positivo → `400 E_VALIDATION_INPUT`. Lo stato
  EMESSA si applica comunque: un lotto selezionato ma non emesso non viene
  numerato. Il digest della selezione entra nella chiave di business.

⭐ **Lo step DEFINITIVA ha tre task, dal 2026-08-18** (prima due):

```text
numera_fatture  →  popola_fatture_rettifiche  →  stampa_documenti_lotto
```

`popola_fatture_rettifiche` proietta il legame documento-a-documento delle
**note di credito** (`vendite.fatture_rettifiche`) da ciò che le righe già
dicono (`fatture_righe.riga_rettificata_id`). Idempotente
(`ON CONFLICT DO NOTHING`), non cancella mai.

⚠️ **Sta in mezzo, e le due ragioni non sono intercambiabili**: *dopo* la
numerazione perché prima un reset di lotto può ancora passare e
`fn_cleanup_fatture_by_ids` **non** cancella `fatture_rettifiche` (la FK non è
`ON DELETE CASCADE`); *prima* della stampa perché una TD04 porta
`DatiFattureCollegate`, cioè numero e data del documento rettificato. L'ordine è
**dichiarato** in `_TASK_ORDER_DEPENDENCIES` e verificato **prima** che il primo
task scriva, non lasciato al solo seed.

⚠️ **Fail-fast per fattura**, a differenza di `genera_scadenze_lotto` e
`snapshot_indirizzi_lotto` che chiudono in esito parziale: qui la stampa viene
subito dopo e **consuma** il legame, quindi proseguire non lascerebbe una riga
da rilavorare — stamperebbe un documento fiscale incompleto. La `task_policy` è
`RESUME_TASK`: il rilancio riprende dal task fallito, e l'idempotenza rende
innocuo il secondo giro.

### ⭐ `numera_fatture` numera in id crescente (2026-08-21)

Dal 2026-08-21 `fn_numera_fattura_opz_emessa` **rifiuta**
(`E_FATTURA_RETTIFICATA_SENZA_NUMERO`, 937) di numerare un documento le cui
righe rettificano righe di una fattura ancora senza numero: la TD04 deve citare
numero e data del documento corretto. Poiché il giro è fail-fast, una nota di
credito incontrata **prima** della sua fattura fermerebbe l'intero step.

L'ordine è quindi **esplicito nel task** (`sorted()` in
`_handle_numera_fatture_task`) e non ereditato dall'`ORDER BY` del repository —
che ha due chiamanti e potrebbe cambiare per un'altra ragione. L'id crescente
*è* l'ordine di dipendenza: perché un accredito sia possibile la merce dev'essere
già stata fatturata, quindi la fattura rettificata nasce sempre prima della nota.
⛔ Il caso **cross-lotto** deve invece fermarsi: è la ragione della guardia.

### ⭐ …e i LOTTI si numerano in ordine di DATA DOCUMENTO (2026-08-25)

⚠️ Due ordinamenti diversi che si somigliano, e vanno tenuti distinti: dentro un
lotto le **fatture** vanno per id crescente (qui sopra, è l'ordine di dipendenza
delle rettifiche); fra loro i **lotti** vanno per **data documento**
(`min(f.data)` delle fatture senza numero, poi `id`), perché il cancello di
`fn_get_next_progressivo` rifiuta una data anteriore all'ultimo numero emesso sul
sezionale.

🔴 Non è teoria: il giro del **2026-08-05** ha numerato sei lotti in un solo atto
e ha prodotto un'inversione lo stesso (numero 2 al 21/07, numero 3 al 19/06),
proprio perché ordinava per id di lotto — cioè nell'ordine in cui i lotti sono
**nati**, non in quello in cui i loro documenti sono **datati**.

Sede: `VenditeRepository.list_lotti_numerabili`, con il frammento SQL condiviso
`db/_data_documento_sql.py` — lo stesso che alimenta `data_corrente` della
finestra di numerazione. Due copie e il dialog racconterebbe un ordine diverso da
quello con cui il giro numera davvero.

### ⭐ Il codice del DB arriva intatto all'operatore (2026-08-21)

`_run_per_fattura_task` non appiattisce più ogni `DatabaseError` su
`E_TASK_FATTURA`: legge il codice di dominio dal campo strutturato e lo usa per
il `ServiceError`, il messaggio (`diag.message_primary`) e il log FATTURA.
🔴 Misurato: la guardia qui sopra dice *«numera prima la fattura NNN»* e
arrivava a video come *«Errore su singola fattura durante task pipeline»*.
`E_TASK_FATTURA` resta il ripiego per ciò che il database non ha nominato.
Dettagli: [api_pipeline_task.md](api_pipeline_task.md).

### 4. «Rendi definitive» singolo lotto (C-4, sincrono)

- `POST /api/v1/vendite/fatturazione/lotti/<lotto_id>/numera/` · permesso dalla **riga del
  passaggio** EMESSA → DEFINITIVA (oggi `numera_fatture_lotti`), col BB `PassaggioDocumento`:
  è la stessa riga che leggono la capability del lotto (che nasconde «Numera» a chi non
  ha l'azione) e il verbo DB. Da un lotto non EMESSA la riga non c'è: decide il livello
  sul documento e il guard qui sotto risponde 409 (brief-modello-documento-vendita
  §15.8, 2026-10-27).
- Body: `{}` oppure `{ "data_documento": "YYYY-MM-DD" }`. Guard scope (404 fuori
  scope) + guard **EMESSA** (409 se non EMESSA).

### ⭐ `data_documento`: la data si DICHIARA, e non è un sinonimo di «oggi» (2026-08-25)

Il parametro è **facoltativo su tutti e tre i verbi**, e assente non vuol dire
«usa oggi»: vuol dire **nessuna dichiarazione**, e allora la data la decide la
politica del registro (`vendite.registri_fatturazione.politica_data_documento`:
`OGGI` oppure `FINE_MESE_COMPETENZA`) nel momento in cui la testata nasce.

| verbo                         | cosa fa `data_documento`                                                                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `fatturazione/run/` (BE-1)    | è scritta sui **lotti che il giro crea**, come i `gruppi`: alla creazione, non su un lotto indicato per id |
| `fatturazione/numera/` (BE-2) | **una data per l'intero atto**: vale per tutti i lotti che quel giro numera, non una per lotto             |
| `lotti/<id>/numera/` (BE-2)   | vale per quel lotto                                                                                        |

⛔ **Sui due verbi di numerazione la data si applica PRIMA di numerare**, via
`vendite.fn_imposta_data_documento_lotto`, che in un atto solo scrive la data sul
lotto, la propaga alle fatture **non ancora numerate** e **rigenera i loro piani
rate**. La rigenerazione non è un contorno: le scadenze si calcolano da
`fatture.data` e il guard D-K verifica la **somma** delle rate — che non cambia,
mentre cambiano le date. Una data nuova con le rate vecchie **passerebbe in
silenzio**.

⚠️ Le fatture **già numerate si saltano e si contano**: il caso «lotto numerato a
metà» esiste nei dati, e rifiutare l'intero lotto renderebbe irrisolvibile
proprio il caso per cui la funzione esiste.

⚠️ **Due transazioni, non una.** La dichiarazione e la numerazione sono atti
separati: se la numerazione poi fallisce (guard D-K, padre di una nota ancora
senza numero), **la data e le rate rigenerate restano**. Non è un difetto da
correggere avvolgendo tutto in un `atomic` — il runner tiene apposta il lavoro
parziale degli step già fatti — ed è la ragione per cui l'esito porta
`aggiornate`/`rate_rigenerate` **anche quando il giro si ferma**.

### 5. Ristampa massiva lotto (C-8, sincrono)

- `POST /api/v1/vendite/fatturazione/lotti/<lotto_id>/ristampa/` · nessun
  `post_permission` (stampa = lettura I-4; gate readonly lato FE)
- Body: `{}`. Guard scope (404) + guard **DEFINITIVA** (409): accoda in
  `vendite.fatture_stampa_coda` una riga per ogni fattura non esclusa; il worker
  `draina_coda_stampa` le renderizza. **Non numera** (gate DEFINITIVA → il
  backstop del worker non ha nulla da numerare).

### 6. Esiti giri + stato coda stampa (C-5, sola lettura)

- `GET /api/v1/vendite/fatturazione/esiti/[?competenza_mese=YYYY-MM-DD]`
- Due sorgenti fuse in `giri`: i job della **coda lavori** `FATTURAZIONE_GIRO` /
  `FATTURAZIONE_NUMERA` (`dbops.coda_lavori`, `origine: "app"`) e i giri
  schedulati da `maintenance.job_run_log` con jobname di prefisso
  `run_fatturazione_batch` (`origine: "batch"`); più i conteggi della coda stampa
  per stato **scoped all'operatore** (JOIN a `vendite.fatture`).
- `competenza_mese` (facoltativo, normalizzato al 1° del mese): restringe giri e
  coda stampa a quel mese di competenza; assente = totali da sempre. Data
  malformata → `400`.

### 7. Finestra di numerazione (BE-5, sola lettura, 2026-08-25)

- `GET /api/v1/vendite/fatturazione/finestra-numerazione/?lotto_id=<id>`
- `GET /api/v1/vendite/fatturazione/finestra-numerazione/?competenza_mese=YYYY-MM-DD`
- `GET /api/v1/vendite/fatturazione/finestra-numerazione/?lotti=12&lotti=15` —
  la **selezione** (parametro ripetuto): il pavimento più restrittivo fra i lotti
  indicati, ricalcolato mentre l'operatore spunta
- **Esattamente uno** dei tre perimetri (più d'uno o nessuno →
  `E_VALIDATION_INPUT`).

Risponde a due domande su due perimetri: con quale data si può numerare, e da
quale data i documenti partono **adesso**.

```json
{ "data": {
    "lotto_id": 1278, "competenza_mese": null,
    "n_lotti": null,               // quanti lotti nel perimetro (selezione/mese)
    "data_documento": null,        // la DICHIARAZIONE sul lotto (spesso assente)
    "data_corrente": "2026-08-03", // la data che i documenti da numerare portano oggi
    "data_minima":  "2026-08-23"   // il PAVIMENTO del sezionale
} }
```

⭐ **Non è un abbellimento.** Sul registro Back-office la politica è
`FINE_MESE_COMPETENZA`: ogni lotto di competenza **arretrata** nasce con una data
anteriore all'ultimo numero emesso, quindi senza questa lettura il dialog
proporrebbe **ogni volta** una data che il DB rifiuta, e l'operatore imparerebbe
a leggere l'errore invece della targa.

⛔ **È una TARGA, non un lucchetto.** `fn_get_data_minima_numerabile_lotto` è
SECURITY INVOKER su `vendite.fatture`, che ha la RLS: sotto un perimetro
ristretto il minimo esce **più basso del vero** (fail-open, e la funzione DB lo
dichiara). Il rifiuto vero resta del cancello in `fn_get_next_progressivo`, che
legge il **contatore** — tabella senza RLS. Chi usasse questa risposta AL POSTO
del cancello starebbe sostituendo un presidio con un suggerimento.

⚠️ `data_minima` a `null` = nessun pavimento (su quei sezionali non è ancora
stato emesso nessun numero), **non** «nessun limite noto». `data_corrente` a
`null` = nel perimetro non c'è niente da numerare.

## Output

- Accodamento (run / numera perimetro):
```json
{ "data": { "job_id": 555, "stato": "PENDING" }, "meta": { "request_id": "..." } }
```
- Polling (`run/<job_id>/`):
```json
{ "data": {
    "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "FATTO",
    "tentativi": 0, "max_tentativi": 5,
    "result": { "lane": 3, "senza_emittente": 0, "falliti": 0 },
    "ultimo_errore": null, "job_run_id": 12
} }
```
  Stati: `PENDING` → `IN_CORSO` → `FATTO` | `ERRORE` | `ANNULLATO`. Il `result`
  del giro riporta `lane` (terne emittibili), `falliti`; quello della
  numerazione perimetro `lotti`/`numerati`/`falliti` (più `data_documento`, la
  data con cui l'atto è stato compiuto: a giro finito è l'unico posto dove si
  legge).
- Ristampa: `{ "data": { "lotto_id": 117, "accodate": 4 } }`
- Numerazione singolo lotto: esito dello step (`stato_doc_fiscale_id`,
  `step_eseguiti`, `motivo_stop`, `errore`). ⚠️ È l'esito del **driver di
  pipeline**, con lo stesso contratto — *un `200` non è un successo, si guarda
  `motivo_stop`* — descritto una volta sola in
  [api_run_lotto_pipeline_until_done.md](api_run_lotto_pipeline_until_done.md)
  §Output. ⭐ Con `data_documento` nel body l'esito porta
  anche `data_documento`, `aggiornate`, `saltate_numerate`, `rate_rigenerate`:
  **le due conseguenze che l'operatore non si aspetta** sono un lotto numerato a
  metà e delle scadenze che si sono spostate. Chi non le mostra le nasconde.
- Finestra di numerazione: vedi §7.
- Esiti: `{ "data": { "giri": [ { "jobname": "...", "origine": "app|batch", "mio_count": 3, "altri_count": 1, "last_run_at": "...", "in_corso": false, "ultima_conclusa": { "started_at": "...", "ended_at": "...", "ok": true } | null, "total_runs": 24, "ok_count": 23, "fail_count": 1, "saltate_count": 0 } ], "coda_stampa": { "PENDING": 2, "FATTO": 5 } } }`.
  ⛔ Dal 2026-09-14 **`last_ok` non c'è più**: era l'esito dell'ultimo giro
  concluso accanto alla data dell'ultimo giro *toccato*, e durante un giro in
  esecuzione il pannello mostrava l'ora del giro in corso con l'esito del
  precedente (sulle righe «app» un job `IN_CORSO` usciva addirittura «Errore»).
  Ora l'esito viaggia con la **sua** data in `ultima_conclusa`, e `in_corso`
  dice a parte che un giro sta girando. Stessa forma da entrambe le sorgenti
  (`maintenance.job_run_log` e `dbops.coda_lavori`), perché il pannello le
  fonde in una lista sola. `ok` può essere `null` sul giornale dei run
  (colonna nullable): il pannello lo rende «esito non scritto», non «Errore».
  `saltate_count` c'è sulle sole righe `batch` (dal 2026-10-10): sono le sveglie
  che hanno trovato la corsia occupata, e non entrano in `total_runs` né in
  `ultima_conclusa` — una corsa saltata non ha fatto il lavoro. La coda lavori
  non ha corse saltate. `mio_count` / `altri_count` ci sono sulle sole righe
  `app`: quanti job sono stati accodati dallo **scope dell'operatore** che legge
  e quanti da altri (`altri_count = total_runs - mio_count`).

## Regole

- **Idempotenza a due layer**: header HTTP `Idempotency-Key`
  (`dbops.idempotency_keys`, replay della risposta) ≠ **chiave di business** della
  coda `{job_type}[:{corsia}]:{competenza}:{scope_key}[:{digest}]` (dedup dei
  job VIVI: due click sullo stesso mese/scope → stesso job). La `corsia` c'è sul
  solo giro `FATTURAZIONE_GIRO` (`mirata` con `gruppi`, altrimenti quella
  on-demand); il `digest` (sha256 troncato a 12) dell'insieme di `gruppi` o
  `lotti` c'è solo se l'insieme è valorizzato. La `scope_key` = «ALL» (admin) o gli emittenti
  autorizzati ordinati.
- **Identità operatore catturata** all'accodamento (`auth_user_id`, `username`,
  `identita_id`, `emittente_ids`, `scope_key`): il worker la ripropone per intero
  (6 GUC via `set_jwt_gucs`) così la RLS risolve **come nel web**. Un job
  OPERATORE senza identità completa → fail-loud. Identità non risolta dal token
  all'accodamento → `400 E_CODA_SCOPE_OPERATORE_INVALIDO`.
- **Gate fiscale I-7**: numerazione (atto fiscale) sempre dietro permesso
  `numera_fatture_lotti`, distinto da `genera_fatture_lotti`; la ristampa è gated
  a **DEFINITIVA** per non numerare mai via backstop.
- **La data documento non entra nella chiave di business della coda**: due «Rendi definitive» vivi sullo
  stesso mese e scope restano un doppione anche con date diverse — la dedup
  difende l'**atto fiscale**, non il parametro.
- **Validata all'endpoint, non solo nel worker**: una data malformata torna 400 a
  chi preme il pulsante invece di diventare un job fallito da leggere nei log un
  minuto dopo. ⛔ E viene **riscritta** in ISO, non solo controllata: nel payload
  della coda deve finire una forma sola, quella che il worker sa rileggere.
  ⚠️ Il worker la rilegge con `parse_data_iso` e **non** con
  `parse_competenza_mese`: la seconda fa `.replace(day=1)` — perché una
  competenza *è* un mese — e trasformerebbe un 25/08 dichiarato in un 01/08
  senza sollevare niente.
- **Worker non schedulato** = job resta PENDING: il polling FE ha un cap
  (~3 min) e avvisa «in coda» invece di attendere all'infinito.

## Codici errore

| Codice                                          | HTTP | Quando                                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_VALIDATION_INPUT`                            | 400  | `competenza_mese` assente; `gruppi`/`lotti` malformati o vuoti; finestra senza esattamente un perimetro                                                                                                                                                                                                                                                                           |
| `E_CODA_SCOPE_OPERATORE_INVALIDO`               | 400  | identità operatore non risolta dal token: il lavoro non si accoda                                                                                                                                                                                                                                                                                                                 |
| `E_JOB_NON_TROVATO`                             | 404  | polling di un job inesistente o di altro scope                                                                                                                                                                                                                                                                                                                                    |
| `E_LOTTO_NON_TROVATO`                           | 404  | lotto fuori scope/inesistente (numera/ristampa singolo)                                                                                                                                                                                                                                                                                                                           |
| `E_LOTTO_NON_NUMERABILE`                        | 409  | «Rendi definitive» su lotto non EMESSA                                                                                                                                                                                                                                                                                                                                            |
| `E_LOTTO_NON_RISTAMPABILE`                      | 409  | ristampa massiva su lotto non DEFINITIVA                                                                                                                                                                                                                                                                                                                                          |
| `E_IDEMPOTENCY_KEY_REQUIRED`                    | 400  | POST senza header `Idempotency-Key`                                                                                                                                                                                                                                                                                                                                               |
| `E_FATTURA_RETTIFICATA_SENZA_NUMERO` (**937**)  | 409  | numerazione di un documento che rettifica righe di una fattura **senza numero** (o non visibile: il guard è fail-closed sulla RLS)                                                                                                                                                                                                                                                |
| `E_FATTURA_NON_NUMERABILE_INCOERENTE` (**574**) | 422  | documento incoerente — totali, riepiloghi IVA o piano rate (sei condizioni, vedi la [guida](../../../guide/fatturazione.md))                                                                                                                                                                                                                                                      |
| `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO`        | 400  | la data del documento è anteriore all'ultimo numero già emesso sul sezionale. Sollevato dal **cancello** (`fn_get_next_progressivo`, sotto l'advisory lock) e, in anticipo, da `fn_imposta_data_documento_lotto`. `ui_action` **`highlight_form_fields`** e non il banner di default: il DB manda `column_name = data_documento`, cioè nomina il campo che l'operatore ha davanti |
| `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE`         | 400  | la data del documento è anteriore al **limite di emissione** del sezionale (troppo vecchia per essere ancora emessa). Distinto da quello sopra: si rimedia avvicinando la data a oggi. Quale dei due esce lo decide l'origine del pavimento (`fn_get_pavimento_data_documento`); il messaggio nomina il pavimento effettivo. Stesse due sedi (`fn_get_next_progressivo`, `fn_imposta_data_documento_lotto`) |
| `E_FATTURA_DATA_NON_MODIFICABILE`               | 409  | si è tentato di cambiare la data di una fattura **già numerata** (trigger `trg_fatture_a10_guard_data_numerata_upd`)                                                                                                                                                                                                                                                              |
| `E_TASK_FATTURA`                                | 400  | fallimento su singola fattura **che il database non ha nominato** (errore Python, guasto tecnico). Se il codice di dominio c'è, arriva quello                                                                                                                                                                                                                                     |

## Dipendenze DB

- **Coda lavori generica**: `dbops.coda_lavori` (+ `dbops.coda_lavori_tipi`
  registry, seed tipi `FATTURAZIONE_GIRO`/`FATTURAZIONE_NUMERA`) +
  `dbops.fn_accoda_lavoro(...)` (enqueue atomico + dedup job vivi). Claim/reaper/
  marca = BE in SQL diretto (`FOR UPDATE SKIP LOCKED`).
- **Coda stampa** (outbox PDF): `vendite.fatture_stampa_coda` +
  `vendite.fn_accoda_stampe_lotto(p_lotto_id)`. Drenata da `draina_coda_stampa`.
- **Pipeline**: `vendite.fatturazione_lotti`, `vendite.fatture`,
  `config.stati_doc_fiscale` (EMESSA/DEFINITIVA), `maintenance.job_run_log`.
- **Emissione mirata**: `vendite.fatturazione_lotti_gruppi` (perimetro del
  lotto), `vendite.fn_build_gruppo_fatturabile_key` (unica fonte della chiave) e
  il parametro `p_gruppi` di `fn_list_emittibili_lane`,
  `fn_list_commesse_emittibili`, `fn_emit_attivita_fatturabili_da_commessa`,
  `fn_select_attivita_fatturabili`. Assenza di righe/`NULL` = nessuna
  restrizione = comportamento del giro schedulato.
- **Data documento** (cantiere 2026-08-25): `registri_fatturazione.politica_data_documento`,
  `fatturazione_lotti.data_documento`, `registri_fatturazione_progressivi.ultima_data`
  (il **pavimento**, su tabella **senza RLS**) e le funzioni
  `script.fn_data_operativa`, `vendite.fn_calcola_data_documento`,
  `fn_get_data_minima_numerabile[_lotto]`, `fn_imposta_data_documento_lotto`,
  `trgfn_fatture_guard_data_numerata`. Il cancello vive dentro
  `fn_get_next_progressivo`, **dopo** l'advisory lock: letto prima sarebbe
  soggetto a corsa.
- **RLS operatore** su `fatturazione_lotti`/`fatture` (policy
  `rls_*_ef_whitelist`, GUC `app.current_user_id` + `app.ruolo_applicativo`).

## Note di migrazione

Le azioni sono endpoint di **comando accanto** alle viste `vw_dash_*` (I-6: il
read-side non si tocca). Deploy worker: systemd timer su `draina_coda_lavori`
(+ `draina_coda_stampa`) — vedi `docs/it/dev/backend/play-book-operativo-backend.md`
§16. Contratto coda + design: `docs/it/dev/work-in-progress/brief-design-coda-lavori-generica.md`;
guide funzionali `docs/it/guide/gestione-code-di-lavoro.md` +
`analisi-tracciamento-processi-e-job.md`.

**Emissione mirata (2026-07-27)**: additiva su `fatturazione/run/`. Senza
`gruppi` il comportamento — corsia, chiave di dedup, esito — è **bit-identico**
a prima. Substrato DB `20260727-10..19`; brief BE/FE
`dev/work-done/brief-be-fe-emissione-fattura-mirata.md`.

**Data documento e cancello di sequenza (2026-08-25)**: additivo su tutti e tre i
verbi — senza `data_documento` il comportamento è quello di prima, con la sola
differenza che la data della testata non è più `current_date` (in **UTC**, quindi
sbagliata di un giorno per tutto ciò che nasceva dopo mezzanotte) ma il risultato
di `fn_calcola_data_documento`. Nuovo endpoint di sola lettura
`fatturazione/finestra-numerazione/`. Brief:
`dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` (§8 le
consegne BE/FE, §12 il consuntivo); analisi con le misure sui dati veri:
`analisi-numerazione-fattura-data-e-sequenza.md`.
