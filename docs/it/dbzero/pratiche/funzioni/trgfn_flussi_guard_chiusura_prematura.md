{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_chiusura_prematura.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_chiusura_prematura`

```sql
CREATE FUNCTION trgfn_flussi_guard_chiusura_prematura()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_chiusura_prematura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il flusso "di chiusura" (template.chiude_pratica) chiude la
--   pratica: non puo' essere completato finche' restano ALTRI
--   obbligatori bloccanti. Coerente col guard di chiusura della
--   pratica; evita che l'auto-chiusura conseguente fallisca.
-- Regole:
--   1. Scatta solo alla transizione di stato verso COMPLETATO.
--   2. Solo se il template del flusso e' chiude_pratica.
--   3. fn_check_pratica_chiudibile escludendo il template di chiusura
--      stesso (non ancora COMPLETATO): se false -> errore parlante.
DECLARE
    v_completato_id config.stati_flussi_pratiche.id%TYPE;
    v_e_chiusura    boolean;
BEGIN
    -- (1) Solo verso COMPLETATO, e solo a stato realmente cambiato.
    SELECT id INTO v_completato_id
      FROM config.stati_flussi_pratiche
     WHERE codice_interno = 'COMPLETATO';

    IF NEW.stato_id IS DISTINCT FROM v_completato_id
       OR OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;
    END IF;

    -- (2) Solo flussi da template "di chiusura".
    IF NEW.template_flusso_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT tf.chiude_pratica INTO v_e_chiusura
      FROM pratiche.template_flussi tf
     WHERE tf.id = NEW.template_flusso_id;

    IF NOT COALESCE(v_e_chiusura, false) THEN
        RETURN NEW;
    END IF;

    -- (3) Ammesso solo se nessun ALTRO obbligatorio e' bloccante.
    IF NOT pratiche.fn_check_pratica_chiudibile(NEW.pratica_id, NEW.template_flusso_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_flussi_guard_chiusura_prematura',
            'PRATICHE_CHIUSURA_FLUSSO_PREMATURO',
            jsonb_build_object(
                'pratica_id', NEW.pratica_id,
                'flusso_id', NEW.id,
                'template_flusso_id', NEW.template_flusso_id
            ),
            NEW.tx_id,
            NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_chiusura_prematura()
IS 'BEFORE UPDATE OF stato_id su flussi: blocca il completamento del flusso di chiusura (template.chiude_pratica) se restano altri obbligatori bloccanti (fn_check_pratica_chiudibile escludendo il template stesso).';
```

---
{% include-markdown "signature-core.md" %}
