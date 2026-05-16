{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_lock_post_attivazione.md" %}
# ⚙️ Funzione `trgfn_contratti_lock_post_attivazione`

```sql
CREATE FUNCTION trgfn_contratti_lock_post_attivazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_lock_post_attivazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: impedisce la modifica dei campi pricing della testata su contratti ATTIVI.
-- Campi bloccati (UPDATE OF): listino_id, listino_versione_id,
--   tipo_variazione_globale, valore_variazione_globale.
-- Il trigger non scatta per update di altri campi (meta, note, valido_al).
-- Errore: E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE (452).
DECLARE
    v_codice_stato config.stati_doc_contratti.codice_interno%TYPE;
BEGIN
    SELECT codice_interno
      INTO v_codice_stato
      FROM config.stati_doc_contratti
     WHERE id = OLD.stato_doc_contratto_id;

    IF v_codice_stato = 'ATTIVO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE',
            jsonb_build_object(
                'contratto_id', NEW.id,
                'numero',       NEW.numero,
                'stato',        v_codice_stato
            ),
            NEW.tx_id,
            NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_lock_post_attivazione()
IS 'Lock pricing testata: blocca UPDATE di listino_id, listino_versione_id, tipo_variazione_globale, valore_variazione_globale su contratti ATTIVI. Non scatta per update di altri campi. Errore: E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE (452). Step 2.3.';
```

---
{% include-markdown "signature-core.md" %}
