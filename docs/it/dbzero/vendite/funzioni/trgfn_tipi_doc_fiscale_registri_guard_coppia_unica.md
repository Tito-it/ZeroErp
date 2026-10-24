# ⚙️ Funzione `trgfn_tipi_doc_fiscale_registri_guard_coppia_unica`

```sql
CREATE FUNCTION trgfn_tipi_doc_fiscale_registri_guard_coppia_unica()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_emittente  vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_utility    vendite.registri_fatturazione.utility_id%TYPE;
    v_occupante  vendite.registri_fatturazione.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un collegamento (tipo, natura) → registro non puo'
    --   affiancare un altro registro dello stesso emittente e
    --   della stessa utility sulla stessa coppia.
    --
    -- Regole:
    --   - uscita sul no-op: un UPDATE che non cambia tipo,
    --     natura ne' registro non e' un collegamento nuovo;
    --   - lock consultivo per emittente, lo stesso del guard
    --     sul registro, prima di guardare.
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND NEW.tipo_doc_fiscale_id = OLD.tipo_doc_fiscale_id
       AND NEW.natura_doc_id       = OLD.natura_doc_id
       AND NEW.registro_id         = OLD.registro_id THEN
        RETURN NEW;
    END IF;

    SELECT r.emittente_soggetto_ruolo_id, r.utility_id
      INTO v_emittente, v_utility
      FROM vendite.registri_fatturazione r
     WHERE r.id = NEW.registro_id;

    -- Registro inesistente: lo ferma la FK, non questo guard.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.coppia_registro_fattura'),
        hashtext(v_emittente::text));

    v_occupante := vendite.fn_registro_che_copre_coppia(
        NEW.tipo_doc_fiscale_id, NEW.natura_doc_id,
        v_emittente, v_utility, NEW.registro_id);

    IF v_occupante IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica',
            'E_REGISTRO_COPPIA_GIA_COPERTA',
            jsonb_build_object(
                'campo', 'registro_id',
                'tipo_doc_fiscale_id', NEW.tipo_doc_fiscale_id,
                'natura_doc_id', NEW.natura_doc_id,
                'registro_id', NEW.registro_id,
                'registro_occupante_id', v_occupante,
                'emittente_soggetto_ruolo_id', v_emittente,
                'utility_id', v_utility),
            NULL::uuid,
            (SELECT n.descrizione FROM config.nature_doc_fiscale n WHERE n.id = NEW.natura_doc_id),
            (SELECT t.descrizione FROM config.tipi_doc_fiscale t WHERE t.id = NEW.tipo_doc_fiscale_id),
            (SELECT r.codice FROM vendite.registri_fatturazione r WHERE r.id = v_occupante));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica()
IS 'Guard BEFORE INSERT OR UPDATE OF tipo_doc_fiscale_id, natura_doc_id, registro_id su vendite.tipi_doc_fiscale_registri (2026-10-18): rifiuta un collegamento che affianca, sulla stessa coppia (tipo documento, natura), un altro registro dello stesso emittente e della stessa utility (E_REGISTRO_COPPIA_GIA_COPERTA, campo registro_id). Senza, vendite.fn_lookup_registro_id sceglieva il primo per id. Il gemello sul registro e'' vendite.trgfn_registri_fatturazione_guard_coppia_unica; la chiave la dice vendite.fn_registro_che_copre_coppia. Lock consultivo per emittente (namespace vendite.coppia_registro_fattura) prima di guardare. Uscita sul no-op. R-BE-14, D-14d di Tid, brief-db-processi-accensione-per-ambiente §6.14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
