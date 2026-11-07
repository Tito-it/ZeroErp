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
| Proprietario | per-OPERATORE: chi ha accodato (`scope->>'auth_user_id'`; per «Esegui ora», lavoro SISTEMA, `payload->>'richiesto_da'`); perimetro d'azienda dalla RLS (dal 2026-11-07, blocco 5b e BE9) | per-OPERATORE via `user_insert` (chi ha innescato la stampa); perimetro emittente dalla RLS e, nei conteggi, via JOIN a `vendite.fatture` |
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
  liveness worker (`ultimo run entro la tolleranza dichiarata` = attivo).
  Pollato dal FE a 60s.
- ⭐ **La soglia non è un numero nel backend**: è il **contratto del processo**,
  `dbops.processi.tolleranza_minuti`, letto via
  `ProcessiRepository.contratti_liveness` — lo stesso numero con cui il database
  dichiara un processo `MUTO`. Non sta in `backend/deploy/sveglie.json`, che
  descrive solo come il deploy sveglia il processo: se il campo
  `tolleranza_minuti` ricompare lì, `carica_sveglie()` rifiuta il file.
- ⛔ Prima era `WORKER_ATTIVO_SOGLIA_MINUTI = 10` in `gestione_service.py`, con
  il commento «i timer girano a 1-2 minuti»: per sapere se 10 fosse ancora
  giusto bisognava aprire l'`OnCalendar` in un altro file, che nessuno
  rileggeva. Due scritture dello stesso fatto, e la divergenza sarebbe stata
  **muta** — un pallino verde su un worker fermo.
- ⚠️ Il contratto della risposta per worker è `{last_run_at, attivo, in_corso,
  ultima_conclusa}` (dal 2026-09-14; fino a quel giorno `{last_run_at, attivo,
  last_ok}`), e un worker mai girato resta `{attivo: false}` esplicito.
  ⛔ **`last_ok` non c'è più, ed è una scelta**: era l'esito dell'ultima corsa
  *conclusa* accanto alla data della corsa *più recente* — due corse in una
  riga. Ora la riga più recente è il segno di vita (`last_run_at`, `attivo`,
  `in_corso` = è ancora aperta) e l'esito viaggia **con la sua data** in
  `ultima_conclusa = {started_at, ended_at, ok}` (`null` se nessuna corsa è
  mai stata chiusa; `ok` può essere `null`: la colonna è nullable e nessun
  CHECK la lega a `ended_at`). Il badge rende solo `attivo` e `last_run_at`;
  il digest dei presidi e il pannello degli esiti rendono anche il resto.
- ⚠️ Se un worker arrivasse senza contratto (processo non a catalogo, o
  tolleranza `NULL`) il service ripiega su 10 minuti per non spegnere il badge,
  ma è una configurazione incompleta e la CI la rifiuta
  (`test_worker_del_badge_hanno_un_contratto`).

### 2. Lista coda lavori (BE-5, sola lettura)

- `GET /api/v1/core/tracciamento/coda-lavori/`
- Query: `ambito` (`miei` default = i lavori **accodati da me** | `tutti` =
  tutti quelli **delle mie aziende**, cioè ciò che la RLS di
  `dbops.coda_lavori` mostra — i lavori SISTEMA solo al super admin. È
  **visibilità aperta a ogni operatore**: la coda è una risorsa condivisa;
  `code_manage` serve solo per azioni e dettaglio sui lavori dei colleghi),
  `stato`, `tipo` (job_type), `solo_vivi`, `data_da`/`data_a` (YYYY-MM-DD,
  inclusiva; giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09)), `archiviate` (bool, default `false` — vedi §6), `limit` (default
  25, max 200)/`offset`, `order_by`/`order_dir` (fino al 2026-10-20
  `sort_by`/`sort_dir`, oggi ignorati: brief-be-verifica-documentazione-api §A4).
- Ogni riga porta `is_mio` (calcolato dal BE: il lavoro l'ha accodato il
  chiamante — la stessa regola del filtro «miei»; fino al 2026-11-07 era «la
  stessa `scope_key`», poi per poche ore «della mia azienda») e `proprietario`
  (`scope->>'username'`).

#### ⭐ `data_insert` e l'ordinamento di default (dal 2026-09-07)

Ogni riga porta **`data_insert`** — *quando il lavoro è entrato in coda*. È un
fatto **diverso da `started_at`**: il primo lo scrive chi accoda, il secondo il
worker quando prende il lavoro. Su un lavoro in **attesa** esiste solo il primo.

