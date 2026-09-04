# API Gestione code — coda lavori + coda stampa (Django)

## Scopo

Documentare gli endpoint della **UI di gestione code** (brief
`brief-be-fe-gestione-code-lavori-stampa`): conteggi per il badge top bar,
liste della coda lavori generica (`dbops.coda_lavori`) e della coda stampa
(`vendite.fatture_stampa_coda`), dettaglio job e azioni di governo
(annulla/requeue). Estendono il layer **tracciamento core** esistente
(`tracciamento/job-runs/` ecc.) — stessa area, stesso namespace.

## Contesto

Le code sono il motore async del cockpit fatturazione (Fase C): i verbi UI
accodano job (`FATTURAZIONE_GIRO`/`FATTURAZIONE_NUMERA`), la DEFINITIVA accoda
stampe, i worker `draina_coda_lavori`/`draina_coda_stampa` (systemd timer)
drenano. Questi endpoint danno all'operatore la superficie di **monitoraggio e
governo**: quanti processi ha in coda, se il worker è vivo, e la possibilità di
annullare/sbloccare i **propri** job.

Asimmetria di scope (regge il design):

| | Coda lavori | Coda stampa |
| --- | --- | --- |
| Proprietario | per-UTENTE via `scope->>'scope_key'` (whitelist emittenti) | per-EMITTENTE via JOIN a `vendite.fatture` |
| Azioni di esecuzione | annulla / requeue (solo propri, o `code_manage`) | nessuna (il drainer ritenta da solo) |
| Archiviazione | archivia / ripristina (`code_manage`, effetto globale) | identica: le due code sono simmetriche |

Tre layer: `views_tracciamento.py` (`ApiCode*`, `ApiCodaLavori*`,
`ApiCodaStampaList`) → `apps/core/services/coda_lavori/gestione_service.py` →
`CodaLavoriRepository` (core) + `VenditePipelineRepository.elenca_coda_stampa`
(vendite, satellite di fatture) + `MaintenanceRepository.job_liveness`.

## Input

Header sicurezza su tutti: `Authorization: Bearer <access_token>`. Area
funzionale: **`strumenti`** (area DEDICATA, seed §6 del brief — decisione
2026-07-21: non si apre `core` agli operatori solo per le code, esporrebbe il
tracciamento infra). `LETTURA` = conteggi/liste/dettaglio; `TUTTO` = anche le
azioni POST. Le view tracciamento legacy (audit-log, job-runs…) restano su
area `core`. I POST richiedono `Idempotency-Key` (header).

### 1. Conteggi badge (BE-4, sola lettura)

- `GET /api/v1/core/tracciamento/code/conteggi/`
- Conteggi vivi (PENDING/IN_CORSO) delle due code, **scoped** al chiamante, +
  liveness worker (`ultimo run entro 10 minuti` = attivo). Pollato dal FE a 60s.

### 2. Lista coda lavori (BE-5, sola lettura)

- `GET /api/v1/core/tracciamento/coda-lavori/`
- Query: `ambito` (`miei` default | `tutti` — richiede `code_manage`/SUPER_ADMIN),
  `stato`, `tipo` (job_type), `solo_vivi`, `data_da`/`data_a` (YYYY-MM-DD,
  inclusiva), `archiviate` (bool, default `false` — vedi §6), `limit` (max
  200)/`offset`, `sort_by`/`sort_dir`.
- Ogni riga porta `is_mio` (calcolato dal BE: la `scope_key` del job coincide
  con quella del chiamante) e `proprietario` (`scope->>'username'`).

### 3. Lista coda stampa (BE-6, sola lettura)

- `GET /api/v1/core/tracciamento/coda-stampa/`
- Query: come sopra + `lotto_id`; niente `is_mio` (la coda è per-emittente).
- Righe: fattura (numero/anno/serie), emittente, lotto, stato, tentativi,
  ultimo_errore, documento_id, `archiviato`/`archiviato_il`/`archiviato_da`.

⭐ **`ultimo_errore` porta il codice di DOMINIO, dal 2026-08-25.** Prima, su un
rifiuto del database, la riga conteneva `{"code": "ProgrammingError", "message":
"<testo + stack CONTEXT>"}`: un render fallito muto su un rifiuto che ha un nome.
Ora il drenatore legge la diagnostica dal BB `diagnostica_db` e scrive il codice
applicativo, la frase (`message_primary`, senza lo stack), e — **solo dove ci
sono** — `detail`, `campo` e `bersagli`:

