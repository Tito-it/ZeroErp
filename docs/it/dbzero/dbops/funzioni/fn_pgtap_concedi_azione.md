{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_concedi_azione.md" %}
# ⚙️ Funzione `fn_pgtap_concedi_azione`

```sql
CREATE FUNCTION fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: concedere a un utente di fixture un'azione di processo, con un
--   override utente valido da oggi e senza scadenza, e fare in modo che
--   VALGA: dal tetto d'area (brief-db-permessi-tetto-area) anche l'area
--   dell'azione deve arrivare al suo livello_minimo_area. Solo per i pgTAP.
-- Uso: PERFORM dbops.fn_pgtap_concedi_azione(
--          (SELECT auth_user_id FROM _mondo), 'registra_magazzino');
DECLARE
    v_azione_id   config.azioni_processo.id%TYPE;
    v_area_id     config.azioni_processo.area_id%TYPE;
    v_minimo      config.azioni_processo.livello_minimo_area%TYPE;
    v_schema_db   config.aree_funzionali.schema_db%TYPE;
    v_override_id config.user_override_azioni.id%TYPE;
BEGIN
    SELECT ap.id, ap.area_id, ap.livello_minimo_area, af.schema_db
      INTO v_azione_id, v_area_id, v_minimo, v_schema_db
      FROM config.azioni_processo ap
      JOIN config.aree_funzionali af ON af.id = ap.area_id
     WHERE ap.permission_codename = p_permission_codename;

    IF v_azione_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_concedi_azione: azione di processo % inesistente', p_permission_codename;
    END IF;

    INSERT INTO config.user_override_azioni
           (auth_user_id, azione_id, abilitata, motivo, valido_dal, valido_al)
    VALUES (p_auth_user_id, v_azione_id, true, 'Fixture pgTAP', (SELECT script.fn_data_operativa()), NULL)
    ON CONFLICT ON CONSTRAINT uq_user_override_azioni_user_azione
    DO UPDATE SET abilitata  = true,
                  valido_dal = (SELECT script.fn_data_operativa()),
                  valido_al  = NULL
    RETURNING id INTO v_override_id;

    -- Il tetto d'area: se l'area non arriva al minimo dell'azione, la si apre
    -- AL MINIMO (non di piu'), con un override d'area come lo scrive il pannello.
    IF NOT script.fn_area_consente_azione(
               script.fn_resolve_livello_area(p_auth_user_id, v_schema_db), v_minimo) THEN
        -- ⛔ Un override d'area valido scritto dal test e' una scelta del test: la
        --    fixture non lo scavalca, lo dice.
        IF EXISTS (SELECT 1
                     FROM config.user_override_aree uoa
                    WHERE uoa.auth_user_id = p_auth_user_id
                      AND uoa.area_id      = v_area_id
                      AND uoa.validita @> (SELECT script.fn_data_operativa())) THEN
            RAISE EXCEPTION 'fn_pgtap_concedi_azione: l''area % dell''azione % e'' chiusa da un override d''area del test: l''azione non varrebbe (tetto d''area)',
                            v_schema_db, p_permission_codename;
        END IF;

        INSERT INTO config.user_override_aree
               (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
        VALUES (p_auth_user_id, v_area_id, v_minimo,
                'Fixture pgTAP: tetto d''area di ' || p_permission_codename,
                (SELECT script.fn_data_operativa()), NULL)
        ON CONFLICT ON CONSTRAINT uq_user_override_aree_user_area
        DO UPDATE SET livello    = EXCLUDED.livello,
                      valido_dal = (SELECT script.fn_data_operativa()),
                      valido_al  = NULL;
    END IF;

    RETURN v_override_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
IS 'Fixture pgTAP: concede un''azione di processo a un utente con un override (config.user_override_azioni, abilitata, valido da oggi senza scadenza), idempotente sulla UNIQUE (utente, azione), e la fa VALERE: se l''area dell''azione non arriva al suo livello_minimo_area (script.fn_area_consente_azione, il tetto d''area) scrive un override d''area al minimo, valido da oggi. Un override d''area valido gia'' scritto dal test che chiude l''area -> RAISE: la fixture non scavalca la scelta del test. Serve ai pgTAP dei verbi che applicano un''azione con script.fn_guard_azione: l''operatore di dbops.fn_pgtap_crea_emittente_operatore non ha ne'' azioni ne'' aree. Azione inesistente -> RAISE. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
