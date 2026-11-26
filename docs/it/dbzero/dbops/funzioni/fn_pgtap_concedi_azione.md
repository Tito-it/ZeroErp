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
-- ⚠️ Le voci le scrivono i verbi del SUPER_ADMIN (dbops.fn_pgtap_scrivi_override):
--   le altre voci dell'utente restano, i loro id cambiano.
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

    PERFORM dbops.fn_pgtap_scrivi_override(
        'config.user_override_azioni'::regclass, p_auth_user_id,
        jsonb_build_object('azione_id', v_azione_id),
        jsonb_build_object('abilitata',  true,
                           'motivo',     'Fixture pgTAP',
                           'valido_dal', (SELECT script.fn_data_operativa()),
                           'valido_al',  NULL));

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

        PERFORM dbops.fn_pgtap_scrivi_override(
            'config.user_override_aree'::regclass, p_auth_user_id,
            jsonb_build_object('area_id', v_area_id),
            jsonb_build_object('livello',    v_minimo,
                               'motivo',     'Fixture pgTAP: tetto d''area di ' || p_permission_codename,
                               'valido_dal', (SELECT script.fn_data_operativa()),
                               'valido_al',  NULL));
    END IF;

    SELECT uoz.id INTO v_override_id
      FROM config.user_override_azioni uoz
     WHERE uoz.auth_user_id = p_auth_user_id
       AND uoz.azione_id    = v_azione_id;

    RETURN v_override_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
IS 'Fixture pgTAP: concede un''azione di processo a un utente con un override (config.user_override_azioni, abilitata, valido da oggi senza scadenza), idempotente sulla UNIQUE (utente, azione), e la fa VALERE: se l''area dell''azione non arriva al suo livello_minimo_area (script.fn_area_consente_azione, il tetto d''area) scrive un override d''area al minimo, valido da oggi. Un override d''area valido già scritto dal test che chiude l''area -> RAISE: la fixture non scavalca la scelta del test. Le voci le scrivono i verbi del SUPER_ADMIN config.fn_imposta_override_azioni e _aree, da dbops.fn_pgtap_scrivi_override: le altre voci dell''utente restano, i loro id cambiano. Ritorna l''id della riga. Il gemello che nega è dbops.fn_pgtap_nega_azione. Serve ai pgTAP dei verbi che applicano un''azione con script.fn_guard_azione: l''operatore di dbops.fn_pgtap_crea_emittente_operatore non ha né azioni né aree. Azione inesistente -> RAISE. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
