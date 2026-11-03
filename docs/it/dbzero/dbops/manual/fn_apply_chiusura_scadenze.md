## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_chiusura_scadenze`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Guide:
> [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali)
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)
>
Approfondimento tabelle:
> [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze)
> [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
WIP:
> [Automazione chiusure per scadenza](/dev/work-done/automazione-chiusure-scadenze)

### 🎯 Scopo Principale

(latest review 26-04-2026)

La funzione **`dbops.fn_apply_chiusura_scadenze()`** e' il **motore del
framework parametrico di chiusura per scadenza**: itera su
`dbops.automazione_chiusura_scadenze` (righe `attivo=true`) ed esegue
UPDATE dinamici per portare lo stato gestionale al valore "chiuso"
sulle righe target con `valido_al` scaduto.

E' invocata dal job pgAgent unico `chiusura_scadenze_daily` ogni
notte alle 00:05. Ritorna un JSONB con conteggio righe chiuse per
tabella + meta-info di esecuzione.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_chiusura_scadenze(
    p_classe text DEFAULT NULL     -- NULL = tutti i bersagli, come prima
) RETURNS jsonb
LANGUAGE plpgsql;
```

La configurazione vive nella tabella
[dbops.automazione_chiusura_scadenze](/dbzero/dbops/manual/automazione_chiusura_scadenze):
una riga per tabella bersaglio.

#### ⭐ `p_classe` *(dal 2026-09-04)* — lavora solo i bersagli di quella natura

⚠️ **Il default `NULL` non è pigrizia, è un requisito**: il job pgAgent chiama
la funzione **senza argomenti**, e la configurazione dello scheduler è una fase
che in CI **non gira mai**. Cambiare la chiamata avrebbe voluto dire modificare
qualcosa che nessun test esercita, e scoprire l'errore di notte.

⇒ Chiamata senza argomenti: comportamento **identico a prima**. Con una classe:
lavora solo quei bersagli.

⭐ **A cosa serve davvero**: è ciò che permetterà ai bersagli di `DOMINIO` di
migrare sulla coda — dove girano con l'identità di un operatore — **senza che
pgAgent li lavori una seconda volta**. Il filtro esiste prima della migrazione,
non dopo, così la migrazione non richiede di toccare il job.

---

### Output (JSONB)

```json
{
  "vendite.listini_versioni": 3,
  "vendite.contratti": 12,
  "_total": 15,
  "_executed_at": "2026-04-27T00:05:01.234567+02:00"
}
```

* Una chiave `<schema>.<tabella>` per ciascuna riga di config processata, con il numero di righe chiuse (puo' essere 0).
* `_total`: somma dei conteggi.
* `_executed_at`: timestamp di chiusura del run.

---

### Logica operativa

1. **Iterazione** sulle righe `attivo=true` di `dbops.automazione_chiusura_scadenze`, ordinate per `id`.
2. **Pre-check** per ogni riga di config:
   * **Tabella target esistente**: verifica via `to_regclass(format('%I.%I', schema, nome))`.
   * **Colonne `col_stato` + `col_valido_al` esistenti**: verifica su `pg_attribute`.
   * **Per `tipo_stato='FK'`**: anche `fk_lookup_schema.fk_lookup_table` deve esistere; pre-check del lookup combinato di `stato_attivo_codice` + `stato_chiuso_codice` su `codice_interno`.
   * In caso di config invalida: `script.fn_log_and_raise_error` con codice `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` (fail-fast, no exec parziale).
3. **UPDATE dinamico** con `format(%I)` / `format(%L)` per identificatori e valori:
   * `tipo_stato='VARCHAR'`: UPDATE diretto.
   * `tipo_stato='FK'`: lookup combinato id_attivo/id_chiuso (via pivot `MAX(CASE...)` in 1 round-trip), poi UPDATE con id risolti.
4. **Aggregazione** del conteggio righe chiuse in JSONB.
5. **Audit log** (best-effort): chiamata a `dbops.fn_audit_log_once(p_function_name='dbops.fn_apply_chiusura_scadenze', p_status='OK', p_params=<risultato JSONB>)`. Eventuali errori di audit sono catturati con `EXCEPTION WHEN OTHERS THEN NULL` per non bloccare il caller (il JSONB con i conteggi viene comunque ritornato).
   ⚠️ Lo stesso `WHEN OTHERS` rende muto un audit che non si scrive: fino al 3 novembre 2026 lo status era `INFO`, che `chk_audit_status` rifiuta, e l'audit di questa funzione non si è mai scritto (`brief-db-revisione-maintenance` R5). Lo presidia `db/pgtap/dbops/test-chiusura-scadenze-audit-v1.sql`.

---

### Sicurezza SQL dinamico

* **Identificatori**: `format(%I)` (alias di `quote_ident`) per `schema_tabella`, `nome_tabella`, `col_stato`, `col_valido_al`, e i campi di lookup FK.
* **Valori**: `format(%L)` (alias di `quote_literal`) per `stato_attivo_codice`, `stato_chiuso_codice`, e gli id risolti (cast a text).
* I valori in `dbops.automazione_chiusura_scadenze` sono comunque amministrativamente controllati (Liquibase seed), ma l'igiene e' applicata per principio.

---

### Le testate sotto la porta del modello (rev 2026-10-28)

Una testata con la porta del modello del documento (`script.trgfn_doc_stato_solo_dal_verbo`)
non si chiude con l'`UPDATE` dinamico: la funzione chiama il **verbo di chiusura** dichiarato
nella colonna `verbo_chiusura` del registro (oggi `vendite.fn_cessa_contratti_scaduti` per il
contratto, `vendite.fn_chiudi_versioni_listino_scadute` per la versione di listino e, dal
31-10-2026, `vendite.fn_chiudi_preventivi_scaduti` per il preventivo). Verbo
assente, o non una funzione viva senza argomenti: `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA`.

### Compatibilita' con guard tabella-specifici

Ogni UPDATE eseguito dalla funzione attraversa eventuali trigger
`trg_<tabella>_a10_guard_transizione_stato_upd` e li **soddisfa per
costruzione**: la precondizione temporale del guard
(`NEW.valido_al < CURRENT_DATE`) e' identica al WHERE della query
del framework. Nessun bypass, nessun GUC, nessun privilegio elevato.

---

### Errori sollevati

| Codice | Quando |
| --- | --- |
| `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` | Riga di config inapplicabile: tabella/colonna/tabella lookup inesistenti, o codice FK non trovato. Il `context` JSONB contiene `config_id`, `target`, `motivo`. |

---

### Esempi

**1) Esecuzione manuale (debug/recovery):**

```sql
SELECT dbops.fn_apply_chiusura_scadenze();
-- {"vendite.listini_versioni": 0, "vendite.contratti": 1, "_total": 1, "_executed_at": "..."}
```

**2) Esecuzione schedulata via job pgAgent:**

```sql
-- Da dentro il job step 'run_chiusura_scadenze':
SELECT dbops.fn_apply_chiusura_scadenze();
```

**3) Disattivare temporaneamente una tabella prima di eseguire:**

```sql
UPDATE dbops.automazione_chiusura_scadenze
   SET attivo = false
 WHERE schema_tabella = 'vendite' AND nome_tabella = 'contratti';

SELECT dbops.fn_apply_chiusura_scadenze();
-- {"vendite.listini_versioni": 0, "_total": 0, "_executed_at": "..."}
```

---

### Note operative

* **Idempotenza**: la query seleziona solo righe ancora attive con `valido_al` scaduto; esecuzioni ripetute nella stessa giornata sono no-op.
* **Performance**: le query sono O(N×K) dove N = righe config attive (oggi 2), K = costo UPDATE singola tabella. Trascurabile per i volumi previsti. Indice parziale `ix_automazione_chiusura_scadenze_attivo` supporta la scansione iniziale anche con N grande.
* **Fail-fast**: nessun EXCEPTION handling per "isolare" il fallimento di una riga: se UPDATE su una tabella fallisce, l'intero run termina in errore (visibile in `pga_joblog`). Scelta deliberata per non nascondere errori.
* **Concorrenza**: nessun lock esplicito; MVCC garantisce atomicita' per riga. Edge case di modifica concorrente da utente: l'UPDATE del job semplicemente non chiude quella riga, verra' ripreso al run successivo.

---

{% include-markdown "signature-core.md" %}

---