⇒ **È anche il nuovo ordinamento di default**, `DESC`, su **entrambe** le code.

🔴 **Perché è cambiato, ed è un difetto che vale la pena non ricreare.** Il
default era `started_at DESC NULLS LAST`. Un lavoro `PENDING` `started_at` non
ce l'ha per definizione, quindi finiva **dopo ogni lavoro mai avviato**: non
filtrato — *sepolto*. Misurato il 2026-09-07 su dbdev: le righe senza
`started_at` in posizione **112 e 113 su 113**, cioè in quinta pagina da 25.
⛔ La lista non sbagliava e non nascondeva niente: metteva in fondo esattamente
la riga che interessa. È la stessa forma già nominata in
[api.md](../../../dev/api.md) per i gruppi del lotto — *«il caso che interessa
finirebbe in fondo»*.
⭐ L'argomento strutturale, al netto dei gusti: **`data_insert` è `NOT NULL`**.
Ordinare su una colonna che ammette NULL significa avere sempre un ramo che cade
in fondo — e qui quel ramo era sistematicamente lo **stato vivo**.

⚠️ **La coda stampa non aveva il difetto, ma per coincidenza**: ordinava su
`data_update`, che è `NOT NULL` e su una riga mai toccata vale quanto
`data_insert`. Le due code hanno una semantica sola per decisione (Tid,
2026-07-23), quindi sono state allineate: due default diversi erano una
simmetria che reggeva finché nessuno aggiornava una riga in attesa.

⛔ **Questo default vive in TRE sedi che devono concordare**, e la divergenza non
darebbe nessun errore — darebbe una lista che si riordina da sola al primo tocco
dell'operatore:

| Sede | Cosa |
| --- | --- |
| `gestione_service` (`default=`) | ciò che il BE applica se il client non chiede niente |
| `ui.lista_preset.ordinamento_default` | ciò che il preset del catalogo dichiara |
| store FE (`orderBy`) | ciò che il client manda al primo caricamento |

⛔ **E nessun presidio tiene insieme le tre**, verificato il 2026-09-08:
`test_liste_configurabili_seed` confronta le colonne **ordinabili** del seed con
la whitelist del repository — non i default — e in tutto `backend/apps` niente
legge `ordinamento_default`. `test_coda_lavori_gestione_service` fissa i due
default **del service** e nient'altro. ⇒ Le tre sedi si controllano **a mano**,
e questa riga esiste perché la prossima persona non creda il contrario.

### 3. Lista coda stampa (BE-6, sola lettura)

- `GET /api/v1/core/tracciamento/coda-stampa/`
- Query: come sopra + `lotto_id`. `ambito=miei` = righe innescate dal
  chiamante (`user_insert`); `tutti` = tutte quelle del suo perimetro emittente
  (RLS). Ogni riga porta `is_mio` e `operatore` (`user_insert`), come la coda
  lavori.
