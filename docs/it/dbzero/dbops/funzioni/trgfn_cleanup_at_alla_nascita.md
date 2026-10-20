{% include-markdown "it/dbzero/dbops/manual/trgfn_cleanup_at_alla_nascita.md" %}
# ⚙️ Funzione `trgfn_cleanup_at_alla_nascita`

```sql
CREATE FUNCTION trgfn_cleanup_at_alla_nascita()
```

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
    v_params   jsonb;
    v_ttl_days integer;
    v_base_col text;
    v_base_ts  timestamptz;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere NEW.cleanup_at = <colonna base> + ttl_days
    --   ALL'INSERT, leggendo termine e colonna base dalla
    --   regola CLEANUP_AT che copre la tabella.
    --
    -- Regole:
    --   - nessuna regola → cleanup_at resta NULL (non scade mai)
    --   - colonna base = params->>'base_ts_column'; se assente,
    --     o NULL sulla riga, la base e' now()
    --   - SOVRASCRIVE cio' che passa il chiamante: un diario
    --     non lascia scegliere quando scade. Per produrre una
    --     riga gia' scaduta (pgTAP) si retrodata la colonna base
    --
    -- ⭐ Perche' alla nascita e non con l'UPDATE del job: su un
    --   registro l'UPDATE notturno riscriverebbe data_update e
    --   user_update di ogni riga fresca e passerebbe dai trigger
    --   di UPDATE. Il job resta per il pregresso (righe a NULL).
    -- =========================================================
    v_params := dbops.fn_cleanup_at_params(TG_TABLE_SCHEMA::text, TG_TABLE_NAME::text);

    IF v_params IS NULL THEN
        RETURN NEW;
    END IF;

    v_ttl_days := (v_params ->> 'ttl_days')::integer;
    IF v_ttl_days IS NULL THEN
        RETURN NEW;
    END IF;

    -- La colonna base si legge dalla riga in arrivo per nome:
    -- la stessa che dbops.fn_apply_cleanup_at usera' sul pregresso.
    v_base_col := NULLIF(btrim(v_params ->> 'base_ts_column'), '');
    IF v_base_col IS NOT NULL
       AND dbops.fn_col_exists(TG_TABLE_SCHEMA::text, TG_TABLE_NAME::text, v_base_col) THEN
        EXECUTE format('SELECT ($1).%I::timestamptz', v_base_col)
           INTO v_base_ts
          USING NEW;
    END IF;

    NEW.cleanup_at := COALESCE(v_base_ts, now())
                      + make_interval(days => v_ttl_days);

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION dbops.trgfn_cleanup_at_alla_nascita()
IS 'BEFORE INSERT generico: scrive NEW.cleanup_at = base_ts_column + ttl_days leggendo la regola CLEANUP_AT che copre la tabella (dbops.fn_cleanup_at_params). Nessuna regola → NULL, la riga non scade mai. ⭐ Alla nascita e non con l''UPDATE del job perche'' su un registro quell''UPDATE riscriverebbe data_update/user_update e passerebbe dai trigger di UPDATE; il job resta per il pregresso. ⚠️ Sovrascrive cio'' che passa il chiamante: un diario non lascia scegliere quando scade. Fase _m50_: dopo gli _a10_ che riscrivono l''orario. Montato su vendite.event_log e sui quattro registri di fatturazione e push. Analisi: analisi-osservabilita-log.md, Passo D.';
```

</div>

---
{% include-markdown "signature-core.md" %}
