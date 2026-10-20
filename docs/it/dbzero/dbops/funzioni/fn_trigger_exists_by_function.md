{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_by_function.md" %}
# ⚙️ Funzione `fn_trigger_exists_by_function`

```sql
CREATE FUNCTION fn_trigger_exists_by_function(p_rel regclass, p_fn_schema text, p_fn_name text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_by_function(p_rel regclass, p_fn_schema text, p_fn_name text)
 RETURNS boolean
 LANGUAGE sql
AS $function$
    SELECT EXISTS(
      SELECT 1
        FROM pg_trigger t
        JOIN pg_proc p ON p.oid = t.tgfoid
        JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE t.tgrelid = p_rel
        AND n.nspname = p_fn_schema
        AND p.proname = p_fn_name
        AND NOT t.tgisinternal
    );
  $function$

COMMENT ON FUNCTION dbops.fn_trigger_exists_by_function(p_rel regclass, p_fn_schema text, p_fn_name text)
IS '
      Verifica esistenza di un trigger **non interno** (tgisinternal = false) su una
      relazione specifica, identificandolo per **funzione associata** (`pg_trigger.tgfoid`)
      tramite schema e nome della funzione.

      **Ritorno**: boolean — TRUE se esiste almeno un trigger non-internal sulla relazione
        `p_rel` che invoca la funzione `p_fn_schema.p_fn_name`, altrimenti FALSE.

      **Parametri**
        - `p_rel regclass`: relazione di destinazione (tabella/vista) su cui cercare.
        - `p_fn_schema text`: schema della funzione di trigger da verificare.
        - `p_fn_name text`: nome della funzione di trigger da verificare.

      **Note implementative**
        - Join su `pg_trigger` → `pg_proc` (tgfoid) → `pg_namespace` (pronamespace).
        - Esclude i trigger interni (`NOT tgisinternal`).
        - Restituisce TRUE anche se sono presenti **più** trigger che puntano alla stessa funzione.

      **Casi d’uso tipici**
        - Strategie di “existence check” con criterio **BY_FUNCTION** o **BOTH**,
          indipendenti dal naming effettivo del trigger.
        - Ambienti con naming template differenti ma logica di trigger consolidata su un’unica funzione.

      **Limitazioni**
        - Non disambigua funzioni omonime tra schemi diversi (lo schema viene richiesto apposta).
        - Non verifica la **firma** della funzione; controlla solo schema+nome.
';
```

</div>

---
{% include-markdown "signature-core.md" %}
