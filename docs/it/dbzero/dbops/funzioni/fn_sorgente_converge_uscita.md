# ⚙️ Funzione `fn_sorgente_converge_uscita`

```sql
CREATE FUNCTION fn_sorgente_converge_uscita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sorgente_converge_uscita()
 RETURNS TABLE(tabella text, azione text)
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_relid   oid;
    v_schema  pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella pg_catalog.pg_class.relname%TYPE;
    v_trigger pg_catalog.pg_trigger.tgname%TYPE;
    v_nome    text;
BEGIN
    -- =========================================================
    -- Scopo: i trigger del lato «in uscita» uguali al catalogo
    --   delle sorgenti. Idempotente: a regime non fa niente.
    -- =========================================================

    -- Dove il catalogo lo chiede e manca: si monta.
    FOR v_relid, v_schema, v_tabella IN
        SELECT DISTINCT c.oid, n.nspname, c.relname
          FROM config.sorgenti s
          CROSS JOIN LATERAL (VALUES (s.target_table), (s.righe_table),
                                     (s.dettaglio_table)) x(t)
          JOIN pg_catalog.pg_class c     ON c.oid = x.t
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r', 'p')
           AND NOT EXISTS (
               SELECT 1 FROM pg_catalog.pg_trigger tg
                WHERE tg.tgrelid = c.oid
                  AND tg.tgfoid = 'script.trgfn_sorgente_in_uscita()'::regprocedure)
         ORDER BY n.nspname, c.relname
    LOOP
        v_nome := 'trg_'
            || CASE WHEN EXISTS (
                        SELECT 1 FROM pg_catalog.pg_class o
                         WHERE o.relname = v_tabella AND o.oid <> v_relid
                           AND o.relkind IN ('r', 'p'))
                    THEN v_schema || '_' ELSE '' END
            || v_tabella || '_a10_sorgente_in_uscita_dlt';

        EXECUTE format(
            'CREATE TRIGGER %I AFTER DELETE ON %I.%I '
            'REFERENCING OLD TABLE AS vecchie FOR EACH STATEMENT '
            'EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()',
            v_nome, v_schema, v_tabella);

        tabella := v_schema || '.' || v_tabella;
        azione  := 'MONTATO';
        RETURN NEXT;
    END LOOP;

    -- Dove c'e' e il catalogo non dichiara piu' la tabella: si toglie.
    FOR v_schema, v_tabella, v_trigger IN
        SELECT n.nspname, c.relname, tg.tgname
          FROM pg_catalog.pg_trigger tg
          JOIN pg_catalog.pg_class c     ON c.oid = tg.tgrelid
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE tg.tgfoid = 'script.trgfn_sorgente_in_uscita()'::regprocedure
           AND NOT EXISTS (
               SELECT 1 FROM config.sorgenti s
                WHERE tg.tgrelid IN (s.target_table, s.righe_table, s.dettaglio_table))
         ORDER BY n.nspname, c.relname
    LOOP
        EXECUTE format('DROP TRIGGER %I ON %I.%I', v_trigger, v_schema, v_tabella);

        tabella := v_schema || '.' || v_tabella;
        azione  := 'SMONTATO';
        RETURN NEXT;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_sorgente_converge_uscita()
IS 'Fa convergere al catalogo delle sorgenti i trigger del lato «in uscita» della provenienza: monta script.trgfn_sorgente_in_uscita (AFTER DELETE, per istruzione, tabella di transizione «vecchie») su ogni tabella che config.sorgenti dichiara come documento, righe o dettaglio di un tipo, e lo toglie dove il catalogo non la dichiara piu''. Nome: trg_[<schema>_]<tabella>_a10_sorgente_in_uscita_dlt, con lo schema se un''altra tabella ha lo stesso nome. Restituisce le azioni fatte; a regime nessuna. La lancia 90_end a ogni migrazione, dopo i seed. INVOKER: la lancia il proprietario delle tabelle.';
```

</div>

---
{% include-markdown "signature-core.md" %}
