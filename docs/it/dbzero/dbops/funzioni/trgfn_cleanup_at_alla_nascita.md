{% include-markdown "it/dbzero/dbops/manual/trgfn_cleanup_at_alla_nascita.md" %}
# ⚙️ Funzione `trgfn_cleanup_at_alla_nascita`

```sql
CREATE FUNCTION trgfn_cleanup_at_alla_nascita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ Niente %TYPE: il trigger e' generico, non riflette
    --    una colonna di UNA tabella. cleanup_at e la base sono
    --    timestamptz per contratto del framework.
    v_regola  record;
    v_base_ts timestamptz;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere NEW.cleanup_at = <colonna base> + ttl_days
    --   ALL'INSERT, con la regola di dbops.fn_cleanup_at_regola:
    --   la stessa che il runner applica al pregresso.
    --
    -- Regole:
    --   - la tabella senza cleanup_at → la riga passa intatta;
    --   - nessuna regola, o una regola che non si applica
    --     (tabella esclusa, colonna base assente) → cleanup_at
    --     NULL: la riga non scade;
    --   - la colonna base NULL sulla riga → cleanup_at NULL: la
    --     scadenza la scrive il job quando la base c'e', come sul
    --     pregresso;
    --   - SOVRASCRIVE cio' che passa il chiamante: un diario
    --     non lascia scegliere quando scade. Per produrre una
    --     riga gia' scaduta (pgTAP) si retrodata la colonna base.
    --
    -- ⭐ Perche' alla nascita e non con l'UPDATE del job: su un
    --   registro l'UPDATE notturno riscriverebbe data_update e
    --   user_update di ogni riga fresca e passerebbe dai trigger
    --   di UPDATE. Il job resta per il pregresso (righe a NULL).
    -- =========================================================
    SELECT r.ttl_days, r.base_ts_column, r.motivo_salto
      INTO v_regola
      FROM dbops.fn_cleanup_at_regola(TG_TABLE_SCHEMA::text, TG_TABLE_NAME::text) r;

    IF FOUND AND v_regola.motivo_salto = 'NO_CLEANUP_COLUMN' THEN
        RETURN NEW;
    END IF;

    IF NOT FOUND OR v_regola.motivo_salto IS NOT NULL THEN
        -- Senza regola che si applica: la riga non scade. Se la tabella
        -- non avesse cleanup_at, l'assegnazione fallirebbe: senza regola
        -- non lo sappiamo, quindi si guarda.
        IF dbops.fn_col_exists(TG_TABLE_SCHEMA::text, TG_TABLE_NAME::text, 'cleanup_at') THEN
            NEW.cleanup_at := NULL;
        END IF;
        RETURN NEW;
    END IF;

    -- La colonna base si legge dalla riga in arrivo per nome:
    -- la stessa che dbops.fn_apply_cleanup_at usera' sul pregresso.
    EXECUTE format('SELECT ($1).%I::timestamptz', v_regola.base_ts_column)
       INTO v_base_ts
      USING NEW;

    NEW.cleanup_at := v_base_ts + make_interval(days => v_regola.ttl_days);

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION dbops.trgfn_cleanup_at_alla_nascita()
IS 'BEFORE INSERT generico: scrive NEW.cleanup_at = colonna base + ttl_days con la regola di dbops.fn_cleanup_at_regola, la stessa che dbops.fn_run_automations_cleanup applica al pregresso. Nessuna regola, o una regola che non si applica (tabella esclusa, colonna base assente) -> cleanup_at NULL, la riga non scade; colonna base NULL sulla riga -> NULL, la scadenza la scrive il job quando la base c''e''. Una tabella senza cleanup_at passa intatta. Alla nascita e non con l''UPDATE del job perche'' su un registro quell''UPDATE riscriverebbe data_update/user_update e passerebbe dai trigger di UPDATE; il job resta per il pregresso. ⚠️ Sovrascrive cio'' che passa il chiamante: un diario non lascia scegliere quando scade. Fase m50: dopo gli a10 che riscrivono l''orario. Si monta a mano (trg_<tabella>_m50_cleanup_at_ins) sui registri che non ammettono l''UPDATE del job.';
```

</div>

---
{% include-markdown "signature-core.md" %}
