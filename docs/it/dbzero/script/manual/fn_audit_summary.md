# fn_audit_summary

### Scopo

Calcola **al volo** il diff fra uno snapshot storico e il suo
precedente (stessa riga originale, ordinato per `valid_from`)
(Fase 5 P1 2026-04-29). Sostituisce la funzione FE locale
`snapshotSummary` nel drawer admin
([`AuditLogView.vue:95-107`](/dev/work-in-progress/analisi-refactor.frontend-amm-software))
spostando il calcolo dal client al DB.

**Read-side**, lazy: nessuna modifica al framework di storicizzazione,
nessun trigger nuovo, nessuna colonna aggiuntiva sulle storico.

> **Vedi anche**
>
> - [Guida Audit e Tracciabilità](/guide/audit-e-tracciabilita)
> - [vw_audit_sources](/dbzero/script/manual/vw_audit_sources) — vista che lista i `code` ammessi
> - [audit_sources](/dbzero/dbops/manual/audit_sources) — tabella metadata (storico_table / storico_pk_col)
> - [trgfn_storico_generic](/dbzero/script/manual/trgfn_storico_generic) — il trigger che popola gli snapshot

## Schema

`script` (cross-dominio: legge `dbops.audit_sources` + `storico.*` dinamicamente).

## Firma

```sql
script.fn_audit_summary(
    p_audit_source_code text,
    p_storico_id        bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_audit_source_code` | `text` | Sì | Codice della audit_source (es. `'user_override_aree'`). Deve esistere e essere `attivo` in `dbops.audit_sources`, altrimenti `E_AUDIT_SOURCE_NON_TROVATO` (407). |
| `p_storico_id` | `bigint` | Sì, `> 0` | ID dello snapshot nella `storico.<tabella>` dispatchata. **Non** è l'id della riga originale, è l'id PK dello snapshot. |

## Output

`jsonb` a 2 chiavi (contratto API):

```jsonc
{
    "summary": "3 modifiche",
    "diff": [
        {"field": "attivo",     "old": true,    "new": false},
        {"field": "livello",    "old": "TUTTO", "new": "BLOCCATO"},
        {"field": "valido_al",  "old": null,    "new": "2026-12-31"}
    ]
}
```

| Chiave | Tipo | Significato |
|---|---|---|
| `summary` | `text` | Frase neutra `'<N> modifiche'`. Il FE/BE compone l'eventuale frase localizzata, il DB non traduce. |
| `diff` | `jsonb[]` | Array di `{field, old, new}` ordinato alfabeticamente per `field`. Solo le coppie effettivamente cambiate (NULL-safe). |

### Esclusioni dal `diff`

Per ridurre il rumore, sono **sempre escluse** dal diff le 5 colonne audit standard:

- `data_insert`, `data_update`
- `user_insert`, `user_update`
- `tx_id`

Sono cambiamenti tracciati a parte dalle colonne stesse della storico
(`valid_from`, `user_insert` snapshot-level).

## Algoritmo

1. **Guard parametri** (errori 406-407 via `script.fn_log_and_raise_error`):
   - `p_audit_source_code` NULL o blank → `E_AUDIT_SUMMARY_PARAM_NON_VALIDO`
   - `p_storico_id` NULL o `<= 0` → `E_AUDIT_SUMMARY_PARAM_NON_VALIDO`
2. **Lookup** `dbops.audit_sources` per `code` AND `attivo=true` →
   recupera `storico_table` (`schema.tabella`) e `storico_pk_col`
   (nome della colonna riferimento riga originale). Non trovato →
   `E_AUDIT_SOURCE_NON_TROVATO`.
3. **Dispatch dinamico** (SQL `EXECUTE format` con `%I` sanitizer):
    ```sql
    WITH target AS (
        SELECT <pk_col> AS row_id
          FROM <schema>.<table>
         WHERE id = $1
    ),
    ranked AS (
        SELECT s.id, s.snapshot,
               LAG(s.snapshot) OVER (ORDER BY s.valid_from, s.id) AS prev
          FROM <schema>.<table> s
          JOIN target t ON s.<pk_col> = t.row_id
    )
    SELECT snapshot, prev FROM ranked WHERE id = $1
    ```
   Trova lo snapshot indirizzato + lo snapshot precedente sulla stessa
   riga originale (LAG partition implicita perché filtriamo via
   `JOIN target`).
4. Snapshot non trovato → `E_AUDIT_SNAPSHOT_NON_TROVATO`.
5. **Calcolo diff**: itera sull'**UNION** dei keys di `snapshot` e
   `prev`. Filtro NOT IN audit cols, filtro
   `prev IS NULL OR prev->k IS DISTINCT FROM snapshot->k` (NULL-safe).
   L'UNION garantisce la copertura di tutti e 3 gli scenari di
   schema-change tra snapshot:
   - **field aggiunto**: chiave solo in `snapshot` → `{old:null, new:val}`
   - **field rimosso**: chiave solo in `prev` → `{old:val, new:null}`
   - **field modificato**: chiave in entrambi, valori diversi → `{old:v1, new:v2}`
6. **Compose summary**: `format('%s modifiche', jsonb_array_length(v_diff))`.

## Casi del diff

