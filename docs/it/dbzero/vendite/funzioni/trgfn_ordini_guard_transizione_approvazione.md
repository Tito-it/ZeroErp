# ⚙️ Funzione `trgfn_ordini_guard_transizione_approvazione`

```sql
CREATE FUNCTION trgfn_ordini_guard_transizione_approvazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_guard_transizione_approvazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca la transizione a CONFERMATO di un ordine con
--   componenti BoM CASO A in workflow approvazione prezzo (PENDING)
--   oppure con prezzo_unitario IS NULL (pending valorizzazione).
DECLARE
    v_stato_codice config.stati_doc_ordini.codice_interno%TYPE;
BEGIN
    SELECT sdo.codice_interno INTO v_stato_codice
      FROM config.stati_doc_ordini sdo
     WHERE sdo.id = NEW.stato_doc_ordine_id;

    IF v_stato_codice IS DISTINCT FROM 'CONFERMATO' THEN
        RETURN NEW;
    END IF;

    -- Check 1: componenti BoM CASO A con prezzo PENDING approvazione
    IF EXISTS (
        SELECT 1 FROM vendite.ordini_righe or_
          JOIN vendite.ordini_righe_componenti orc
            ON orc.riga_ordine_id = or_.id
         WHERE or_.ordine_id = NEW.id
           AND orc.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_COMPONENTE_PREZZO_PENDENTE',
            jsonb_build_object('ordine_id', NEW.id,
                'hint', 'Componente BoM CASO A in attesa di approvazione prezzo. '
                     || 'Attendi esito su tutti i componenti prima di confermare.'),
            NULL::uuid, NEW.id::text
        );
    END IF;

    -- Check 2: componenti BoM CASO A con prezzo NULL (pending valorizzazione)
    IF EXISTS (
        SELECT 1 FROM vendite.ordini_righe or_
          JOIN vendite.ordini_righe_componenti orc
            ON orc.riga_ordine_id = or_.id
         WHERE or_.ordine_id = NEW.id
           AND orc.attivo = TRUE
           AND orc.prezzo_unitario IS NULL
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE',
            jsonb_build_object('ordine_id', NEW.id,
                'hint', 'Uno o piu'' componenti BoM CASO A hanno prezzo non valorizzato. '
                     || 'Valorizzare tutti i prezzi prima di confermare.'),
            NULL::uuid, NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_guard_transizione_approvazione()
IS 'Trigger function: blocca transizione ordine a CONFERMATO se componenti BoM CASO A hanno stato PENDING approvazione (E_COMPONENTE_PREZZO_PENDENTE) o prezzo NULL (E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE).';
```

---
{% include-markdown "signature-core.md" %}
