# Brief DB — Contesto di SISTEMA per processi headless sotto RLS (ruoli batch per-job)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟠 ALTA — la RLS è da trattare come **invariante di sistema sempre
> attivo** (non una feature del solo multi-face). Va chiuso **prima** che il batch
> fatturazione (e qualsiasi altro processo headless) operi su tabelle RLS-enabled in
> un ambiente con RLS realmente applicata.
> **Data**: 2026-06-17 · **Stato**: 🟢 **Path A, modello per-job** (ruolo
> `zeroerp_batch_fatturazione` BYPASSRLS, SELECT ampio + DML scoped al perimetro
> fatturazione, alias Django dedicato). **Lato DB (D1–D5): COMPLETATO e verificato su
> dbdev** (provisioning applicato, check postura verde, pgTAP `ok 1..11`). **Restano
> D6–D9 lato BE** → vedi §10 (consegna al BE). Piano completo in §7.
>
> **⚠️ Questo brief REVISIONA la precedente scelta "Opzione B"** (sentinel
> `app.ruolo_applicativo='SISTEMA'` + policy `_sistema` per-tabella) dopo analisi
> critica del 2026-06-17. Il BE aveva già pushato l'implementazione B (`_system_db_context`
> con GUC sentinel, costante `RUOLO_APPLICATIVO_SISTEMA`): **andrà adeguata** a Path A
> (refactor piccolo, vedi §6). La motivazione del cambio è in §4.
>
> **Origine**: [analisi-commesse-stato-e-sviluppi.md](analisi-commesse-stato-e-sviluppi.md)
> §9 + §10.4 F4 (caveat RLS). Coordinare con
> [analisi-attivazione-rls-operatori-be-fe.md](../work-done/analisi-attivazione-rls-operatori-be-fe.md),
> [db-brief-rls-ondata2-insert-bloccati.md](../work-done/db-brief-rls-ondata2-insert-bloccati.md)
> e [provisioning-db-roles.md](../backend/provisioning-db-roles.md).

---

## 1. Contesto (fatti verificati)

La RLS operatori filtra il ciclo attivo per emittente via GUC di sessione: policy
`rls_<tabella>_ef_whitelist` keyed su `current_setting('app.ruolo_applicativo', true) =
'OPERATORE'` + whitelist emittente (USING + WITH CHECK, **PERMISSIVE**, `FOR ALL` —
ondata2 `20260603-16..25`).

Fatti accertati (esplorazione 2026-06-17):

