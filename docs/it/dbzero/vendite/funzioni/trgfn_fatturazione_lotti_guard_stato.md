{% include-markdown "it/dbzero/vendite/manual/trgfn_fatturazione_lotti_guard_stato.md" %}
# ⚙️ Funzione `trgfn_fatturazione_lotti_guard_stato`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_guard_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: il cambio di stato del lotto (BEFORE UPDATE OF
--   stato_doc_fiscale_id).
--   1. Lo stato d'arrivo si applica al lotto
--      (config.stati_doc_fiscale.applica_lotto), sulla
--      DESTINAZIONE; la nascita la copre il CHECK
--      chk_stati_doc_fiscale_iniziale_applica.
--   2. Il passaggio e' una riga ammessa della matrice con
--      solo_fattura = false e, se la riga lo dichiara, il
--      tipo_lotto.
--   3. Un lotto fermo non entra in uno stato congelato e non
--      abortito: il verdetto dalla sede unica.
-- =========================================================
DECLARE
    v_ok BOOLEAN;  -- esito di EXISTS sulla matrice
    v_applica   config.stati_doc_fiscale.applica_lotto%TYPE;
    v_bypass TEXT;
    v_tipo_lotto TEXT;
    v_congela   config.stati_doc_fiscale.congela_fiscale%TYPE;
    v_abortito  config.stati_doc_fiscale.is_abortito%TYPE;
    v_fermo     boolean;  -- verdetto della sede unica
    v_motivo    text;     -- motivo del fermo, dalla sede unica
BEGIN
    -- Bypass per reset tecnico
    v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1', 'true', 'on', 'yes') THEN
        RETURN NEW;
    END IF;
    IF NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id THEN
        -- 1. La destinazione si applica al lotto.
        SELECT s.applica_lotto INTO v_applica
          FROM config.stati_doc_fiscale s
         WHERE s.id = NEW.stato_doc_fiscale_id;
        IF v_applica IS NOT TRUE THEN
            PERFORM script.fn_log_and_raise_error('database', 'vendite.trgfn_fatturazione_lotti_guard_stato', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'stato_doc_fiscale_id', 'atteso', 'applica_lotto=true', 'ricevuto', NEW.stato_doc_fiscale_id),
                NULL::uuid, 'stato non applicabile a lotto', NEW.stato_doc_fiscale_id::text);
        END IF;

        -- 2. Il passaggio e' ammesso e non solo_fattura.
        SELECT EXISTS (
            SELECT 1 FROM config.stati_doc_fiscale_transizioni t
             WHERE t.ammesso AND t.stato_from_id = OLD.stato_doc_fiscale_id AND t.stato_to_id = NEW.stato_doc_fiscale_id
               AND t.solo_fattura = FALSE
               AND ((t.meta->>'tipo_lotto') IS NULL OR (t.meta->>'tipo_lotto') = NEW.tipo_lotto)
        ) INTO v_ok;
        IF NOT v_ok THEN
            v_tipo_lotto := COALESCE(NEW.tipo_lotto, '');
            PERFORM script.fn_log_and_raise_error('database', 'vendite.trgfn_fatturazione_lotti_guard_stato', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'transizione_stato', 'atteso', concat(OLD.stato_doc_fiscale_id, '→ammessa'), 'ricevuto', NEW.stato_doc_fiscale_id, 'tipo_lotto', v_tipo_lotto),
                NULL::uuid, concat('transizione ', OLD.stato_doc_fiscale_id, '→', NEW.stato_doc_fiscale_id), v_tipo_lotto);
        END IF;

        -- 3. Un lotto fermo non diventa definitivo. Stato congelato
        -- e non abortito, dal vocabolario; il verdetto dalla sede unica
        -- (legge le righe figlie, non questa colonna: in BEFORE ROW va
        -- bene).
        SELECT COALESCE(s.congela_fiscale, FALSE), COALESCE(s.is_abortito, FALSE)
          INTO v_congela, v_abortito
          FROM config.stati_doc_fiscale s
         WHERE s.id = NEW.stato_doc_fiscale_id;
        IF v_congela IS TRUE AND v_abortito IS FALSE THEN
            SELECT s.fermo, s.fermo_motivo
              INTO v_fermo, v_motivo
              FROM vendite.vw_lotti_segnalazioni_summary s
             WHERE s.lotto_id = NEW.id;
            IF v_fermo IS TRUE THEN
                PERFORM script.fn_log_and_raise_error('database', 'vendite.trgfn_fatturazione_lotti_guard_stato', 'E_PIPELINE_LOTTO_CRITICAL',
                    jsonb_build_object('lotto_id', NEW.id, 'codice', NEW.codice,
                                       'stato_da', OLD.stato_doc_fiscale_id, 'stato_a', NEW.stato_doc_fiscale_id,
                                       'fermo_motivo', v_motivo),
                    NULL::uuid, VARIADIC ARRAY[]::text[]);
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato()
IS 'Guard (BEFORE UPDATE OF stato_doc_fiscale_id) del cambio di stato del lotto di fatturazione. Lo stato d''arrivo deve applicarsi al lotto (config.stati_doc_fiscale.applica_lotto): la regola sta sulla destinazione; la nascita la copre il CHECK chk_stati_doc_fiscale_iniziale_applica. Il passaggio deve essere una riga ammessa di config.stati_doc_fiscale_transizioni con solo_fattura = false e, se la riga lo dichiara in meta, lo stesso tipo_lotto. Errore dei due controlli: E_LOTTO_PARAMETRO_NON_COERENTE (parametro stato_doc_fiscale_id o transizione_stato). Un lotto fermo (vendite.vw_lotti_segnalazioni_summary.fermo: segnalazioni critiche, fatture o documenti in errore) non entra in uno stato congelato e non abortito (congela_fiscale, is_abortito): E_PIPELINE_LOTTO_CRITICAL, lo stesso codice del runner; l''annullo resta ammesso. Bypass per il reset tecnico: GUC zeroerp.maintenance_reset_lotto_draft.';
```

</div>

---
{% include-markdown "signature-core.md" %}
