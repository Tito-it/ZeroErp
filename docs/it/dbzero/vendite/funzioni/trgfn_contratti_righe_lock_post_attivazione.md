{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_righe_lock_post_attivazione.md" %}
# ⚙️ Funzione `trgfn_contratti_righe_lock_post_attivazione`

```sql
CREATE FUNCTION trgfn_contratti_righe_lock_post_attivazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_lock_post_attivazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca INSERT, UPDATE e DELETE su contratti_righe quando il contratto
--   padre è ATTIVO. Le eccezioni sono immutabili post-attivazione (§3-bis-A).
-- Enforcement DB-first: garantisce il blocco anche da psql diretto o script.
-- Errore: E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE (452).
DECLARE
    v_contratto_id vendite.contratti_righe.contratto_id%TYPE;
    v_articolo_id  vendite.contratti_righe.articolo_id%TYPE;
    v_codice_stato config.stati_doc_contratti.codice_interno%TYPE;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_contratto_id := OLD.contratto_id;
        v_articolo_id  := OLD.articolo_id;
    ELSE
        v_contratto_id := NEW.contratto_id;
        v_articolo_id  := NEW.articolo_id;
    END IF;

    SELECT sdc.codice_interno
      INTO v_codice_stato
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti sdc ON sdc.id = c.stato_doc_contratto_id
     WHERE c.id = v_contratto_id;

    IF v_codice_stato = 'ATTIVO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE',
            jsonb_build_object(
                'contratto_id', v_contratto_id,
                'articolo_id',  v_articolo_id,
                'operazione',   TG_OP
            ),
            CASE WHEN TG_OP = 'DELETE' THEN OLD.tx_id ELSE NEW.tx_id END,
            v_contratto_id::text,
            TG_OP
        );
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_lock_post_attivazione()
IS 'Lock righe post-attivazione: blocca INSERT/UPDATE/DELETE su contratti_righe quando il contratto padre è ATTIVO. Errore: E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE (452). Step 2.3.';
```

---
{% include-markdown "signature-core.md" %}
