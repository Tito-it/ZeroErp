{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_by_name.md" %}
# ⚙️ Funzione `fn_trigger_exists_by_name`

```sql
CREATE FUNCTION fn_trigger_exists_by_name(p_rel regclass, p_trigger_name text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_by_name(p_rel regclass, p_trigger_name text)
 RETURNS boolean
 LANGUAGE sql
AS $function$
    SELECT EXISTS(
      SELECT 1 FROM pg_trigger t
      WHERE t.tgrelid = p_rel
        AND t.tgname  = p_trigger_name
        AND NOT t.tgisinternal
    );
  $function$

COMMENT ON FUNCTION dbops.fn_trigger_exists_by_name(p_rel regclass, p_trigger_name text)
IS '
  Verifica l’esistenza di un trigger **non interno** (tgisinternal = false) su una
  relazione specifica, identificandolo per **nome esatto**.

  • **Ritorno**: boolean — TRUE se esiste almeno un trigger non-internal con nome
    `p_trigger_name` sulla relazione `p_rel`, altrimenti FALSE.

  • **Parametri**
    - `p_rel regclass`: relazione di destinazione (tabella/vista) su cui cercare.
    - `p_trigger_name text`: nome del trigger da verificare (match esatto su `pg_trigger.tgname`).

  • **Note implementative**
    - Interroga `pg_trigger` filtrando `tgrelid = p_rel` e `tgname = p_trigger_name`.
    - Esclude i trigger interni (`NOT tgisinternal`).
    - È una funzione **idempotente** e a **basso costo** (utilizza `EXISTS`).

  • **Casi d’uso tipici**
    - Controlli di esistenza prima di creare/eliminare trigger in processi di automazione.
    - Strategie di “existence check” con criterio **BY_NAME**.

  • **Limitazioni**
    - Il match è sensibile al nome completo del trigger; differenze di naming policy
      (es. template diversi) richiedono l’uso di strategie alternative (es. BY_FUNCTION).
  ';
```

</div>

---
{% include-markdown "signature-core.md" %}
