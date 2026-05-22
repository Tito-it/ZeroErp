# fn_non_editable_fields

> **Vedi anche**
>
> - [dbops.lock_columns_conditional](/dbzero/dbops/manual/lock_columns_conditional) — registro lock condizionali (condition_expr)
> - [dbops.vw_non_editable_fields](/dbzero/dbops/manual/vw_non_editable_fields) — lock statici (incondizionati)
> - [dbops.automation_lock_columns](/dbzero/dbops/manual/automation_lock_columns) — tabella sorgente dei lock statici
> - [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva) — prima applicazione: guard trigger simmetrico

## Scopo

(latest review 2026-05-22)

`dbops.fn_non_editable_fields` e' l'entry-point unificato per conoscere i campi
non editabili di una **riga specifica**: unisce i lock statici
(da `dbops.vw_non_editable_fields`) con i lock condizionali
(da `dbops.lock_columns_conditional`, valutati dinamicamente sulla riga).

Differenza rispetto alla sola vista `vw_non_editable_fields`:

| | `vw_non_editable_fields` | `fn_non_editable_fields` |
| --- | --- | --- |
| Lock statici | ✅ | ✅ |
| Lock condizionali | ❌ | ✅ |
| Richiede id riga | No | Sì (`p_record_id text`) |
| Tipo | Vista SQL | Funzione PL/pgSQL |
| Volatility | STABLE | VOLATILE |

---

## Schema DB

`dbops`

## Firma

```sql
dbops.fn_non_editable_fields(
    p_schema     text,   -- schema tabella target (es. 'catalogo')
    p_table      text,   -- nome tabella target (es. 'articoli')
    p_record_id  text    -- PK della riga come text (cast a tipo target in condition_expr)
) RETURNS text[]
```

---

## Output

Array di nomi colonna non editabili, **deduplicato e ordinato alfabeticamente**.
Restituisce `ARRAY[]::text[]` (mai NULL) se nessun lock e' attivo.

Esempi:

```sql
-- Articolo senza BoM attive: solo lock statici
SELECT dbops.fn_non_editable_fields('catalogo', 'articoli', art_id::text);
-- → '{codice}'

-- Articolo padre di BoM attiva: lock statici + condizionali
SELECT dbops.fn_non_editable_fields('catalogo', 'articoli', art_composito_id::text);
-- → '{codice,is_composito,requires_serial}'
```

---

## Algoritmo

1. **Lock statici**: `array_agg(column_name)` da `dbops.vw_non_editable_fields`
   filtrata per `(target_schema, target_table)`.
2. **Lock condizionali**: loop su `dbops.lock_columns_conditional` per
   `(schema_name, table_name, enabled IS TRUE)`. Per ogni riga:
   ```sql
   EXECUTE 'SELECT (' || condition_expr || ')' USING p_record_id INTO v_match
   ```
   Se `v_match IS TRUE`, aggiunge `column_name` al risultato.
3. **Deduplicazione + ordinamento**: `ARRAY(SELECT DISTINCT col FROM unnest(...) ORDER BY col)`.

La concatenazione diretta (`||`) invece di `format()` evita ambiguita' sul carattere `%`
in `condition_expr`. `$1` e' parametrico via `USING` — non soggetto a SQL injection.

---

## Volatility e sicurezza

**VOLATILE**: le `condition_expr` leggono stato corrente del DB (righe BoM, date,
flag `attivo`). Il risultato puo' cambiare nella stessa transazione se i dati
sottostanti cambiano. Non usare in contesti dove ci si aspetta stabilita' del piano.

**SECURITY INVOKER**: la funzione esegue le query con i permessi del chiamante.
Prerequisito: le tabelle referenziate nelle `condition_expr` devono avere
`GRANT SELECT` al ruolo applicativo (`zeroerp_app`). Con RLS attiva, vengono
viste solo le righe accessibili al chiamante — comportamento corretto.

---

## Uso BE (Python)

Il repository `LockColumnsRepository` chiama la funzione passando `record_id::text`.
La chiamata sostituisce `list_non_editable` per i detail endpoint che hanno l'id riga:

```python
# apps/core/db/lock_columns_repository.py (futuro metodo)
def list_non_editable_with_record(schema: str, table: str, record_id: str) -> tuple[str, ...]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT dbops.fn_non_editable_fields(%s, %s, %s)",
            [schema, table, record_id],
        )
        row = cursor.fetchone()
        assert row is not None
        return tuple(row[0] or [])
```

Il service usa il risultato per costruire `non_editable_fields` nel DTO/detail:

```python
# Nel service detail
non_editable = lock_repo.list_non_editable_with_record(
    'catalogo', 'articoli', str(articolo['id'])
)
articolo['non_editable_fields'] = sorted(non_editable)
```

---

## Dipendenze

| Oggetto | Tipo | Motivo |
| --- | --- | --- |
| `dbops.vw_non_editable_fields` | Vista | Lock statici (passo 1) |
| `dbops.lock_columns_conditional` | Tabella | Registro regole condizionali (passo 2) |

---

## Note operative

- **Nessun caching a DB**: la funzione e' VOLATILE, ogni chiamata esegue le query.
  Per la stessa riga in un detail endpoint (1 chiamata), il costo e' trascurabile.
  Se il numero di regole condizionali per `(schema, table)` cresce molto, valutare
  un indice su `(schema_name, table_name, enabled)`.
- **Backward compat**: `vw_non_editable_fields` resta invariata per i caller
  che non hanno bisogno dei lock condizionali (list endpoint, lookup statici).
  `fn_non_editable_fields` e' addizionale, non sostitutiva della vista.
- **Guard trigger disaccoppiato**: questa funzione segnala al FE cosa e' bloccato;
  il trigger DB rifiuta il save anche se il segnale non viene emesso.
  Sono due difese indipendenti, intenzionalmente disaccoppiate.
- Migration di riferimento: `20260522-03`.
