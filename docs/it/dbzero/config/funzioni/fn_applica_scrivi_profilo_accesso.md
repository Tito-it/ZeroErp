{% include-markdown "it/dbzero/config/manual/fn_applica_scrivi_profilo_accesso.md" %}
# ⚙️ Funzione `fn_applica_scrivi_profilo_accesso`

```sql
CREATE FUNCTION fn_applica_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb, p_azioni jsonb, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_applica_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb DEFAULT NULL::jsonb, p_azioni jsonb DEFAULT NULL::jsonb, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi    jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_id       config.profili_accesso.id%TYPE;
    v_tipo     config.profili_accesso.tipo%TYPE;
    c_ammesse  CONSTANT text[] := ARRAY['attivo', 'richiede_secondo_fattore'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Primitiva: scrivere un profilo di accesso, crearlo o
    --   aggiornarlo per codice, e sostituirne le aree e le azioni
    --   se indicate. Ritorna l'id. Non chiede permessi: lo chiede
    --   il verbo config.fn_scrivi_profilo_accesso. L'app non la esegue.
    --
    -- Regole:
    --   - campi assenti: il DEFAULT alla nascita, invariati dopo;
    --   - aree/azioni NULL = invariate, un elenco = sostituite;
    --   - un codice di un altro tipo, argomenti mancanti,
    --     elenchi malformati: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - chiave estranea nei campi: E_CAMPO_NON_AMMESSO.
    -- =========================================================
    IF p_tipo IS NULL OR NULLIF(btrim(p_codice), '') IS NULL OR p_descrizione IS NULL
       OR jsonb_typeof(v_campi) <> 'object'
       OR (p_aree IS NOT NULL AND jsonb_typeof(p_aree) <> 'array')
       OR (p_azioni IS NOT NULL AND jsonb_typeof(p_azioni) <> 'array') THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_scrivi_profilo_accesso', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo',        p_tipo,
                               'codice',      p_codice,
                               'tipo_campi',  jsonb_typeof(v_campi),
                               'tipo_aree',   jsonb_typeof(p_aree),
                               'tipo_azioni', jsonb_typeof(p_azioni)),
            NULL::uuid,
            'config.fn_scrivi_profilo_accesso',
            'tipo, codice o descrizione mancanti, o campi, aree, azioni malformati');
    END IF;

    PERFORM script.fn_guard_campi_ammessi(
        v_campi, c_ammesse,
        'config', 'config.fn_scrivi_profilo_accesso',
        jsonb_build_object('codice', p_codice));

    -- 1. Il profilo, per codice: un codice ha un tipo solo.
    --    ⛔ Si CERCA col codice normalizzato, si SCRIVE quello
    --    ricevuto: lo normalizza il trigger CODICE_MAIUSCOLO, che
    --    dice anche se in maiuscolo supera la colonna (rev 2026-11-04).
    SELECT pa.id, pa.tipo
      INTO v_id, v_tipo
      FROM config.profili_accesso pa
     WHERE pa.codice = script.fn_codice_normalizzato(p_codice);

    IF v_id IS NULL THEN
        INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo, richiede_secondo_fattore)
        VALUES (p_tipo, p_codice, p_descrizione,
                COALESCE((v_campi ->> 'attivo')::boolean, true),
                COALESCE((v_campi ->> 'richiede_secondo_fattore')::boolean, false))
        RETURNING id INTO v_id;
    ELSIF v_tipo IS DISTINCT FROM p_tipo THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_scrivi_profilo_accesso', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('codice', p_codice, 'tipo_esistente', v_tipo, 'tipo_chiesto', p_tipo),
            NULL::uuid,
            'config.fn_scrivi_profilo_accesso',
            'il codice e'' di un profilo di un altro tipo');
    ELSE
        UPDATE config.profili_accesso pa
           SET descrizione              = p_descrizione,
               attivo                   = COALESCE((v_campi ->> 'attivo')::boolean, pa.attivo),
               richiede_secondo_fattore = COALESCE((v_campi ->> 'richiede_secondo_fattore')::boolean,
                                                   pa.richiede_secondo_fattore)
         WHERE pa.id = v_id;
    END IF;

    -- 2. Le aree, sostituite.
    IF p_aree IS NOT NULL THEN
        DELETE FROM config.profili_accesso_aree paa WHERE paa.profilo_accesso_id = v_id;
        INSERT INTO config.profili_accesso_aree (profilo_accesso_id, area_id, livello)
        SELECT v_id, (a ->> 'area_id')::integer, (a ->> 'livello')::config.livello_accesso
          FROM jsonb_array_elements(p_aree) AS a;
    END IF;

    -- 3. Le azioni, sostituite.
    IF p_azioni IS NOT NULL THEN
        DELETE FROM config.profili_accesso_azioni paz WHERE paz.profilo_accesso_id = v_id;
        INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
        SELECT v_id, (a ->> 'azione_id')::integer, (a ->> 'abilitata')::boolean
          FROM jsonb_array_elements(p_azioni) AS a;
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION config.fn_applica_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb, p_azioni jsonb, p_campi jsonb)
IS 'Primitiva: scrive un profilo di accesso per codice (uq_profili_accesso_codice): lo crea, o ne aggiorna descrizione e campi; poi ne sostituisce le aree (p_aree: elenco di {area_id, livello}) e le azioni (p_azioni: elenco di {azione_id, abilitata}) se indicate, NULL = invariate. p_campi: attivo, richiede_secondo_fattore; assenti valgono il DEFAULT alla nascita (true, false) e restano invariati dopo; una chiave estranea: E_CAMPO_NON_AMMESSO. Il profilo si cerca con script.fn_codice_normalizzato e si scrive col codice ricevuto, che il trigger CODICE_MAIUSCOLO normalizza. Un codice che esiste con un altro tipo, argomenti mancanti o elenchi malformati: E_SCRIPT_CHIAMATA_NON_VALIDA. FK, unicità dell''area e livello valido li dicono i vincoli. Ritorna l''id. Non scrive legami e non chiede permessi; l''applicazione non la esegue: la chiamano il verbo config.fn_scrivi_profilo_accesso e anagrafiche.fn_provisiona_dati_di_sviluppo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
