{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_gestori_guard.md" %}
# ⚙️ Funzione `trgfn_gestori_guard`

```sql
CREATE FUNCTION trgfn_gestori_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_gestori_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_soggetto_id   uuid;
    v_partita_iva   text;
    v_existing_id   integer;
BEGIN

-- =========================================================
-- anagrafiche.trgfn_gestori_guard_ins_upd()
-- Guard di dominio per anagrafiche.gestori
--
-- Regole:
--  1) Singleton: massimo 1 record in anagrafiche.gestori
--  2) Il soggetto collegato DEVE avere partita_iva valorizzata
--
-- rev 2026-08-04 (bonifica riferimenti morti, F4):
--   la prima chiamata di log usava dbops.fn_log_and_raise_error
--   (inesistente) e mescolava un argomento con nome
--   (`p_codice_errore`, per giunta non un parametro vero: e'
--   `p_error_code`) con argomenti posizionali, che PostgreSQL
--   non ammette. Resa identica alle due sorelle sotto.
-- =========================================================

    ----------------------------------------------------------------
    -- 0) Verifica che il soggetto_ruolo esista e risali al soggetto
    ----------------------------------------------------------------
    SELECT s.id, s.partita_iva
    INTO v_soggetto_id, v_partita_iva
    FROM anagrafiche.soggetti_ruoli sr
    JOIN anagrafiche.soggetti s
    ON s.id = sr.soggetto_id
    WHERE sr.id = NEW.soggetto_ruolo_id;

    IF v_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database' ,
            TG_NAME,
            'E_GESTORE_SOGGETTO_RUOLO_MANCANTE',
            jsonb_build_object(
                    'table', TG_TABLE_NAME,
                    'soggetto_ruolo_id', NEW.soggetto_ruolo_id
                ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 1) Regola: il soggetto del gestore deve avere PARTITA IVA
    ----------------------------------------------------------------
    IF v_partita_iva IS NULL OR btrim(v_partita_iva) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database' ,
            TG_NAME,
            'E_RUOLO_RICHIEDE_PIVA',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'soggetto_id', v_soggetto_id,
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
            ),
            NULL::uuid,
            'gestore',
            v_soggetto_id::text,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 2) Regola singleton: massimo 1 record in anagrafiche.gestori
    --
    -- NB: id <> NEW.id per permettere UPDATE sulla stessa riga.
    ----------------------------------------------------------------
    SELECT g.id
    INTO v_existing_id
    FROM anagrafiche.gestori g
    WHERE g.id <> COALESCE(NEW.id, -1)
    LIMIT 1;

    IF FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database' ,
            TG_NAME,
            'E_GESTORE_SINGLETON_VIOLATO',
            jsonb_build_object
                ('table', TG_TABLE_NAME,
                'existing_gestore_id', v_existing_id,
                'new_soggetto_ruolo_id', NEW.soggetto_ruolo_id
                ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_gestori_guard()
IS 'Guard di dominio per anagrafiche.gestori.';
```

</div>

---
{% include-markdown "signature-core.md" %}