```json
{ "code": "E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO",
  "message": "La data del documento e' anteriore all'ultimo numero gia' emesso…",
  "campo": "data_documento",
  "bersagli": [ { "type": "LOTTO", "id": "1278" } ] }
```

⛔ **Perché conta proprio qui.** Il backstop di numerazione
(`numera_fattura_backstop`) gira dentro il drenatore, **senza un operatore
davanti**: dal 2026-08-25 può rifiutare (il cancello sulla sequenza del
registro), e questa riga di coda è **l'unico posto** dove quel motivo può essere
letto. Va scritto qui o non esiste da nessuna parte.

⚠️ Vale per **entrambi** i rami di errore del drenatore, non solo per quello
generico: un `ServiceError` di dominio porta gli stessi canali (`targets`) e
prima li perdeva — la stessa riga raccontava due storie a seconda di quale
`except` l'avesse presa.

### 4. Dettaglio job (BE-8, sola lettura)

- `GET /api/v1/core/tracciamento/coda-lavori/<job_id>/`
- Payload, origine, priorità, timeline (accodato/claimed/started/ended),
  tentativi/max, ultimo_errore, result, job_run_id, proprietario, is_mio.

### 5. Azioni (BE-7, comando)

- `POST /api/v1/core/tracciamento/coda-lavori/<job_id>/annulla/` · body `{}`
  — solo job **PENDING** → `ANNULLATO`.
- `POST /api/v1/core/tracciamento/coda-lavori/<job_id>/requeue/` · body
  `{"extra_tentativi": 1..10}` (default 3, fonte unica nel service) — solo job
  **ERRORE**, oppure **IN_CORSO davvero STANTIO** (`claimed_at` oltre la
  soglia del reaper, 30 min — stessa definizione di «bloccato»): riaccodare
  un job che un worker sta eseguendo farebbe partire una **seconda esecuzione
  concorrente** (review 2026-07-22). → `PENDING` con `max_tentativi += extra`
  (storia tentativi preservata).

### 6. Archiviazione delle righe di coda (2026-09-04)

> Brief: `brief-db-archiviazione-righe-code`. DB applicato il 2026-09-04.

Togliere una riga **dall'elenco** senza toccarne lo **stato**. Nasce da una
richiesta precisa: i conteggi del pannello **Esiti fatturazione**
(`count_coda_stampa_per_stato`) sono un `GROUP BY` sullo stato **senza filtro di
visibilità**, quindi una cancellazione li fa calare e un annullamento sposta la
ripartizione. Serviva una bandiera che leggesse **solo la lista**.

- `POST /api/v1/core/tracciamento/coda-lavori/archivia/` · body `{"ids": [...]}`
- `POST /api/v1/core/tracciamento/coda-lavori/ripristina/` · body `{"ids": [...]}`
- `POST /api/v1/core/tracciamento/coda-stampa/archivia/` · body `{"ids": [...]}`
- `POST /api/v1/core/tracciamento/coda-stampa/ripristina/` · body `{"ids": [...]}`

⭐ **Rotte di COLLEZIONE, elenco nel corpo — anche per una riga sola.** Il menu
di riga manda `{"ids": [12]}`. Un verbo di massa e uno singolo sarebbero **due
contratti da tenere allineati per lo stesso rifiuto**, che è per riga. Tetto
`MAX_RIGHE_ARCHIVIAZIONE = 200` (lo stesso della paginazione, e la stessa
ragione di `MAX_ATTIVITA_RIPORTO`: oltre un certo punto «metti via N righe»
smette di essere un gesto che una persona ha guardato). Gli `ids` sono
**deduplicati** conservando l'ordine — il database tratterebbe due volte lo
stesso id come una riga sola, ma il conteggio che torna a video direbbe un
numero diverso da quello spuntato.