| Tipo evento (snapshot) | `prev` | `diff` calcolato |
|---|---|---|
| Primo snapshot per la riga (`tipo_operazione=1` INIZIALE) | `NULL` | Tutti i campi non-audit (`old=null, new=valore`). |
| UPDATE / DELETE successivi (`tipo_op=2/3`) | snapshot precedente | Solo i campi cambiati rispetto al precedente. |
| UPDATE che non cambia nulla di rilevante (es. solo `data_update`) | snapshot precedente | `[]` (zero modifiche, summary=`"0 modifiche"`). |

## Codici errore

| Codice | id | Quando | HTTP suggerito |
|---|---|---|---|
| `E_AUDIT_SUMMARY_PARAM_NON_VALIDO` | 406 | `p_audit_source_code` blank/NULL o `p_storico_id` ≤ 0 / NULL | 400 (programmazione BE) |
| `E_AUDIT_SOURCE_NON_TROVATO` | 407 | Code non in `dbops.audit_sources` o non attivo | 400 |
| `E_AUDIT_SNAPSHOT_NON_TROVATO` | 408 | `storico_id` non esiste nella `storico.<tabella>` dispatchata | 404 |

Tutti gli errori passano per `script.fn_log_and_raise_error` →
audit log + i18n + codice stabile per il mapping `error_policies.py`.

## Caratteristiche

- `LANGUAGE plpgsql STABLE` — read-only, nessuna scrittura.
- `EXECUTE format(%I, ...)` sanifica gli identificatori (zero rischio
  SQL injection anche se i metadata fossero compromessi).
- Read-rate ≪ write-rate (il drawer è consultato raramente): compute
  on-read è la scelta architetturale corretta vs trigger-time.
  **Nessuna colonna aggiuntiva** sulle 80+ tabelle storico.
- `LAG()` è O(N) sulla storia di una singola riga — tipicamente
  poche revisioni, query veloce.

## Tipi parametri / return

| Posizione | Tipo | Note |
|---|---|---|
| `p_audit_source_code` | `text` | Esplicito, non `audit_sources.code%TYPE` per evitare dipendenza al CREATE FUNCTION (la fn potrebbe servire test in cui audit_sources non esiste ancora). |
| `p_storico_id` | `bigint` | Esplicito. Tutte le storico hanno `id` = bigserial; `bigint` copre anche le `serial` (integer è subset di bigint). |
| Variabili interne | `dbops.audit_sources.<col>%TYPE` | `%TYPE` su colonne non-django, coerente con la regola del progetto. |

## Performance e indici

- Le storico tabelle hanno **indice automatico** su `<table>_id` (creato
  dal framework storicizzazione, vedi
  [proc_automations_storico_provision_job](/dbzero/maintenance/manual/proc_automations_storico_provision_job)).
- Le query del LAG filtrano su `<pk_col>` indicizzato e ordinano per
  `valid_from`. Per dataset grandi conviene aggiungere un indice
  composito `(<pk_col>, valid_from)` — non urgente per il volume
  attuale (configurazione/identità).

## Dipendenze

### Tabelle

- `dbops.audit_sources` (lookup metadata)
- `storico.*` (dispatchata dinamicamente)

### Funzioni

- `script.fn_log_and_raise_error(...)` — raise standardizzato

## Chi la chiama

- BE (Fase 5): `ApiAuditLogList` aggiunge un campo `summary` (e
  opzionalmente `diff`) alla risposta della list, calcolato chiamando
  `fn_audit_summary` per ogni riga.
- Test pgTAP: `db/pgtap/script/test-fn-audit-summary.sql`.

## Riferimenti

- Migration: `db/changelog/migrations_v2/20_code/script/20260429-07-create-fn-audit-summary-mctit.yaml`
- Codici errore: aggiunti id 406-408 in `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`
- Brief Fase 5: `docs/it/dev/work-in-progress/analisi-refactor.frontend-amm-software.md`

## Esempio

```sql
-- Smoke test: prendi un id storico esistente e ottieni il summary.
SELECT script.fn_audit_summary(
    'user_override_aree',
    (SELECT min(id) FROM storico.user_override_aree)
);
-- {"summary":"2 modifiche","diff":[{"field":"attivo","old":true,"new":false},{"field":"livello_accesso","old":"TUTTO","new":"BLOCCATO"}]}

-- Source non valida -> raise E_AUDIT_SOURCE_NON_TROVATO
SELECT script.fn_audit_summary('inesistente', 1);
-- ERROR: fn_audit_summary: audit_source_code 'inesistente' non trovato in dbops.audit_sources (o non attivo).

-- Param invalido -> raise E_AUDIT_SUMMARY_PARAM_NON_VALIDO
SELECT script.fn_audit_summary(NULL, 1);
-- ERROR: fn_audit_summary parametro p_audit_source_code non valido: NULL.
```

## Note di evoluzione

- **In v1**: il `diff` espone i `field` come snake_case raw (nome
  colonna). Il FE compone il display via i18n catalog. Una mappatura
  `(table, field) → label_key` field-level è stata **deliberatamente
  esclusa** in v1: aggiunge una seconda lookup (~50 entry) per un
  beneficio limitato. Riapribile in v2 se il drawer richiede
  traduzioni precise per ogni campo.
- **`tipo_operazione`** (1=INIZIALE, 2=MODIFICA, 3=ELIMINAZIONE)
  resta decodificato dal BE. Spostarlo in DB richiederebbe un altro
  lookup (`config.tipi_operazione_storico`?) — fuori scope Fase 5.
