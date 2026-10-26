# ⚙️ Funzione `trgfn_registri_fatturazione_guard_coppia_unica`

```sql
CREATE FUNCTION trgfn_registri_fatturazione_guard_coppia_unica()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_registri_fatturazione_guard_coppia_unica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_coppia     record;
    v_occupante  vendite.registri_fatturazione.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Spostare un registro su un altro emittente o un'altra
    --   utility sposta tutti i suoi collegamenti: nessuno di
    --   loro puo' finire accanto a un registro che copre gia'
    --   la stessa coppia.
    --
    -- Regole:
    --   - uscita sul no-op: emittente e utility invariati;
    --   - lock consultivo sul NUOVO emittente, lo stesso del
    --     guard sul collegamento.
    -- =========================================================
    IF NEW.emittente_soggetto_ruolo_id IS NOT DISTINCT FROM OLD.emittente_soggetto_ruolo_id
       AND NEW.utility_id IS NOT DISTINCT FROM OLD.utility_id THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.coppia_registro_fattura'),
        hashtext(NEW.emittente_soggetto_ruolo_id::text));

    FOR v_coppia IN
        SELECT m.tipo_doc_fiscale_id, m.natura_doc_id
          FROM vendite.tipi_doc_fiscale_registri m
         WHERE m.registro_id = NEW.id
         ORDER BY m.tipo_doc_fiscale_id, m.natura_doc_id
    LOOP
        v_occupante := vendite.fn_registro_che_copre_coppia(
            v_coppia.tipo_doc_fiscale_id, v_coppia.natura_doc_id,
            NEW.emittente_soggetto_ruolo_id, NEW.utility_id, NEW.id);

        IF v_occupante IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_registri_fatturazione_guard_coppia_unica',
                'E_REGISTRO_COPPIA_GIA_COPERTA',
                jsonb_build_object(
                    'campo', CASE
                                 WHEN NEW.utility_id IS DISTINCT FROM OLD.utility_id
                                 THEN 'utility_id'
                                 ELSE 'emittente_soggetto_ruolo_id'
                             END,
                    'tipo_doc_fiscale_id', v_coppia.tipo_doc_fiscale_id,
                    'natura_doc_id', v_coppia.natura_doc_id,
                    'registro_id', NEW.id,
                    'registro_occupante_id', v_occupante,
                    'emittente_soggetto_ruolo_id', NEW.emittente_soggetto_ruolo_id,
                    'utility_id', NEW.utility_id),
                NULL::uuid,
                (SELECT n.descrizione FROM config.nature_doc_fiscale n WHERE n.id = v_coppia.natura_doc_id),
                (SELECT t.descrizione FROM config.tipi_doc_fiscale t WHERE t.id = v_coppia.tipo_doc_fiscale_id),
                (SELECT r.codice FROM vendite.registri_fatturazione r WHERE r.id = v_occupante));
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_registri_fatturazione_guard_coppia_unica()
IS 'Guard BEFORE UPDATE OF emittente_soggetto_ruolo_id, utility_id su vendite.registri_fatturazione (2026-10-18): spostare un registro sposta tutti i suoi collegamenti (tipo documento, natura), e nessuno puo'' finire accanto a un registro dello stesso emittente e utility che copre gia'' la stessa coppia (E_REGISTRO_COPPIA_GIA_COPERTA, campo utility_id o emittente_soggetto_ruolo_id). Gemello di vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica, stessa chiave (vendite.fn_registro_che_copre_coppia), stesso lock consultivo per emittente. Uscita sul no-op. R-BE-14, D-14d di Tid, brief-db-processi-accensione-per-ambiente §6.14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
