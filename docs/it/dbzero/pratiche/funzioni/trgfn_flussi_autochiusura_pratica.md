{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_autochiusura_pratica.md" %}
# ⚙️ Funzione `trgfn_flussi_autochiusura_pratica`

```sql
CREATE FUNCTION trgfn_flussi_autochiusura_pratica()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_autochiusura_pratica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: chiusura guidata dal workflow. Al completamento di un flusso
--   chiude automaticamente la pratica padre (APERTA -> CHIUSA).
-- Regole:
--   1. Scatta solo alla transizione di stato verso COMPLETATO.
--   2. Solo da pratica APERTA (no SOSPESA/BOZZA/terminale).
--   3. Definizione CON flusso di chiusura -> chiude sse il flusso
--      completato e' quello; nessun altro flusso chiude la pratica.
--   4. Definizione SENZA flusso di chiusura ma con >=1 obbligatorio
--      attivo -> chiude sse fn_check_pratica_chiudibile (D1: nessun
--      bloccante E nessun flusso istanziato aperto, escluso NEW.id).
--   5. Definizione senza obbligatori e senza flusso di chiusura -> no-op.
--   6. La UPDATE su pratiche attraversa guard transizione/chiusura e
--      giornale esistenti (chiusura registrata come la manuale).
-- Fork-aware: template di chiusura e gate obbligatori scopati per la
--   DEFINIZIONE pinnata della pratica (definizione_id), non per tipo:
--   con i fork esistono piu' definizioni per tipo.
DECLARE
    v_completato_id  config.stati_flussi_pratiche.id%TYPE;
    v_pratica_stato  config.stati_pratiche.codice_interno%TYPE;
    v_definizione_id pratiche.pratiche.definizione_id%TYPE;
    v_chiusura_tmpl  pratiche.template_flussi.id%TYPE;
    v_chiusa_id      config.stati_pratiche.id%TYPE;
    v_aperta_id      config.stati_pratiche.id%TYPE;
    v_ha_obbligatori boolean;
    v_deve_chiudere  boolean := false;
BEGIN
    -- (1) Solo verso COMPLETATO, e solo se lo stato cambia davvero.
    SELECT id INTO v_completato_id
      FROM config.stati_flussi_pratiche
     WHERE codice_interno = 'COMPLETATO';

    IF NEW.stato_id IS DISTINCT FROM v_completato_id
       OR OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;
    END IF;

    -- Stato e definizione pinnata della pratica padre.
    SELECT sp.codice_interno, p.definizione_id
      INTO v_pratica_stato, v_definizione_id
      FROM pratiche.pratiche p
      JOIN config.stati_pratiche sp ON sp.id = p.stato_id
     WHERE p.id = NEW.pratica_id;

    -- (2) Auto-chiusura solo da APERTA.
    IF v_pratica_stato IS DISTINCT FROM 'APERTA' THEN
        RETURN NEW;
    END IF;

    -- Flusso di chiusura della DEFINIZIONE pinnata (0/1 per definizione).
    SELECT tf.id INTO v_chiusura_tmpl
      FROM pratiche.template_flussi tf
     WHERE tf.definizione_id = v_definizione_id
       AND tf.chiude_pratica
       AND tf.attivo
     LIMIT 1;

    IF v_chiusura_tmpl IS NOT NULL THEN
        -- (3) Modello con flusso di chiusura.
        v_deve_chiudere := (NEW.template_flusso_id = v_chiusura_tmpl);
    ELSE
        -- (4)/(5) Modello auto: gate "almeno un obbligatorio".
        SELECT EXISTS (
            SELECT 1 FROM pratiche.template_flussi tf
             WHERE tf.definizione_id = v_definizione_id
               AND tf.obbligatorio
               AND tf.attivo
        ) INTO v_ha_obbligatori;

        v_deve_chiudere := v_ha_obbligatori
                           AND pratiche.fn_check_pratica_chiudibile(NEW.pratica_id, NULL, NEW.id);
    END IF;

    IF v_deve_chiudere THEN
        SELECT id INTO v_aperta_id FROM config.stati_pratiche WHERE codice_interno = 'APERTA';
        SELECT id INTO v_chiusa_id FROM config.stati_pratiche WHERE codice_interno = 'CHIUSA';

        -- Chiude solo se ancora APERTA (sicurezza concorrenza).
        UPDATE pratiche.pratiche
           SET stato_id = v_chiusa_id
         WHERE id = NEW.pratica_id
           AND stato_id = v_aperta_id;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_autochiusura_pratica()
IS 'AFTER UPDATE OF stato_id su flussi: al completamento chiude la pratica padre (APERTA -> CHIUSA) secondo il modello misto (flusso di chiusura | auto con >=1 obbligatorio | no-op). Fork-aware: flusso di chiusura e gate obbligatori scopati per la DEFINIZIONE pinnata (definizione_id), non per tipo. Il modello auto usa fn_check_pratica_chiudibile con predicato D1 (nessun bloccante E nessun flusso aperto, escluso NEW.id). Riusa guard transizione/chiusura e giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
