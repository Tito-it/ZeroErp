{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_transizione`

```sql
CREATE FUNCTION trgfn_ddt_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato DDT.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_ddt.
--   Letto dalla matrice (no grafo hardcodato). Mirror del guard
--   ordini (trgfn_ordini_guard_transizione).
--   rev 2026-07-19: la Regola 2 (righe) delega a
--   script.fn_check_ddt_emittibile — single source con la capability.
DECLARE
    v_codice_da config.stati_doc_ddt.codice_interno%TYPE;
    v_codice_a  config.stati_doc_ddt.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_ddt_id IS NOT DISTINCT FROM OLD.stato_doc_ddt_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_ddt_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_ddt_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_ddt
     WHERE id IN (OLD.stato_doc_ddt_id, NEW.stato_doc_ddt_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_ddt t
         WHERE t.stato_da_id = OLD.stato_doc_ddt_id
           AND t.stato_a_id  = NEW.stato_doc_ddt_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_STATO_DDT_TRANSIZIONE_NON_VALIDA',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'stato_da', v_codice_da,
                'stato_a',  v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2: DRAFT->EMESSO richiede almeno una riga attiva.
    -- Zero righe = niente da trasportare. Il "DDT solo trasporto"
    -- resta possibile: e' righe senza prezzo, non zero righe.
    -- Verdetto dalla single source (fn_check_ddt_emittibile).
    IF v_codice_da = 'DRAFT' AND v_codice_a = 'EMESSO'
       AND script.fn_check_ddt_emittibile(NEW)
           @> '[{"codice": "E_DDT_EMISSIONE_SENZA_RIGHE"}]'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_DDT_EMISSIONE_SENZA_RIGHE',
            jsonb_build_object(
                'ddt_id', NEW.id,
                'numero', NEW.numero
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(NEW.numero, 'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_transizione()
IS 'Trigger function: enforcement grafo transizioni stato DDT letto da config.transizioni_stati_ddt (E_STATO_DDT_TRANSIZIONE_NON_VALIDA). Regola 2: DRAFT->EMESSO richiede almeno una riga attiva (E_DDT_EMISSIONE_SENZA_RIGHE) — verdetto delegato a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt). Mirror di trgfn_ordini_guard_transizione. rev 2026-07-19 (brief-db-guard-righe-avanzamento-stato Rev 2).';
```

---
{% include-markdown "signature-core.md" %}
