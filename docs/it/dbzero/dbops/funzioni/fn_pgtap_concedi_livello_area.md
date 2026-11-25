{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_concedi_livello_area.md" %}
# ⚙️ Funzione `fn_pgtap_concedi_livello_area`

```sql
CREATE FUNCTION fn_pgtap_concedi_livello_area(p_auth_user_id integer, p_area_schema_db character varying, p_livello config.livello_accesso)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_concedi_livello_area(p_auth_user_id integer, p_area_schema_db character varying, p_livello config.livello_accesso)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a un utente di fixture un livello su un'AREA funzionale, con un
--   override utente valido da oggi e senza scadenza. Gemello di
--   dbops.fn_pgtap_concedi_azione, per i verbi che chiedono un livello
--   d'area (script.fn_guard_livello_area) o un livello d'oggetto che ricade
--   sull'area (script.fn_guard_livello). Solo per i pgTAP.
-- Uso: PERFORM dbops.fn_pgtap_concedi_livello_area(
--          (SELECT auth_user_id FROM _mondo), 'vendite', 'TUTTO');
-- ⚠️ Scrive il livello chiesto, anche piu' basso di quello che c'e': e' cosi'
--   che un test costruisce il caso «senza il livello» (LETTURA, BLOCCATO).
DECLARE
    v_area_id     config.aree_funzionali.id%TYPE;
    v_override_id config.user_override_aree.id%TYPE;
BEGIN
    SELECT af.id INTO v_area_id
      FROM config.aree_funzionali af
     WHERE af.schema_db = p_area_schema_db;

    IF v_area_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_concedi_livello_area: area funzionale % inesistente', p_area_schema_db;
    END IF;
    IF p_auth_user_id IS NULL OR p_livello IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_concedi_livello_area: utente e livello obbligatori';
    END IF;

    INSERT INTO config.user_override_aree
           (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
    VALUES (p_auth_user_id, v_area_id, p_livello, 'Fixture pgTAP',
            (SELECT script.fn_data_operativa()), NULL)
    ON CONFLICT ON CONSTRAINT uq_user_override_aree_user_area
    DO UPDATE SET livello    = EXCLUDED.livello,
                  valido_dal = (SELECT script.fn_data_operativa()),
                  valido_al  = NULL
    RETURNING id INTO v_override_id;

    RETURN v_override_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_concedi_livello_area(p_auth_user_id integer, p_area_schema_db character varying, p_livello config.livello_accesso)
IS 'Fixture pgTAP: da'' a un utente un livello su un''area funzionale con un override (config.user_override_aree, valido da oggi senza scadenza), idempotente sulla UNIQUE (utente, area): il secondo giro scrive il livello nuovo, anche piu'' basso, ed e'' cosi'' che un test costruisce il caso «senza il livello». Area inesistente, utente o livello nulli -> RAISE. Gemello di dbops.fn_pgtap_concedi_azione, per i verbi che chiedono un livello d''area (script.fn_guard_livello_area) o d''oggetto con la ricaduta sull''area (script.fn_guard_livello): l''operatore di dbops.fn_pgtap_crea_emittente_operatore non ha ne'' azioni ne'' aree. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
