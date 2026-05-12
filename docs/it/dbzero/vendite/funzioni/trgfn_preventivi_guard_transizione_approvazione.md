{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_guard_transizione_approvazione.md" %}
# ⚙️ Funzione `trgfn_preventivi_guard_transizione_approvazione`

```sql
CREATE FUNCTION trgfn_preventivi_guard_transizione_approvazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_transizione_approvazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca la transizione a ACCETTATO di un preventivo con
--   righe o componenti BoM CASO A ancora in workflow approvazione
--   prezzo (stato_approvazione_prezzo=PENDING).
DECLARE
    v_stato_codice config.stati_doc_preventivi.codice_interno%TYPE;
BEGIN
    SELECT sdp.codice_interno INTO v_stato_codice
      FROM config.stati_doc_preventivi sdp
     WHERE sdp.id = NEW.stato_doc_preventivo_id;

    IF v_stato_codice IS DISTINCT FROM 'ACCETTATO' THEN
        RETURN NEW;
    END IF;

    -- Check 1: righe preventivo con prezzo PENDING approvazione
    IF EXISTS (
        SELECT 1 FROM vendite.preventivi_righe pr
         WHERE pr.preventivo_id = NEW.id
           AND pr.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_PREVENTIVO_RIGHE_PRICING_PENDENTI',
            jsonb_build_object('preventivo_id', NEW.id,
                'hint', 'Riga preventivo in attesa di approvazione prezzo. '
                     || 'Attendi esito o rifiuta la richiesta prima di accettare.'),
            NULL::uuid, NEW.id::text
        );
    END IF;

    -- Check 2: componenti BoM CASO A con prezzo PENDING approvazione
    IF EXISTS (
        SELECT 1 FROM vendite.preventivi_righe pr
          JOIN vendite.preventivi_righe_componenti prc
            ON prc.riga_preventivo_id = pr.id
         WHERE pr.preventivo_id = NEW.id
           AND prc.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_PREVENTIVO_RIGHE_PRICING_PENDENTI',
            jsonb_build_object('preventivo_id', NEW.id,
                'hint', 'Componente BoM CASO A in attesa di approvazione prezzo. '
                     || 'Attendi esito su tutti i componenti prima di accettare.'),
            NULL::uuid, NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_guard_transizione_approvazione()
IS 'Trigger function: blocca transizione preventivo ad ACCETTATO se righe/componenti in stato PENDING approvazione (E_PREVENTIVO_RIGHE_PRICING_PENDENTI). Check 3 prezzo NULL rimosso (form atomic 12-05-2026).';
```

---
{% include-markdown "signature-core.md" %}