- **Django ha un solo alias DB** (`default`), che si connette come `zeroerp_app`
  ([settings.py:205-218](../../../../backend/zeroerp_backend/settings.py#L205-L218)).
  `zeroerp_app` è **`NOBYPASSRLS`, non-owner** → **soggetto alla RLS**
  ([provisioning-db-roles.md:39-53](../backend/provisioning-db-roles.md#L39-L53)).
- Il **driver di fatturazione** è un **management command** (`run_fatturazione_batch`,
  cron/systemd), **senza JWT e senza GUC d'identità**, e usa la **stessa connessione
  `default`** → **gira come `zeroerp_app`**. È un processo di sistema che deve operare
  su **tutti** gli emittenti (la numerazione fattura è per emittente).
- **Il progetto NON usa `FORCE`**: `zeroerp_app` essendo non-owner + NOBYPASSRLS è già
  vincolato dal solo `ENABLE`; l'owner (`titodb`) e i ruoli esenti restano fuori per
  natura ([provisioning-db-roles.md:64-68](../backend/provisioning-db-roles.md#L64-L68)).
  L'evento di attivazione **non è "FORCE"** ma il fatto che la RLS sia applicata sul
  ruolo runtime: già oggi, su un ambiente allineato, `zeroerp_app` è soggetto.

> Correzione rispetto alla stesura precedente: non è vero che "oggi funziona perché la
> RLS è dormiente per via di NO FORCE". Su un ambiente con `ENABLE` applicato,
> `zeroerp_app` **è già soggetto**; il batch headless senza contesto **è già a rischio
> default-deny**. Va trattato come problema presente, non futuro.

## 2. Problema

Un processo headless (`run_fatturazione_batch` o qualunque futuro job/CLI/cron) che si
connette come `zeroerp_app` **senza** settare `app.ruolo_applicativo='OPERATORE'` +
whitelist non soddisfa **nessuna** policy → **default-deny**:

- `SELECT` vuoti sulla discovery/lettura → il batch "completa" senza fare nulla, **in
  silenzio** (il caso più insidioso);
- `INSERT`/`UPDATE` negati (`new row violates row-level security policy`).

Serve un **canale di sistema** che dia ai processi headless visibilità/scrittura piena
su tutti gli emittenti, distinto dallo scope per-emittente degli operatori, con un
**meccanismo generico** (qualsiasi processo futuro lo riusa senza riprogettare) ma
**privilegi per-job** (ogni job vede solo ciò che gli serve, vedi §4).

## 3. Perimetro reale (corregge la stima precedente)

Conta l'intersezione **{tabelle toccate dal batch} ∩ {tabelle RLS-enabled}**:

- **Tabelle RLS-enabled** (ondata1+2, 10 totali):
  `vendite.{fatture, fatture_scadenze, fatturazione_lotti, ordini, preventivi,
  contratti, offerte_commerciali}`, `documenti.documenti_generati`,
  `pratiche.pratiche`, `anagrafiche.billing_account`
  ([provisioning-db-roles.md:27-32](../backend/provisioning-db-roles.md#L27-L32)).
- **Perimetro di SCRITTURA del batch fatturazione** (~16, incl. scritture via trigger):
  `vendite.fatturazione_lotti`, `vendite.fatture`, `vendite.fatture_righe`,
  `vendite.fatture_fondi_fattura`, `vendite.fatture_fondi_fattura_source`,
  `vendite.fatture_riepiloghi_iva`, `vendite.attivita_fatturabili`,
  `vendite.registri_fatturazione_progressivi`, `vendite.fatturazione_lotti_fatture`,
  `vendite.fatture_log`, `vendite.fatturazione_lotti_log`, `vendite.note_fatture`,
  `vendite.fatture_sdi`, `vendite.fatture_scadenze`, `pagamenti.vendite_contabili`,
  `pagamenti.vendite_contabili_righe`. **Questo è l'elenco a cui ancorare i GRANT DML**
  (§5.1).
- **Intersezione scrittura/RLS oggi**: `fatturazione_lotti`, `fatture`, `fatture_scadenze`.
- **Lettura critica oggi**: `anagrafiche.billing_account` è **RLS-enabled ed è letta dalla
  discovery** (`fn_select_attivita_fatturabili`) → sotto contesto non valido il `SELECT`
  torna vuoto → batch a vuoto silenzioso. Le letture toccano inoltre una sfilza di lookup
  in JOIN (`catalogo.articoli`, `config.*`, `anagrafiche.soggetti_ruoli`, registri…):
  enumerarle sarebbe fragile → per la lettura si concede ampio (§5.1).

**Lezione che motiva Path A**: con un approccio per-tabella sulla *RLS* (Opzione B), ogni
futura tabella RLS toccata si tradurrebbe in una nuova policy o → default-deny silenzioso.
Path A sposta il confine sui **GRANT** del ruolo: la scrittura resta limitata al perimetro
noto e un'eventuale tabella mancante fallisce **rumorosamente** (`permission denied`), non
in silenzio.

## 4. Decisione: Path A, modello per-job (e perché non B, e perché non un `_batch` generico)

**Scelta**: per ogni processo headless un **ruolo PostgreSQL dedicato** con `BYPASSRLS`,
**SELECT ampio** sugli schemi applicativi ma **DML limitato al solo perimetro del job**,
usato tramite un **alias Django dedicato**. `zeroerp_app` resta il `DB_USER` del web,
`NOBYPASSRLS`, invariato. Il primo (e oggi unico) ruolo è **`zeroerp_batch_fatturazione`**.

Questo è il **"ruolo batch equivalente"** già previsto dalla doc per "pgAgent, job SQL
pianificati, manutenzione, batch DB puri fuori dal perimetro RLS"
([provisioning-db-roles.md:70-80](../backend/provisioning-db-roles.md#L70-L80)). Il
paletto della doc — *non usare `titodb`/`postgres` come utenza del backend per aggirare
filtri* ([:98-99](../backend/provisioning-db-roles.md#L98-L99),
[:221-222](../backend/provisioning-db-roles.md#L221-L222)) — **resta rispettato**: non
tocchiamo il `DB_USER` del web e non usiamo `postgres`/`titodb`.

**Perché per-job e NON un `zeroerp_batch` generico con grant larghi:**

- Con `BYPASSRLS` la RLS non filtra più → **i GRANT sono l'unico confine DB-enforced
  rimasto**. Un ruolo generico con DML largo (es. membership piena di `zeroerp_app`)
  potrebbe **scrivere ogni tabella applicativa cross-tenant**: è "web-powers cross-tenant",
  l'esatto rischio da evitare. Lo scoping va fatto **da subito**, non "largo ora, stretto
  poi" (sarebbe contraddittorio: un ruolo con grant scoped *è già* il ruolo del suo job).
- La **genericità** che serve sta nel **meccanismo** (alias dedicato + gateway BE
  parametrico + pattern di provisioning), **non** in un ruolo condiviso. Un nuovo job di
  sistema → **nuovo ruolo scoped** (`zeroerp_batch_<job>`), riusando il meccanismo, **mai
  allargando** i grant di un ruolo esistente.
- Il **vettore di danno** di un ruolo BYPASSRLS è la **scrittura** cross-tenant
  (sovrascrivere dati di un altro emittente); il read no. Quindi: SELECT ampio (basso
  rischio, evita di enumerare la sfilza di lookup), DML solo sul perimetro del job.

**Perché NON Opzione B** (sentinel `'SISTEMA'` + policy `_sistema` per-tabella):

- Richiede **una policy RLS per ogni tabella del perimetro**, per sempre; una nuova
  tabella RLS non coperta → **default-deny silenzioso**. Path A fallisce invece
  rumorosamente (`permission denied`), e usa GRANT (più semplici delle policy).
- L'argomento "least-privilege" di B è in parte illusorio: il batch tocca comunque
  l'intero ciclo attivo. In Path A il least-privilege è reale e DB-enforced via i GRANT
  DML scoped.

**Trade-off accettato (e mitigato).** B *fallisce chiuso* (GUC dimenticata → deny). A
*fallisce aperto* (uso errato dell'alias in codice di richiesta → bypass RLS per un
utente reale). Mitigazione obbligatoria in §5.6.

**Evoluzione futura (non ora — YAGNI).** Quando arriverà un secondo processo di sistema si
creerà il suo ruolo+alias scoped. Trade-off da tenere a mente: ruoli per-job = massimo
isolamento ma più credenziali/alias in ops; ruolo condiviso = meno ops ma scope che si
gonfia. Per un canale BYPASSRLS si preferisce l'isolamento.

## 5. Contratto definitivo (Path A, per-job)

### 5.1 Ruolo `zeroerp_batch_fatturazione`

- Attributi: `LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT BYPASSRLS`. **Niente DDL,
  niente owner.**
- **SELECT**: ampio, schema-wide sugli schemi applicativi (come `zeroerp_app`), con
  `ALTER DEFAULT PRIVILEGES` per gli oggetti futuri. Letture cross-tenant a basso rischio;
  enumerare i lookup sarebbe fragile.
- **INSERT/UPDATE/DELETE**: **solo** sul perimetro di scrittura del batch fatturazione
  (le ~16 tabelle elencate in §3) + relative sequenze. È il confine che cap-pa il vettore
  di danno reale (scrittura cross-tenant).
- **NON** via `GRANT zeroerp_app TO zeroerp_batch_fatturazione` (la membership darebbe
  read+write *tutto*): si usa un blocco grant **esplicito** in `provision_db_roles.sql`.
- **`BYPASSRLS`** va settato **diretto** sul ruolo (`ALTER ROLE ... BYPASSRLS`): non è
  ereditabile per membership.
- **Sicurezza direzionale**: ruolo indipendente; `zeroerp_app` (web) non ne è membro →
  non può `SET ROLE` ad esso, non guadagna mai `BYPASSRLS`. Nessuna escalation web→batch.
- **Manutenzione**: quando la pipeline inizia a scrivere una NUOVA tabella, si aggiunge il
  GRANT DML lì (co-locato col codice, **fail-loud**). Nessuna manutenzione sulle letture.

### 5.2 Alias Django dedicato

- Alias `system_fatturazione` in `DATABASES` verso lo **stesso** DB,
  `USER=zeroerp_batch_fatturazione` (nuove env `DB_SYSTEM_FATTURAZIONE_USER`/
  `DB_SYSTEM_FATTURAZIONE_PASSWORD`), **stesso `search_path`** del `default`.
- **Niente DB router automatico**: accesso **opt-in esplicito**
  (`connections['system_fatturazione']` / `.using('system_fatturazione')`) solo nel
  percorso del batch. Mai routing implicito.
- Connessione **separata dal pool del `default`** → nessun rischio di leak GUC sul pool web.

### 5.3 Gateway BE `system_process_context` (parametrico)

- Unico punto d'ingresso per i processi headless, **parametrico per alias + attore di
  audit**: es. `system_process_context(alias="system_fatturazione", actor="BATCH_FATTURAZIONE")`.
  Instrada sull'alias indicato e setta l'identità di audit (§5.4). **Non** setta
  `app.ruolo_applicativo` (la RLS è bypassata dal ruolo; nessuna policy legge quella GUC).
  Così il **meccanismo resta generico** e ogni futuro job passa il proprio alias+attore.
- `run_fatturazione_batch` esegue il corpo dentro il gateway. L'endpoint on-demand
  `pipeline/run-until-done` **resta** nello scope OPERATORE del chiamante (NON usa il
  canale di sistema).

### 5.4 Identità di audit

- Il trigger audit usa `COALESCE(NULLIF(app.jwt_user,''), CURRENT_USER)`. Senza altro,
  le righe risultano `user_insert='zeroerp_batch_fatturazione'` (già pulito).
- **Raccomandato**: il gateway setta `app.jwt_user='BATCH_FATTURAZIONE'` (nome processo)
  così job di sistema diversi restano distinguibili nel giornale/audit.

### 5.5 Ritiri (semplificazione)

- **Non** servono policy `_sistema` per-tabella.
- **Non** serve il sentinel `app.ruolo_applicativo='SISTEMA'`: la costante BE
  `RUOLO_APPLICATIVO_SISTEMA` come *ruolo applicativo* si ritira (non è una veste, non è
  un'`identita_digitali`).

### 5.6 Mitigazione fail-open (obbligatoria)

Il fail-open è la debolezza più affilata di Path A → servono **due** controlli, statico e
runtime, perché coprono buchi diversi.

- **Statico (CI, D8)**: fallisce se `.using('system_…')`/`connections['system_…']` compare
  fuori dai moduli whitelisted (pendant globale del guard anti-drift: uno solo, non uno
  per tabella). Limite: non vede la selezione **dinamica** dell'alias, una misconfig di
  `DATABASES['default']`, o vie che il pattern non intercetta.
- **Runtime (obbligatorio, non "eventuale")**: all'ingresso del percorso richiesta,
  asserire che la connessione attiva **non** è `BYPASSRLS` —
  `SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user` deve essere `false` nel
  contesto web (**fail-closed** se vero). Becca il misuse qualunque sia la via di selezione
  dell'alias.
- **Buco residuo che il runtime guard — non lo scoping DML — chiude**: il ruolo ha
  **SELECT ampio + BYPASSRLS**, quindi un uso errato dell'alias in contesto richiesta
  produrrebbe una **SELECT cross-tenant** (righe di tutti gli emittenti → leak silenzioso),
  e pure una scrittura *dentro* il perimetro bypasserebbe la RLS. Lo scoping DML limita il
  raggio delle scritture fuori perimetro, **non** il caso richiesta: per quello serve il
  runtime guard.

## 6. Impatto sul BE già pushato (Opzione B → Path A)

Il lavoro B non è sprecato: il `_system_db_context` cambia *cosa fa*, non *che esiste*.

- `_system_db_context` → diventa `system_process_context(alias, actor)`: **instrada
  sull'alias dedicato** + setta `app.jwt_user` per audit; **rimuove** il set della GUC
  `app.ruolo_applicativo` e l'azzeramento delle GUC d'identità (non più necessari sul
  canale dedicato).
- `RUOLO_APPLICATIVO_SISTEMA` (ruolo applicativo) → **ritirato**; eventuale costante di
  audit `AUDIT_ACTOR_BATCH_FATTURAZIONE` al suo posto.
- Test BE: da "set/reset GUC SISTEMA" a "il command opera sull'alias `system_fatturazione`
  e produce fatture su ≥2 emittenti con RLS attiva".

## 7. Piano di sviluppo (deliverable)

> Owner: **DB** salvo dove indicato. Stato iniziale: DA FARE.

| # | Deliverable | Owner | Note |
| --- | --- | --- | --- |
| D1 | ✅ Provisioning ruolo `zeroerp_batch_fatturazione` in **`scripts/sql/provision_db_role_batch_fatturazione.sql`** (script dedicato per-job, non `provision_db_roles.sql`): create-if-missing, password idempotente, `ALTER ROLE ... BYPASSRLS`, **SELECT+EXECUTE schema-wide** (+ `ALTER DEFAULT PRIVILEGES` SELECT/EXECUTE, **NO** DML di default), **DML esplicito sulle 16 tabelle del perimetro §3** + sequenze associate (pg_depend) | DB/ops | password fuori da Liquibase; NO membership di `zeroerp_app` |
| D2 | ✅ Script di verifica postura **`scripts/sql/check_db_role_batch_fatturazione.sql`** (dedicato per-job): attributi (BYPASSRLS sì, super/createdb/createrole no), nessuna membership, DML fuori perimetro = 0, buchi DML nel perimetro = 0, SELECT ampio ok, controprova fail-loud su `vendite.ordini`. La query di postura nella doc è in D5 | DB | read-only, ripetibile |
| D3 | ✅ Provisioning CI: **step psql-as-postgres** in `.github/workflows/ci.yaml` ("Provision ruolo batch fatturazione") che riusa lo **stesso** script di D1 (DRY). **NON** un changeset Liquibase: `BYPASSRLS` richiede superuser, mentre Liquibase gira come `zeroerp`/`titodb` (non-superuser) → l'`ALTER ROLE ... BYPASSRLS` fallirebbe | DB | step dopo le migrazioni; `batch_password=secret`, `migrator_role=zeroerp` |
| D4 | ✅ pgTAP postura **`db/pgtap/rls/test-role-batch-fatturazione-postura.sql`** (`plan(11)`): ruolo esiste, LOGIN, `BYPASSRLS`, non super/createdb/createrole, **non** membro di `zeroerp_app`, DML solo sul perimetro (no over-grant, no buchi), SELECT ampio, controprova fail-loud su `vendite.ordini` | DB | struttura, non comportamento; il cross-emittente è BE (D7) |
| D5 | ✅ [provisioning-db-roles.md](../backend/provisioning-db-roles.md): nuova sezione "Ruoli batch per-job `zeroerp_batch_<job>`" + query di postura aggiornata; [contratto-guc-app](../../guide/contratto-guc-app.md): nota "Processi di sistema headless"; [row-level-security.md](../../postgresql/row-level-security.md): nota "Ruoli batch `BYPASSRLS` per-job" nella sezione ruoli DB | DB/doc | wording onesto: ruolo a privilegio scoped che bypassa l'isolamento per-emittente |
| D6 | Alias `DATABASES['system_fatturazione']` in `settings.py` + env `DB_SYSTEM_FATTURAZIONE_USER`/`DB_SYSTEM_FATTURAZIONE_PASSWORD` (`env.sh`, `.env.systemd`); **nessun router** | BE | §5.2 |
| D7 | `system_process_context(alias, actor)` (gateway parametrico) + refactor `run_fatturazione_batch` (§6) + test "batch su ≥2 emittenti con RLS attiva" | BE | sostituisce `_system_db_context` |
| D8 | Guard fail-open (§5.6): **statico** (CI: alias `system_*` fuori whitelist → fail) **+ runtime** (middleware: connessione del percorso richiesta deve essere `rolbypassrls=false`, fail-closed) | BE | due controlli, buchi diversi; il runtime chiude il leak SELECT cross-tenant |
| D9 | Ritiro `RUOLO_APPLICATIVO_SISTEMA` + eventuale `AUDIT_ACTOR_BATCH_FATTURAZIONE` | BE | §5.5/§6 |

**Sequenza di rollout sicura:**

1. D1–D3 (ruolo `zeroerp_batch_fatturazione` + grant scoped + provisioning CI) — può
   atterrare subito, inerte finché nessuno usa l'alias.
2. D6–D7 (alias + gateway + refactor batch) — il batch passa al canale di sistema.
3. D4, D8 (test/guardie) + D5/D9 (doc/cleanup).
4. Verifica congiunta: batch produce fatture su ≥2 emittenti **con RLS attiva**;
   operatore resta isolato (nessuna regressione ondata1/2); processo senza contesto e
   senza canale di sistema resta default-deny (fail-closed).

## 8. Criteri di accettazione

- Con RLS attiva (`ENABLE`), il batch via alias `system_fatturazione` (ruolo
  `zeroerp_batch_fatturazione`) esegue discovery + INSERT lotto + INSERT fatture/scadenze
  su **tutti** gli emittenti, senza default-deny né violazioni.
- Un tentativo di scrittura **fuori dal perimetro** concesso fallisce **rumorosamente**
  (`permission denied`), non in silenzio.
- Le righe scritte dal batch hanno identità di audit riconoscibile
  (`user_insert='zeroerp_batch_fatturazione'` o `app.jwt_user='BATCH_FATTURAZIONE'`).
- Una sessione **operatore** (`zeroerp_app` + GUC) resta isolata per emittente — nessuna
  regressione ondata1/2.
- Un processo **senza** canale di sistema e **senza** contesto operatore resta
  default-deny (fail-closed).
- `zeroerp_batch_fatturazione`: `rolbypassrls=true`, **non** membro di `zeroerp_app`,
  **non** owner, **non** superuser, **non** `DB_USER` del web; DML solo sul perimetro.
- Il check CI fallisce se un alias `system_*` è usato fuori dai moduli whitelisted.

## 9. Coordinamento

- La RLS è **invariante di sistema sempre attivo**: questo brief vale per **ogni**
  processo headless presente e futuro. Il **meccanismo** (alias + gateway + provisioning)
  è generico; i **ruoli** sono per-job e scoped.
- Allineare con l'attivazione/verifica RLS operatori e con il refactor BE (il BE adegua
  l'implementazione B pushata, vedi §6).
- **Trigger di revisione per-job**: alla comparsa del **2° processo di sistema**,
  rivalutare consapevolmente "per-job vs ruolo condiviso-ma-scoped" (vedi trade-off §4) —
  per evitare proliferazione di ruoli/alias per inerzia.
- Nessuna modifica a changelog Liquibase già mergiati; eventuali changeset DB seguono la
  numerazione globale per data.

## 10. Stato e consegna al BE

### Lato DB — CHIUSO (D1–D5)

Il canale di sistema è pronto e verificato su dbdev. Artefatti consegnati:

| Artefatto | File |
| --- | --- |
| Provisioning ruolo (admin DB) | `scripts/sql/provision_db_role_batch_fatturazione.sql` |
| Verifica postura (read-only) | `scripts/sql/check_db_role_batch_fatturazione.sql` |
| Provisioning CI | step psql-as-postgres in `.github/workflows/ci.yaml` ("Provision ruolo batch fatturazione") — riusa lo script D1 (non un changeset Liquibase: BYPASSRLS = superuser-only) |
| pgTAP postura | `db/pgtap/rls/test-role-batch-fatturazione-postura.sql` |
| Doc ruoli | `docs/it/dev/backend/provisioning-db-roles.md` (sez. "Ruoli batch per-job") |
| Doc GUC | `docs/it/guide/contratto-guc-app.md` (sez. "Processi di sistema headless") |
| Doc RLS | `docs/it/postgresql/row-level-security.md` (sez. ruoli DB → "Ruoli batch `BYPASSRLS` per-job") |

Verifiche eseguite su dbdev: ruolo `zeroerp_batch_fatturazione` con `rolbypassrls=t`,
nessuna membership, DML sulle 16 tabelle del perimetro (nessun over-grant, nessun buco),
SELECT ampio attivo, fail-loud su `vendite.ordini`; pgTAP `ok 1..11`.

### Lato BE — DA FARE (D6–D9)

Il DB **non** richiede altro: il BE consuma il canale già pronto.

- **D6** — alias `DATABASES['system_fatturazione']` in `settings.py` (stesso DB,
  `USER=zeroerp_batch_fatturazione`, stesso `search_path`) + env
  `DB_SYSTEM_FATTURAZIONE_USER` / `DB_SYSTEM_FATTURAZIONE_PASSWORD`. **Nessun DB router.**
- **D7** — `system_process_context(alias, actor)` (gateway parametrico) + refactor
  `run_fatturazione_batch`: instrada su `connections['system_fatturazione']` e setta
  `app.jwt_user='BATCH_FATTURAZIONE'`; **rimuove** il set di `app.ruolo_applicativo`
  (sentinel B) e l'azzeramento GUC d'identità. Test: batch su ≥2 emittenti con RLS attiva.
  *Questo sostituisce l'implementazione Opzione B già pushata (`_system_db_context`,
  `RUOLO_APPLICATIVO_SISTEMA`).*
- **D8** — guard fail-open: **statico** (CI: alias `system_*` fuori dai moduli whitelisted
  → fail) **+ runtime** (middleware: connessione del percorso richiesta deve avere
  `rolbypassrls=false`, fail-closed). Vedi §5.6.
- **D9** — ritiro `RUOLO_APPLICATIVO_SISTEMA` (non è una veste) + eventuale costante audit
  `AUDIT_ACTOR_BATCH_FATTURAZIONE`.

> **Credenziale**: la password di `zeroerp_batch_fatturazione` (scelta al provisioning
> manuale) va inserita nelle env D6. In CI il ruolo è creato senza password dal changeset
> ci_apply (DB locale/trusted).
>
> **Endpoint on-demand**: `pipeline/run-until-done` **non** usa il canale di sistema →
> resta nello scope OPERATORE del chiamante. Il canale `system_*` è solo per i percorsi
> headless (cron/command).
