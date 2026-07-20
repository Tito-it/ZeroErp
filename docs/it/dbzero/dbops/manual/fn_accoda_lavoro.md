## 📘 Documentazione Concettuale – Funzione `dbops.fn_accoda_lavoro`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)  
> • [dbops.coda_lavori_tipi](/dbzero/dbops/manual/coda_lavori_tipi)  
>
**Approfondimento funzioni:**
>
• [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)  
>

### 🎯 Scopo Principale
(latest review 20-07-2026)

`dbops.fn_accoda_lavoro` è l'**unica porta d'ingresso** della coda lavori
generica ([dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)): esegue
l'**enqueue atomico e idempotente** di un job. Valida il `job_type` contro il
registry, risolve i default per-tipo, e fa una singola `INSERT` — **atomica per
costruzione** su connessione autocommit. È callable sia da **Python** sia da
**trigger / altro codice DB** (enqueue transazionale da dominio, `origine=TRIGGER`).

Claim, marca esito e reaper **non** sono qui: li fa il worker BE in SQL diretto.
La funzione fornisce solo l'enqueue.

---

### Firma

```sql
dbops.fn_accoda_lavoro(
    p_job_type        text,
    p_payload         jsonb       DEFAULT '{}',
    p_run_as          text        DEFAULT NULL,   -- NULL → run_as_default del tipo
    p_scope           jsonb       DEFAULT NULL,
    p_idempotency_key text        DEFAULT NULL,
    p_priorita        smallint    DEFAULT 100,
    p_run_after       timestamptz DEFAULT NULL,
    p_max_tentativi   int         DEFAULT NULL,    -- NULL → max_tentativi_default del tipo
    p_origine         text        DEFAULT 'API'
) RETURNS bigint   -- id del job (nuovo o, se conflitto idempotente, del job vivo esistente)
```

---

### Regole principali

* **Guard `p_job_type`**: obbligatorio e non vuoto → altrimenti `E_PARAMETRO_INVALIDO`.
* **Guard tipo registrato**: il `job_type` deve esistere in
  [coda_lavori_tipi](/dbzero/dbops/manual/coda_lavori_tipi) → altrimenti
  `E_JOB_TYPE_NON_TROVATO`.
* **Guard tipo attivo**: il tipo deve avere `attivo=true` → altrimenti
  `E_JOB_TYPE_NON_ATTIVO`.
* **Risoluzione default**: `run_as` e `max_tentativi`, se NULL, sono presi dai
  default del tipo (`run_as_default`, `max_tentativi_default`).
* **Guard coerenza scope**: `run_as='OPERATORE'` richiede `p_scope` NOT NULL
  (messaggio parlante `E_PARAMETRO_INVALIDO` prima del CHECK di tabella); il caso
  simmetrico (SISTEMA con scope) lo copre `chk_coda_lavori_run_as_scope`.
* **Idempotente**: `INSERT … ON CONFLICT (job_type, idempotency_key) WHERE …vivo…
  DO NOTHING`; su conflitto ritorna l'`id` del job **vivo** esistente (nessun
  doppione). Copre solo i job vivi (`PENDING`/`IN_CORSO`): a job completato la
  stessa chiave riparte. Il replay «stessa richiesta → stessa risposta» a job
  completato è del layer HTTP `dbops.idempotency_keys`, non di questa funzione.

Solleva sempre via [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)
(SQLSTATE `P0001`). `SECURITY INVOKER` (default): scrive come il ruolo chiamante.

---

### Esempi

Enqueue da endpoint (primo consumatore C-3), scope operatore catturato:

```sql
SELECT dbops.fn_accoda_lavoro(
    'FATTURAZIONE_GIRO',
    p_payload         => '{"competenza":"2026-07","fino_a_stato":"EMESSA"}'::jsonb,
    p_scope           => '{"emittente_ids":[12],"auth_user_id":7}'::jsonb,
    p_idempotency_key => '2026-07|ef:12'
);
```

Enqueue DB-native da un trigger di dominio (`run_as` SISTEMA, nessuno scope):

```sql
PERFORM dbops.fn_accoda_lavoro(
    'INVIA_PEC',
    p_payload => jsonb_build_object('documento_id', NEW.id),
    p_run_as  => 'SISTEMA',
    p_origine => 'TRIGGER'
);
```

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_PARAMETRO_INVALIDO` | `p_job_type` NULL/vuoto, oppure OPERATORE senza `p_scope` |
| `E_JOB_TYPE_NON_TROVATO` | `job_type` non presente in `coda_lavori_tipi` |
| `E_JOB_TYPE_NON_ATTIVO` | `job_type` presente ma `attivo=false` |

Brief: `brief-db-coda-lavori-generica` §3.

---

{% include-markdown "signature-core.md" %}
