{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_quantita_immutabile.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_quantita_immutabile`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_quantita_immutabile()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_bypass text;
    v_qta_ca vendite.commesse_attivita.quantita%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La quantita dell'AF DEVE specchiare la commessa madre. Si
    --   blocca solo l'UPDATE che disallinea l'AF dalla CA (valore
    --   diverso). L'emit (upsert AF.quantita = ca.quantita) passa per
    --   costruzione; un UPDATE manuale a valore diverso e' bloccato.
    --   Brief immutabilita-quantita §4a (mirror-enforcement, 2026-07-21).
    -- Regole:
    --   - bypass tecnico via GUC zeroerp.maintenance_reset_lotto_draft;
    --   - se commessa_attivita_id IS NULL non c'e' specchio da imporre.
    -- =========================================================
    v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1','true','on','yes') THEN
        RETURN NEW;
    END IF;

    IF NEW.commessa_attivita_id IS NOT NULL
       AND NEW.quantita IS DISTINCT FROM OLD.quantita THEN

        SELECT ca.quantita INTO v_qta_ca
          FROM vendite.commesse_attivita ca
         WHERE ca.id = NEW.commessa_attivita_id;

        IF NEW.quantita IS DISTINCT FROM v_qta_ca THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE',
                jsonb_build_object(
                    'id', OLD.id,
                    'commessa_attivita_id', NEW.commessa_attivita_id,
                    'quantita_new', NEW.quantita,
                    'quantita_commessa', v_qta_ca),
                NULL::uuid, OLD.id::text, v_qta_ca::text
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile()
IS 'Guard mirror-enforcement quantita attivita_fatturabili: blocca UPDATE che porterebbe la quantita a un valore diverso dalla commessa madre (commessa_attivita_id). L''emit (upsert = specchio) passa; bypass via GUC zeroerp.maintenance_reset_lotto_draft. Errore E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE. Brief immutabilita-quantita §4a (2026-07-21).';
```

</div>

---
{% include-markdown "signature-core.md" %}