- Righe: fattura (numero/anno/serie), emittente, lotto, stato, tentativi,
  ultimo_errore, documento_id, `data_insert`/`data_update`,
  `archiviato`/`archiviato_il`/`archiviato_da`.
  ⚠️ `data_insert` era già nel payload da prima del 2026-09-07 — mancava solo
  dalla whitelist d'ordinamento e dal catalogo colonne, quindi nessuno poteva
  né ordinarci né vederlo.

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
righe → la riga finisce in `falliti` con `E_JOB_NON_TROVATO` (risposta 200),
indistinguibile da inesistente.

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
      "coda_lavori": {
        "last_run_at": "2026-07-21T22:47:07+02:00", "attivo": true, "in_corso": false,
        "ultima_conclusa": { "started_at": "2026-07-21T22:47:07+02:00",
                             "ended_at": "2026-07-21T22:47:08+02:00", "ok": true }
      },
      "coda_stampa": { "last_run_at": null, "attivo": false, "in_corso": false,
                       "ultima_conclusa": null }
    }
} }
```
- Liste: `{ "data": { "count": N, "archiviate_count": M, "results": [ ... ] } }`
  (offset-based).
- Azioni di esecuzione: `{ "data": { "job_id": 5, "stato": "ANNULLATO" | "PENDING" } }`.
- Archiviazione: `{ "data": { esito, archiviato, richieste, riuscite, falliti[] } }`
  — vedi §6. Identica sulle due code.

## Regole

- **Perimetro d'azienda dal DB, ownership per persona (BE9, 2026-11-07)**: la
  RLS di `dbops.coda_lavori` (blocco 5b) mostra a ciascuno i lavori delle sue
  aziende, i SISTEMA al solo super admin e al drenatore; il backend non scrive
  più un filtro per azienda. Dettaglio e azioni sono dei lavori **accodati dal
  chiamante**, o di ogni lavoro visibile con `code_manage`. Fuori perimetro o
  altrui = **404** indistinguibile da inesistente (no leak). Il polling dei giri
  (`/vendite/fatturazione/run/<id>/`) **non** restringe ai miei: due colleghi
  della stessa azienda seguono il giro condiviso via dedup.
- **`code_manage`** (azione di processo, area `strumenti` — seed §6 del brief,
  id atteso 28): sblocca il dettaglio e le azioni su job altrui, e
  l'archiviazione. `?ambito=tutti` **non** lo richiede. SUPER_ADMIN bypassa. ⚠️ Fino all'apply dei seed (area + azione), tutto il layer è
  fail-closed: solo SUPER_ADMIN.
- **Niente race col worker**: annulla/requeue ri-verificano stato E scope
  nell'UPDATE (0 righe = 409 parlante) — un claim concorrente vince sempre.
- **Liveness fail-visible**: worker mai girato → `{attivo: false}` esplicito,
  mai una chiave mancante.

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_JOB_NON_TROVATO` | 404 | job inesistente o di altro scope (dettaglio/azioni) |
| `E_JOB_NON_ANNULLABILE` | 409 | annulla su job non più PENDING |
| `E_JOB_NON_RIACCODABILE` | 409 | requeue su job non riaccodabile (né ERRORE né IN_CORSO stantio) |
| `E_JOB_NON_TROVATO` | 404 sul singolo, **riga fallita** nel giro di massa | riga inesistente o fuori perimetro emittente (stesso codice sulle due code: la **condizione** è la stessa, non il dominio) |
| `E_PERMESSO_NEGATO` | 403 | archivia/ripristina senza `code_manage`/SUPER_ADMIN |
| `E_VALIDATION_INPUT` | 400 | `ids` assente/vuoto, non interi positivi, o oltre 200 |
| `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` | **riga fallita** nel giro (409 se fosse sola) | archiviazione di una riga ancora VIVA (`PENDING`/`IN_CORSO`). Lo solleva il **trigger**, con la sua frase a catalogo |
| `E_VALIDATION_INPUT` | 400 | `extra_tentativi` fuori range 1..10; `data_da`/`data_a` non `YYYY-MM-DD`, `solo_vivi`/`archiviate` non booleani, `lotto_id` non intero |
| `E_SEARCH_VALIDATION` | 400 | `order_by` fuori dalla whitelist della coda, o `order_dir` diverso da `asc`/`desc` |
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
- `vendite.fatture_stampa_coda` + JOIN `vendite.fatture` e
  `anagrafiche.emittenti_fiscali`. Scope emittente applicativo (convenzione SR)
  nei conteggi e nell'archiviazione; la lista filtra per `user_insert` e per il
  resto si affida alla RLS.
- `maintenance.job_run_log` (liveness worker, jobname
  `draina_coda_lavori`/`draina_coda_stampa`).
  ⚠️ I due jobname **non sono letterali** in `gestione_service.py`: sono le
  costanti di `apps.core.services.processi`, perché il worker si registra sul
  giornale col proprio `processo_codice` ed è con quello che si cerca la
  tolleranza nel dichiarato. Due stringhe uguali in due file si sarebbero
  sfilate al primo rename **senza che niente fallisse**: la tolleranza non si
  sarebbe più trovata e il badge avrebbe continuato con il ripiego.
- `dbops.processi.tolleranza_minuti` — il contratto di liveness dei due
  drainer (via `ProcessiRepository.contratti_liveness`). La cadenza dei timer
  sta invece in `backend/deploy/sveglie.json`: vedi
  [sveglie_processi.md](sveglie_processi.md).
- Seed `config.aree_funzionali` area `strumenti` + azione
  `config.azioni_processo` `code_manage` su quell'area (team DB, brief §6).

## Note di migrazione

Endpoint **accanto** al read-side esistente (I-4: `esiti/` e il polling
`run/<job_id>/` di vendite restano invariati). Consumer FE: badge top bar +
drawer rapido + vista «Strumenti → Code di lavoro». Raccordo col cantiere
dashboard-home: l'eventuale widget KPI «Processi in coda» dovrà riusare
`gestione_service.conteggi_code` come callable del registry contatori, non una
query nuova.
