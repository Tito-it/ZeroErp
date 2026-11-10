{% include-markdown "it/dbzero/dbops/manual/trgfn_installazione_guard_immutabile.md" %}
# ⚙️ Funzione `trgfn_installazione_guard_immutabile`

```sql
CREATE FUNCTION trgfn_installazione_guard_immutabile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_installazione_guard_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'ambiente dell'installazione si scrive una volta,
    --   alla nascita, e non cambia piu' (decisione di Tid del
    --   2026-10-16). Rifiuta UPDATE, DELETE e TRUNCATE.
    --
    -- Regole:
    --   - anche un UPDATE allo stesso valore e' rifiutato: la
    --     riga non si riscrive;
    --   - nel TRUNCATE (trigger di istruzione) OLD non c'e':
    --     il valore si legge dalla tabella.
    -- =========================================================
    IF TG_LEVEL = 'ROW' THEN
        v_ambiente := OLD.ambiente;
    ELSE
        SELECT i.ambiente
          INTO v_ambiente
          FROM dbops.installazione i
         WHERE i.id = 1;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'dbops', 'trgfn_installazione_guard_immutabile', 'E_AMBIENTE_IMMUTABILE',
        jsonb_build_object('operazione', TG_OP,
                           'ambiente',   v_ambiente),
        NULL::uuid,
        COALESCE(v_ambiente, '-'));

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_installazione_guard_immutabile()
IS 'Guard su dbops.installazione: rifiuta UPDATE e DELETE (trigger di riga) e TRUNCATE (trigger di istruzione) con E_AMBIENTE_IMMUTABILE. L''ambiente si scrive una volta, alla nascita, dalla fase post del provisioning, e non cambia in nessuna delle due direzioni: un database di sviluppo non si certifica pulito, una copia della produzione resta produzione. Anche un UPDATE allo stesso valore e'' rifiutato. Il proprietario puo'' disattivare il trigger: la difesa contro un DBA malevolo sono i ruoli, non un guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
