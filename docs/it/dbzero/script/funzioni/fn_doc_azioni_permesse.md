{% include-markdown "it/dbzero/script/manual/fn_doc_azioni_permesse.md" %}
# ⚙️ Funzione `fn_doc_azioni_permesse`

```sql
CREATE FUNCTION fn_doc_azioni_permesse(p_testata regclass, p_stato_da_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_azioni_permesse(p_testata regclass, p_stato_da_id bigint)
 RETURNS TABLE(stato_a_id bigint, stato_a_codice text, action_key text, azione_processo_codename character varying, meta jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- I nomi vengono dalla mappa: tipi nudi.
    v_vocabolario regclass;
    v_matrice     regclass;
    v_col_da      text;
    v_col_a       text;
    v_vivo        text;
    v_filtro      text;
    -- L'utente della sessione, per l'azione del passaggio.
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: i passaggi manuali dallo stato p_stato_da_id che
    --   l'utente della sessione puo' fare.
    -- Regole:
    --   - testata fuori mappa: il chiamante e' rotto,
    --     E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - stato NULL: nessuna riga;
    --   - manuale e azione dalla riga del passaggio
    --     (script.fn_doc_passaggio), come il verbo;
    --   - permesso => nascondi: azione NULL resta (decide il
    --     livello sul documento), altrimenti la concessione.
    -- =========================================================
    SELECT m.vocabolario, m.matrice, m.colonna_da, m.colonna_a, m.colonna_vivo, m.filtro
      INTO v_vocabolario, v_matrice, v_col_da, v_col_a, v_vivo, v_filtro
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_matrice IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_azioni_permesse', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_doc_azioni_permesse',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    IF p_stato_da_id IS NULL THEN
        RETURN;
    END IF;

    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    RETURN QUERY EXECUTE format(
        'SELECT t.%2$I::bigint, s.codice_interno::text, t.meta ->> ''action_key'','
        '       pz.azione_processo_codename, t.meta'
        '  FROM %3$s t'
        '  JOIN %4$s s ON s.id = t.%2$I'
        ' CROSS JOIN LATERAL script.fn_doc_passaggio($1, t.%1$I, t.%2$I) pz'
        ' WHERE t.%1$I = $2 AND t.%5$I IS TRUE %6$s'
        '   AND pz.manuale IS TRUE'
        '   AND (pz.azione_processo_codename IS NULL'
        '        OR script.fn_check_azione_processo($3, pz.azione_processo_codename))',
        v_col_da, v_col_a, v_matrice, v_vocabolario, v_vivo, v_filtro)
      USING p_testata, p_stato_da_id, v_utente;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_azioni_permesse(p_testata regclass, p_stato_da_id bigint)
IS 'BB del modello del documento: i passaggi MANUALI da uno stato di una testata della mappa che l''utente della sessione (app.current_user_id) puo'' fare. Righe vive della matrice (colonna del passaggio vivo e filtro dalla mappa script.fn_doc_stato_modello), manuale e azione dalla riga del passaggio (script.fn_doc_passaggio, come il verbo), permesso => nascondi: azione NULL resta (decide il livello sul documento), altrimenti script.fn_check_azione_processo. Restituisce stato d''arrivo (id e codice), action_key e la meta della riga; l''ordine lo da'' il chiamante. Niente fn_check_*: che cosa e'' eseguibile adesso (abilitazione, motivi) resta della capability del dettaglio. Riceve lo STATO e non il documento (D-1): il permesso non dipende dal documento, e capability e righe di lista lo hanno gia''. Stato NULL: nessuna riga; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Gemello di script.fn_doc_azione_passaggio (che risponde per UN passaggio). Consumatori: le otto script.fn_available_actions_* di vendita (preventivo, offerta, contratto, ordine, ddt, reso, commessa, lotto), il backend (le azioni permesse per riga della lista dei lotti). Brief: brief-modello-documento-vendita §15.14 (Tid 2026-10-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
