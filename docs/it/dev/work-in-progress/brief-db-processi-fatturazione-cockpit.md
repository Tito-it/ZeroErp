# Brief DB — Cockpit processi fatturazione (Fase A/C)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Stato**: 🟢 **G1 APPLICATO + COMMITTATO + PUSHATO (2026-07-20**, commit
> `67d63cae9`; verifica §8 G1.a-d eseguita sul DB vivo, ok). **G2** (append pipeline) resta
> **DA FARE alla release BE** — l'ok arriva dal BE allo step C-10 del
> [brief BE/FE](brief-be-fe-processi-fatturazione.md).
>
> **Design-of-record**:
> [brief-design-gestione-processi-fatturazione.md](brief-design-gestione-processi-fatturazione.md)
> — decisioni **D-1..D-7** chiuse da Tid il 2026-07-19.
> **Gate**: BE/FE partono a oggetti DB applicati ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → breaking
> secchi ammessi, nessuna compatibilità da mantenere.
>
> **Sintesi**: il motore di fatturazione è già completo, ma la stampa massiva **non esiste**
> e va costruita **senza tenere il lock del registro fiscale durante il rendering**. La stampa
> diventa un **task che accoda** (non che renderizza) e il render vive in un **worker che
> drena una coda** (outbox), con la numerazione garantita in fase di stampa (backstop
> idempotente). Perciò questo brief **non è "solo seed"**: aggiunge **una tabella-coda + una
> funzione di accodamento**, oltre ai seed. Nessuna modifica alle viste `vw_dash_*` né alla
> matrice transizioni.
>
> ⚠️ **Revisione 2026-07-19 (analisi critica)**: la prima stesura ("solo seed, stampa come
> task inline, best-effort") è stata **superata**. Motivo, verificato sul codice vivo:
> lo **step pipeline è una singola transazione atomica** ([`pipeline_runner.py:316`]),
> e la numerazione tiene un **`pg_advisory_xact_lock` sul registro** fino al commit
> ([`fn_get_next_progressivo`]). Un task di stampa *inline* renderizzerebbe i PDF **mentre il
> lock fiscale è tenuto** → serializzazione del registro contro ogni altra numerazione
> (corsia giornaliera, altri lotti). La soluzione corretta disaccoppia il render dalla
> transazione di numerazione. Vedi §0.

---

## 0. Decisioni chiuse a monte di questo brief (2026-07-19)

Consolidate con Tid dopo l'analisi critica del motore reale. Le richiamo perché reggono ogni
scelta operativa qui sotto.

| # | Decisione | Perché (verifica sul codice) |
| --- | --- | --- |
| **B-1** | La stampa **accoda**, non renderizza inline. Il task `stampa_documenti_lotto` scrive N righe in una **coda** (outbox) e ritorna subito; un **worker** separato drena e renderizza. | Lo step è **una transazione atomica** ([`pipeline_runner.py:316`]) e `numera_fatture` tiene il **lock del registro** fino al commit. Render inline = lock fiscale tenuto durante l'I/O di N PDF → contesa. |
| **B-2** | **La stampa garantisce la numerazione**: in fase di stampa, se la fattura non è numerata, il worker chiama la numerazione (backstop **idempotente**). | `fn_numera_fattura_opz_emessa(p_fattura_id)` è **per-fattura e idempotente** (se già numerata → no-op). È impossibile produrre un PDF non numerato → **D-1** soddisfatto al livello più forte. |
| **B-3** | `numera_fatture` **resta** come task dello step DEFINITIVA (pre-numerazione bulk): "Rendi definitive" assegna i numeri **subito** a tutto il lotto, atomico. Il backstop B-2 è la rete di sicurezza, non il sostituto. | Coerente col verbo «Rendi definitive = numera adesso» (design §3). |
| **B-4** | Coda dedicata **`vendite.fatture_stampa_coda`** (scoped a fatturazione ora, colonne già "a forma di" `genera_documento()` → promozione a `documenti.*` banale al 2° consumatore). | Regola di progetto *«generalizzazione al 2° consumatore»* ([[reference_link_parametrico_documento_versionato_pratiche]]); il servizio di render è già generico. |
| **B-5** | Il **worker drainer** è un **management command su cron/systemd** (server backend), **non** pgAgent. | I due server sono separati; `run_fatturazione_batch` gira già così (cron/systemd), monitor `maintenance.job_run_log`. → **niente `85_pgagent` in questo brief.** |

**Best-effort vs bloccante (ex §3.4): la domanda non si pone più.** Con B-1 lo step committa
veloce (solo l'INSERT in coda, nessun render) e il fallimento di render vive nei **tentativi
della coda**, disaccoppiato dalla numerazione. Nessuno stato "numerata ma non stampata" da
gestire nella pipeline.

---

## 1. Perché (contesto in tre righe)

La pipeline di fatturazione oggi si pilota solo da cron/curl: nessuna superficie in app.
Il design collegato porta i processi **dentro la Dashboard Competenza** (approva → fattura
→ rendi definitive → stampa). Perché il BE possa esporre le azioni servono due permessi di
processo seedati; perché la stampa massiva esista serve una **coda** e un **accodatore**;
perché **D-1** («numerazione e stampa = un processo unico, mai duplicato») e **D-7** («la
stampa è separata e senza logica») convivano, la stampa vive **nello stesso step della
numerazione** ma come **adattatore che accoda** — la logica di render resta nel processo
generico.

---

## 2. Sequenza di applicazione — DUE gruppi di changeset (⚠️ leggere prima di tutto)

Il punto critico dell'intero brief. Gli oggetti si applicano in **due momenti distinti**,
perché wire-are la stampa nella pipeline **prima** che il BE esista rompe il giro notturno.

**Verifica del rischio (sul codice):** l'executor, se l'handler del task non è registrato,
**solleva `E_TASK_IMPLEMENTATION_NOT_FOUND` (severità C) e fa fallire lo step**
([`pipeline_step_executor.py:173-204`]). La corsia **GIORNALIERO** esegue la DEFINITIVA da
sola (cron `run_fatturazione_batch --modalita immediata`, D-1): se la stampa fosse già
accodata nei `processi` ma l'handler non esistesse, ogni notte `numera_fatture` numererebbe
e **poi** lo step crasherebbe. È il pattern che [[reference_binding_handler_flusso_attivo_false]]
esiste per evitare: **si arma alla release BE, non prima.**

| Gruppo | Quando | Cosa | Stato risultante |
| --- | --- | --- | --- |
| **G1 — Fondamenta (inerti)** | **Ora**, su `dev/db-tid` | Tabella-coda (00_schema) · funzione accodamento (20_code) · seed azioni_processo · seed registry+impl `stampa_documenti_lotto` · seed **task_policy** stampa | Tutto **inerte**: la coda è vuota (nessuno vi scrive), registry/impl/policy sono lookup non referenziati, la funzione non è chiamata. Zero impatto sul giro notturno. |
| **G2 — Attivazione** | **Alla release BE** (handler `stampa_documenti_lotto_default` + drainer deployati) | Append di `stampa_documenti_lotto` ai `processi` degli step DEFINITIVA (id 4 e 6) | La stampa entra in pipeline. **Questo append è l'interruttore.** |

> Regola: **MAI** committare G2 finché il BE non ha registrato l'handler e schedulato il
> drainer. G1 è sicuro in qualsiasi momento.

---

## 3. G1 — Tabella-coda `vendite.fatture_stampa_coda` (00_schema)

Una riga = **un documento da generare** (granularità per-fattura → retry/esito per documento).
**Satellite di `vendite.fatture`**: `sorgente_id = fatture.id`, nessuna colonna emittente
denormalizzata (la RLS delega alla fattura — vedi note). Migration:
[20260720-01-create-fatture-stampa-coda-mctit.yaml](../../../../db/changelog/migrations_v2/00_schema/vendite/20260720-01-create-fatture-stampa-coda-mctit.yaml).

```sql
CREATE TABLE vendite.fatture_stampa_coda (
    id                    bigint  GENERATED ALWAYS AS IDENTITY
                            CONSTRAINT pk_fatture_stampa_coda PRIMARY KEY,
    sorgente_tipo_id      bigint  NOT NULL,   -- = FATTURA (config.sorgenti). "A forma di" genera_documento()
    sorgente_id           bigint  NOT NULL,   -- = vendite.fatture.id (FK)
    sorgente_uid          text    NOT NULL,   -- key_selector FATTURA = id::text
    lotto_id              bigint  NULL,        -- provenienza; NULL per ristampa on-demand
    template_documento_id bigint  NULL,        -- override opzionale del template
    stato                 text    NOT NULL DEFAULT 'PENDING',
    tentativi             integer NOT NULL DEFAULT 0,
    ultimo_errore         jsonb   NULL,
    documento_id          bigint  NULL,        -- documento prodotto (esito)
    data_insert   timestamp with time zone NOT NULL DEFAULT now(),
    user_insert   text NOT NULL DEFAULT CURRENT_USER,
    data_update   timestamp with time zone NOT NULL DEFAULT now(),
    user_update   text NOT NULL DEFAULT CURRENT_USER,
    tx_id         uuid NULL,
    CONSTRAINT chk_fatture_stampa_coda_stato
        CHECK (stato IN ('PENDING','IN_CORSO','FATTO','ERRORE')),
    CONSTRAINT chk_fatture_stampa_coda_tentativi CHECK (tentativi >= 0),
    CONSTRAINT fk_fatture_stampa_coda_fattura
        FOREIGN KEY (sorgente_id) REFERENCES vendite.fatture (id) ON DELETE CASCADE,
    CONSTRAINT fk_fatture_stampa_coda_lotto
        FOREIGN KEY (lotto_id) REFERENCES vendite.fatturazione_lotti (id) ON DELETE SET NULL
);

-- Anti doppio-accodamento: un solo work-item VIVO per fattura (parziale).
CREATE UNIQUE INDEX uq_fatture_stampa_coda_vivo
    ON vendite.fatture_stampa_coda (sorgente_tipo_id, sorgente_id)
    WHERE stato IN ('PENDING','IN_CORSO');

-- Polling FIFO del worker sui soli da-lavorare.
CREATE INDEX ix_fatture_stampa_coda_da_lavorare
    ON vendite.fatture_stampa_coda (id)
    WHERE stato IN ('PENDING','IN_CORSO');
```

**Note di implementazione:**

* **Indice unico parziale** (non `UNIQUE` inline): vale solo su `PENDING/IN_CORSO` → consente
  il ri-accodamento dopo `FATTO`/`ERRORE` per una ristampa. È il meccanismo che rende
  `fn_accoda_stampe_lotto` idempotente.
* **FK**: `sorgente_id` → `vendite.fatture` (`ON DELETE CASCADE`), `lotto_id` →
  `vendite.fatturazione_lotti` (`ON DELETE SET NULL`). `template_documento_id`/`documento_id`
  restano `bigint` senza FK (tabelle in schema `documenti`) — documentati. **Indici FK non a
  mano**: gestiti da `dbops.apply_fk_index_policy()` in `90_end`. `fn_populate` registra le FK
  a `consentito=false`; l'opt-in è **deliberato** via seed
  [20260720-03-upsert-dbops-fk-index-policy-fatture-stampa-coda](../../../../db/changelog/migrations_v2/80_data/changelog/20260720-03-upsert-dbops-fk-index-policy-fatture-stampa-coda-mctit.yaml):
  **entrambe = true**: `lotto_id` (filtro/monitor per lotto), `sorgente_id` (storico/lookup
  stampe per fattura su tutti gli stati — l'unico parziale `uq_fatture_stampa_coda_vivo` copre
  solo i vivi).
* **RLS — DIFFERITA (scelta di implementazione).** In G1 la coda **non ha superficie di
  lettura operatore** (nessun endpoint, tabella vuota) → **nessuna policy** ora. L'attivazione
  RLS operatori segue il **playbook della famiglia fatture** (crea policy → `ENABLE`) con
  changeSet **ondata separato**, quando atterra il read-side lato BE. La coda è **satellite
  della fattura**: la policy operatore userà `script.fn_scope_ef_whitelist_via_fattura(auth_user, sorgente_id)`
  (adapter esistente), la scrittura del worker resta in **canale sistema** — nessuna colonna
  emittente da denormalizzare, nessuna policy nuova da inventare.
* **`stato` come CHECK e non lookup**: stato di lavorazione tecnico, non dato di dominio → CHECK.
* **`sorgente_uid`**: `key_selector` FATTURA = `id::text` ([[reference_sorgente_polimorfa_key_selector]]);
  la funzione §4 è l'unico punto che lo calcola.
* Doc **manuale** in `docs/it/dbzero/vendite/manual/` (la auto-gen la rigenera Tid al migrate —
  **non** editarla a mano, [[feedback_no_hand_edit_autogen_docs]]).

---

## 4. G1 — Funzione di accodamento `vendite.fn_accoda_stampe_lotto` (20_code)

Rende il task di stampa un **one-liner** (D-7: adattatore stupido). Migration:
[20260720-02-create-fn-accoda-stampe-lotto-mctit.yaml](../../../../db/changelog/migrations_v2/20_code/vendite/20260720-02-create-fn-accoda-stampe-lotto-mctit.yaml).
Contratto:

* **Input**: `p_lotto_id BIGINT`.
* **Effetto**: per **ogni fattura non esclusa del lotto** (via bridge
  `vendite.fatturazione_lotti_fatture`, `esclusa IS NOT TRUE`), inserisce una riga `PENDING`
  in `vendite.fatture_stampa_coda` (`sorgente_tipo_id` risolto da `config.sorgenti` = FATTURA,
  `sorgente_id = fatture.id`, `sorgente_uid = id::text`, `lotto_id = p_lotto_id`). L'emittente
  **non** è denormalizzato: lo risolve il worker dalla fattura al drain.
  **Idempotente** grazie all'indice unico parziale: un secondo accodamento sullo stesso lotto
  non duplica i work-item vivi (`ON CONFLICT DO NOTHING`).
* **Guard**: `p_lotto_id NULL/<=0` → errore (`E_PARAMETRO_INVALIDO`, codice registrato —
  [[feedback_error_codes_messaggi_errore]]). Nessuna riga fattura → ritorno 0 (non è errore).
* **Ritorno**: numero di righe accodate (per log/esito task).
* **Atomicità**: pura-DB, una `SELECT fn_()` — madre DB ([[feedback_atomicita_madre_db]]).
  Gira **dentro** la transazione dello step (commit veloce con la numerazione).
* **`plpgsql`**, `%TYPE` sulle colonne riflesse, commenti sintetici sullo scopo/regole.

Il task BE `stampa_documenti_lotto_default` (brief BE) sarà quindi solo:
`SELECT vendite.fn_accoda_stampe_lotto(<lotto_id>)`. Il **backstop B-2** (numera-se-manca) e
il **render** vivono nel **worker drainer** (brief BE), non qui.

---

## 5. G1 — Seed (append a CSV `runOnChange`, nessun loader nuovo)

Tutti e tre i loader coinvolti sono `runOnChange: true` + `validCheckSums: [ANY]` +
`loadUpdateData(primaryKey: id, nullValue: "")` → **ripescano da soli** l'append. **Nessun
nuovo loader** ([[feedback_messaggi_errore_no_new_loader]]).

### 5.1 `config/azioni_processo.csv` — due azioni

Ultimo `id` occupato: **25**. `area_id = 2` = `vendite`.

```csv
26,2,approva_attivita_commessa,Approva attivita di commessa per la fatturazione,f,t,{},2026-07-19 00:00:00+02,postgres,2026-07-19 00:00:00+02,postgres
27,2,numera_fatture_lotti,Numerazione fiscale fatture di lotto (irreversibile),t,t,{},2026-07-19 00:00:00+02,postgres,2026-07-19 00:00:00+02,postgres
```

| Codename | `pericolosa` | Perché serve |
| --- | :--: | --- |
| `approva_attivita_commessa` | `f` | Gate dell'azione **Approva** (riga, commessa, massiva mese — D-3). `fn_approva_commessa_attivita` non ha né endpoint né permesso: decide *cosa entra in fattura*, merita permesso proprio. |
| `numera_fatture_lotti` | **`t`** | D-1: la numerazione è **irreversibile** (dopo la DEFINITIVA solo NC) ed è **atto umano esplicito** per il massivo. Distinta da `genera_fatture_lotti` (giro fino a EMESSA, pre-fiscale/demolibile). **Non ridondante col backstop B-2**: il backstop è la rete di sicurezza della stampa, non l'atto di numerazione massiva. |

### 5.2 `dbops/pipeline_task_registry.csv` — task stampa

Ultimo `id`: **17**. `dominio_id = 1` (dominio fatturazione).

```csv
18,1,stampa_documenti_lotto,Accodamento stampa documenti del lotto (delega a coda + processo generico),true,{},2026-07-19 00:00:00+02,titodb,,
```

Nome `stampa_documenti_lotto` (non `genera_stampa_fatture`): dice ciò che il task **fa** —
**accoda** i documenti del lotto. Il render non è suo (D-7).

### 5.3 `dbops/pipeline_task_registry_impl.csv` — handler

Ultimo `id`: **17**. `handler_code` = `stampa_documenti_lotto_default` (chiave che il BE
registra nel dispatch).

```csv
18,18,default,stampa_documenti_lotto_default,true,true,{},2026-07-19 00:00:00+02,titodb,,
```

### 5.4 `vendite/fatturazione_pipeline_task_policy.csv` — ⚠️ policy del task (lacuna colmata)

**Motivo (verificato):** l'executor crea un `task_run` (tentativi/esito/resume) **solo se
esiste una task_policy** per quel `(pipeline_id, task_code)` ([`pipeline_step_executor.py:208`]).
Senza questa riga, `stampa_documenti_lotto` **non avrebbe task_run né resume**. Ultimo `id`: **14**.

```csv
15,4,stampa_documenti_lotto,t,RESUME_TASK,t,"{""scope"":""DEFINITIVA""}",2026-07-19 00:00:00+02,titodb,,
16,6,stampa_documenti_lotto,t,RESUME_TASK,t,"{""scope"":""DEFINITIVA"",""tipo_lotto"":""GIORNALIERO""}",2026-07-19 00:00:00+02,titodb,,
```

`annullabile = t` (l'accodamento è ri-eseguibile, a differenza di `numera_fatture` che è
`f`); `resume_mode = RESUME_TASK` (su resume ri-esegue il solo task, non l'intero step —
`numera_fatture`, già fatto e `annullabile=f`, resta com'è).

---

## 6. G2 — Attivazione: append ai `processi` DEFINITIVA (⚠️ solo alla release BE)

`vendite/fatturazione_pipeline.csv` — le righe da toccare sono **due**, simmetriche (è il
punto di D-1):

| id | Step | `processi` oggi | Diventa |
| --- | --- | --- | --- |
| **4** | Massiva (DEFINITIVA), `stato_doc_fiscale_id=8` | `[numera_fatture]` | `[numera_fatture, stampa_documenti_lotto]` |
| **6** | Giornaliera (DEFINITIVA), `stato_doc_fiscale_id=8` | `[numera_fatture]` | `[numera_fatture, stampa_documenti_lotto]` |

Elemento da accodare all'array `processi` (dopo `numera_fatture` — si accoda alla stampa un
documento che ha già il suo numero fiscale):

```json
{"task":"stampa_documenti_lotto","fase":"Stampa documenti lotto","params":{"implementation_key":"default"}}
```

> `fase` = **"Stampa documenti lotto"** (non "Generazione stampa fatture"): coerente col nome
> del task e con D-7 (il task accoda, non genera).

Cella CSV risultante (doppie virgolette Liquibase) per lo step 4:

```text
"[{""task"":""numera_fatture"",""fase"":""Numerazione fatture"",""params"":{""implementation_key"":""default""}},{""task"":""stampa_documenti_lotto"",""fase"":""Stampa documenti lotto"",""params"":{""implementation_key"":""default""}}]"
```

(idem per lo step 6). `rollback` resta `[]` su entrambi (dalla DEFINITIVA non si torna
indietro). Loader `20260128-06-upsert-fatturazione-pipeline` già `runOnChange`.

**Anti-contesa (garanzia B-1):** lo step ora fa `numera_fatture` (numera + `pg_advisory_xact_lock`
tenuto) **+** `stampa_documenti_lotto` (**solo INSERT in coda**). L'INSERT è O(N righe) in
memoria, veloce: la transazione committa e **rilascia subito il lock del registro**. Il
rendering avviene **dopo**, nel worker, **senza** lock fiscale.

---

## 7. Fuori scope DB (per non cercarlo / per il brief BE)

* **Worker drainer** (`ensure_numbered` backstop B-2 + `DocumentGenerationService.genera_documento`
  per riga + gestione tentativi/`ultimo_errore`) → **brief BE**, management command su
  cron/systemd, monitor `maintenance.job_run_log` (come `run_fatturazione_batch`).
* **Handler `stampa_documenti_lotto_default`** (`SELECT vendite.fn_accoda_stampe_lotto(...)`)
  → brief BE.
* **Cablaggio FATTURA** sulla factory documentale (`config.sorgenti` id 10 esiste ma non è
  istanziata) + template fattura → brief BE.
* **Backstop B-2**: vive nel worker/context-builder FATTURA, **non** dentro
  `DocumentGenerationService` (che resta generico e stupido — D-7).
* Nessuna vista nuova (`list_lotti` copre già competenza/stato/tipo_doc/emittente — DB-3
  chiusa nel design). Nessuna modifica a `vw_dash_*`, alla matrice transizioni, a
  `fn_approva_commessa_attivita` / famiglia task-run (coprono già).

---

## 8. Verifica attesa dopo l'apply

```sql
-- G1.a: le due azioni esistono, attive, area vendite
SELECT id, permission_codename, pericolosa, attivo
FROM config.azioni_processo
WHERE permission_codename IN ('approva_attivita_commessa','numera_fatture_lotti');
-- atteso: 2 righe, attivo=t, numera_fatture_lotti.pericolosa=t

-- G1.b: task stampa nel registry, dispatchabile
SELECT r.task_code, i.handler_code, i.is_default, i.attivo
FROM dbops.pipeline_task_registry r
JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
WHERE r.task_code = 'stampa_documenti_lotto';
-- atteso: 1 riga, handler=stampa_documenti_lotto_default, is_default+attivo true

-- G1.c: policy del task su ENTRAMBE le corsie DEFINITIVA
SELECT pipeline_id, task_code, annullabile, resume_mode, attivo
FROM vendite.fatturazione_pipeline_task_policy
WHERE task_code = 'stampa_documenti_lotto';
-- atteso: 2 righe (pipeline 4 e 6), annullabile=t, resume_mode=RESUME_TASK, attivo=t

-- G1.d: coda + funzione esistono
SELECT to_regclass('vendite.fatture_stampa_coda') IS NOT NULL AS coda_ok,
       to_regprocedure('vendite.fn_accoda_stampe_lotto(bigint)') IS NOT NULL AS fn_ok;
-- atteso: coda_ok=t, fn_ok=t

-- G2 (dopo attivazione): entrambi gli step DEFINITIVA hanno numerazione E stampa, in ordine
SELECT tipo_lotto, jsonb_path_query_array(processi, '$[*].task') AS tasks
FROM vendite.fatturazione_pipeline
WHERE stato_doc_fiscale_id = 8 AND attivo;
-- atteso: 2 righe, entrambe ["numera_fatture","stampa_documenti_lotto"]

-- G2: invariante D-1 — nessuna asimmetria fra le due corsie
SELECT count(DISTINCT processi) AS varianti
FROM vendite.fatturazione_pipeline
WHERE stato_doc_fiscale_id = 8 AND attivo;
-- atteso: 1  → le due corsie eseguono lo STESSO processo
```

---

## 9. pgTAP

Due file, uno per gruppo (così il test G2 non fallisce finché l'attivazione non è applicata):

**`db/pgtap/vendite/test-stampa-coda-fondamenta-v1.sql`** (G1 — **scritto**, `plan(18)`):
struttura coda (tabella/colonne/`stato` text/`CHECK`/indice unico parziale/indice polling/FK
fattura), esistenza+ritorno `fn_accoda_stampe_lotto(bigint)`, e i seed (2 azioni attive,
`numera_fatture_lotti` pericolosa, registry+impl stampa attivi/default, 2 task_policy su
pipeline 4/6). **Strutturale+seed, CI-safe**: il test funzionale dell'idempotenza di
`fn_accoda_stampe_lotto` richiede un lotto+fatture reali (guard emittente scope) → coperto da
un integration test lato BE, non qui; l'invariante anti-doppione è comunque blindata
dall'asserzione sull'indice unico parziale.

**`db/pgtap/vendite/test-pipeline-definitiva-numerazione-stampa-v1.sql`** (G2, aggiungere con
l'attivazione):

1. lo step DEFINITIVA MASSIVO contiene `numera_fatture` **seguito da** `stampa_documenti_lotto`;
2. idem GIORNALIERO;
3. **invariante D-1**: i `processi` dei due step DEFINITIVA attivi sono **identici** (una sola
   variante distinta) — traduzione in test di *«mai processi duplicati/divergenti»*.

(pgTAP: `BEGIN;` + CF validi fissi + fixture preventivi con `emittente_fiscale_id`/`iva_id`
obbligatori, [[feedback_pgtap_patterns]] / [[feedback_pgtap_preventivi_fixtures]].)

---

## 10. Naming Liquibase (numerazione NN globale per data — [[feedback_liquibase_numerazione_globale_per_data]])

`YYYYMMDD-NN-<tipo>-<descrizione>.yaml`, un changeSet per file, sempre `logicalFilePath`.
NN = **sequenza globale per data** (i `20260719-*` arrivano a `-16` → i nuovi partono da
`20260720-01`). File creati:

* `00_schema/vendite/20260720-01-create-fatture-stampa-coda-mctit.yaml` — CREATE TABLE
  (incluso via `changelog-autogen.yaml`, che si rigenera al migrate —
  [[feedback_no_autogen_changelog_manuale]]).
* `20_code/vendite/20260720-02-create-fn-accoda-stampe-lotto-mctit.yaml` — `fn_accoda_stampe_lotto`.
* `80_data/` — **solo append ai CSV esistenti** (§5): nessun nuovo `.yaml`, i loader
  `runOnChange` ripescano.
* `db/pgtap/vendite/test-stampa-coda-fondamenta-v1.sql` — pgTAP G1.
* G2 (da fare): append al CSV `fatturazione_pipeline.csv` (§6) — di nuovo nessun `.yaml` nuovo.

---

## 11. Sequenza operativa

1. **G1** (ora): tabella + funzione + seed (§3–5) → pgTAP fondamenta verdi → PR su `dev/db-tid`.
2. Parte il **BE/FE** ([brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)):
   handler `stampa_documenti_lotto_default` (accoda), worker drainer (backstop + render),
   cablaggio FATTURA.
3. **G2** (alla release BE, handler + drainer deployati): append ai `processi` DEFINITIVA
   (§6) → pgTAP pipeline verdi → PR. **Non prima.**

*Le azioni DB non le esegue l'agent ([[feedback_db_actions_passaggio_team]]).*