⛔ **ESITO PARZIALE, e il 200 non è un successo.** Il rifiuto è **per riga** (una
riga tornata al lavoro nel frattempo, una che non c'è più): un'unica transazione
farebbe fallire venti archiviazioni buone per una riga sola, e chi guarda non
saprebbe quale. Il telaio è il BB `run_fan_out` — **un savepoint per riga**,
errore isolato, esito aggregato a tre stati. **Chi consuma DEVE guardare
`esito`**, non lo status.

```json
{ "data": { "esito": "PARZIALE", "archiviato": true,
            "richieste": 4, "riuscite": 3,
            "falliti": [ { "id": 1398,
                           "code": "E_CODA_ARCHIVIAZIONE_NON_AMMESSA",
                           "message": "Questa riga della coda è ancora in stato PENDING: …" } ] } }
```

⛔ **E per questo NON si fa un solo `UPDATE … WHERE id = ANY(…)` col predicato
di stato nella `WHERE`**: sarebbe più veloce, ma scriverebbe la **seconda copia**
di «riga viva» — che ha una sede sola, il trigger, e che questo cantiere ha
deliberatamente lasciato lì (brief §7.4).

⛔ **Gate `code_manage`, NON l'ownership degli altri due verbi.** Annulla e
requeue sono owner-scoped — un operatore agisce sui **propri** job e il permesso
serve solo ad **allargare** agli altrui. L'archiviazione ha effetto **globale**:
chi archivia toglie la riga dall'elenco anche all'amministratore. Effetto
globale, permesso globale (decisione di Tid, brief §7.2). ⚠️ Il perimetro
dell'**archiviazione** non è quello della **lista**: la lista è visibilità ed è
aperta a ogni operatore, qui si scrive.

⛔ **E il gate lo verifica il SERVICE, non un `post_permission` sulla view.**
`ZeroERPPermission`, quando trova un `<metodo>_permission`, **ritorna l'esito
dell'azione di processo e salta il controllo di area**: un operatore con
`code_manage` e area `strumenti` in sola `LETTURA` passerebbe, mentre i due
verbi accanto — che quel campo non lo dichiarano — cadono su
`METHOD_REQUIRES['POST'] = 'add'` e pretendono `TUTTO`. Due POST adiacenti nella
stessa schermata con due contratti d'area diversi sono la forma in cui un
permesso «funziona» finché qualcuno non lo restringe e non capisce perché non ha
effetto. Senza `post_permission` valgono **entrambi** i controlli: l'area dalla
catena, `code_manage` dal service (`_guard_archiviazione` → `E_PERMESSO_NEGATO`,
403). Presidio: `test_archiviazione_senza_code_manage_403`.

⭐ **Due verbi e non un flag nel corpo**: le due direzioni hanno esiti diversi —
archiviare una riga ancora viva è un rifiuto del database, ripristinare non
fallisce mai — e un endpoint il cui esito dipende da un booleano nel payload
nasconderebbe quella differenza a chi legge le rotte.

⛔ **Il criterio «solo una riga NON VIVA si archivia» NON vive nel backend.** Ha
una sede sola: il trigger `_a10_archiviazione_upd` (funzione unica
`dbops.trgfn_coda_archiviazione` per le due code) più il `CHECK`
`chk_*_archiviato_non_vivo`. Il backend **traduce e passa**. «Vivo» è
`PENDING|IN_CORSO`, la stessa definizione che conta il badge in topbar.
⛔ Anche `archiviato_il` e `archiviato_da` **le deriva il trigger** (GUC
`app.jwt_user`): il backend non le scrive, quindi non può dire una cosa che la
bandiera smentisce.

⚠️ Sulla coda stampa è la **prima scrittura dell'operatore** su
`vendite.fatture_stampa_coda`. Dal 2026-09-04 la difende la policy RLS
`rls_fatture_stampa_coda_ef_whitelist`, **e il filtro applicativo di emittente
resta**: la RLS si somma ai filtri, non li sostituisce. Fuori perimetro → 0
righe → **404**, indistinguibile da inesistente.

⛔ **Chi NON legge la bandiera, ed è il contratto del cantiere**: claim,
drainer, reaper, `mark_*`/`marca_*`, `count_per_stato`,
`count_coda_stampa_per_stato`, `get_stato`, `uq_fatture_stampa_coda_vivo`. Un
lettore in più farebbe dell'archiviazione un **annullamento silenzioso**, cioè
qualcosa di peggio della cancellazione che esiste per evitare.

⚠️ **`archiviate_count` non è un accessorio.** Le liste nascondono le archiviate
di default e dichiarano quante ne restano fuori: senza quel numero «coda pulita»
e «tre righe messe via» si leggono uguali — è la stessa lezione di
`ritirate_count` sul giornale della fattura. È un conteggio **suo**, con lo
stesso perimetro della lista meno la bandiera; vale **0** quando le archiviate
sono incluse (lì non c'è niente di nascosto da dichiarare).

## Output

- Conteggi:
```json
{ "data": {
    "coda_lavori": { "pending": 2, "in_corso": 1 },
    "coda_stampa": { "pending": 0, "in_corso": 0 },
    "worker": {
      "coda_lavori": { "last_run_at": "2026-07-21 22:47:07+02", "attivo": true, "last_ok": true },
      "coda_stampa": { "last_run_at": null, "attivo": false, "last_ok": null }
    }
} }
```
- Liste: `{ "data": { "count": N, "archiviate_count": M, "results": [ ... ] } }`
  (offset-based).
- Azioni di esecuzione: `{ "data": { "job_id": 5, "stato": "ANNULLATO" | "PENDING" } }`.
- Archiviazione: `{ "data": { esito, archiviato, richieste, riuscite, falliti[] } }`
  — vedi §6. Identica sulle due code.

## Regole

- **Ownership scope-based (I-3)**: l'operatore vede/agisce sui job della
  propria `scope_key` (stessa fonte `scope_key_da_emittenti` dell'enqueue —
  nessuna seconda logica di scope, I-1). Fuori scope = **404** indistinguibile
  da inesistente (no leak). Whitelist emittenti `None` (admin globale) = vede
  tutto.
- **`code_manage`** (azione di processo, area `strumenti` — seed §6 del brief,
  id atteso 28): sblocca `?ambito=tutti` e le azioni su job altrui. SUPER_ADMIN
  bypassa. ⚠️ Fino all'apply dei seed (area + azione), tutto il layer è
  fail-closed: solo SUPER_ADMIN.
- **Niente race col worker**: annulla/requeue ri-verificano stato E scope
  nell'UPDATE (0 righe = 409 parlante) — un claim concorrente vince sempre.
- **Liveness fail-visible**: worker mai girato → `{attivo: false}` esplicito,
  mai una chiave mancante.

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_PERMESSO_NEGATO` | 403 | `?ambito=tutti` senza `code_manage`/SUPER_ADMIN |
| `E_JOB_NON_TROVATO` | 404 | job inesistente o di altro scope (dettaglio/azioni) |
| `E_JOB_NON_ANNULLABILE` | 409 | annulla su job non più PENDING |
| `E_JOB_NON_RIACCODABILE` | 409 | requeue su job non riaccodabile (né ERRORE né IN_CORSO stantio) |
| `E_JOB_NON_TROVATO` | 404 sul singolo, **riga fallita** nel giro di massa | riga inesistente o fuori perimetro emittente (stesso codice sulle due code: la **condizione** è la stessa, non il dominio) |
| `E_PERMESSO_NEGATO` | 403 | archivia/ripristina senza `code_manage`/SUPER_ADMIN |
| `E_VALIDATION_INPUT` | 400 | `ids` assente/vuoto, non interi positivi, o oltre 200 |
| `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` | **riga fallita** nel giro (409 se fosse sola) | archiviazione di una riga ancora VIVA (`PENDING`/`IN_CORSO`). Lo solleva il **trigger**, con la sua frase a catalogo |
| `E_VALIDATION_INPUT` | 400 | `extra_tentativi` fuori range 1..10 |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 400 | POST senza header `Idempotency-Key` |

## Dipendenze DB

- `dbops.coda_lavori` (+ `coda_lavori_tipi`): lettura/UPDATE diretti
  (annulla/requeue condizionati allo stato — design brief coda §3a).
- `dbops.trgfn_coda_archiviazione` + i due trigger `_a10_archiviazione_upd` e i
  `CHECK` gemelli sulle due code: **la** sede del criterio di archiviabilità e
  degli scrittori di `archiviato_il`/`archiviato_da`.
- Policy RLS `rls_fatture_stampa_coda_ef_whitelist` (`FOR ALL`, scope delegato
  alla testata via `script.fn_scope_ef_whitelist_via_fattura`), armata il
  2026-09-04.
- Seed `ui.lista_colonna`: **712** (colonna `azioni` sulla lista 35 — senza,
  il kebab della coda stampa non avrebbe dove attaccarsi), **713**/**714**
  (`archiviato_il` sulle liste 34/35, accese dal BE nello stesso commit in cui
  la colonna entra nella proiezione).
- `vendite.fatture_stampa_coda` + JOIN `vendite.fatture` (scope emittente via
  `add_emittente_scope_condition`, convenzione SR) + `anagrafiche.emittenti_fiscali`.
- `maintenance.job_run_log` (liveness worker, jobname
  `draina_coda_lavori`/`draina_coda_stampa`).
- Seed `config.aree_funzionali` area `strumenti` + azione
  `config.azioni_processo` `code_manage` su quell'area (team DB, brief §6).

## Note di migrazione

Endpoint **accanto** al read-side esistente (I-4: `esiti/` e il polling
`run/<job_id>/` di vendite restano invariati). Consumer FE: badge top bar +
drawer rapido + vista «Strumenti → Code di lavoro». Raccordo col cantiere
dashboard-home: l'eventuale widget KPI «Processi in coda» dovrà riusare
`gestione_service.conteggi_code` come callable del registry contatori, non una
query nuova.
