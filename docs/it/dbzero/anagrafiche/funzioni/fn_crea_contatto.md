{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_contatto.md" %}
# ⚙️ Funzione `fn_crea_contatto`

```sql
CREATE FUNCTION fn_crea_contatto(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_campi jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_contatto(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_campi jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi    jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_estranea text;
    v_manca    text;
    c_ammesse  CONSTANT text[] := ARRAY[
        'tipo_contatto_id', 'nominativo', 'email', 'telefono', 'cellulare',
        'pec', 'note', 'is_default', 'default_context', 'titolo_cortesia_id',
        'unita_organizzativa_id', 'istanza_utility_id'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare un contatto del soggetto (p_soggetto_ruolo_id
    --   NULL) o di un suo ruolo, con le chiavi di p_campi (le
    --   assenti al DEFAULT). Ritorna la riga creata.
    --
    -- Regole:
    --   - nominativo e tipo di contatto obbligatori, non vuoti:
    --     E_CONTATTO_INCOMPLETO col primo campo che manca;
    --   - una chiave estranea si rifiuta: E_CAMPO_NON_AMMESSO.
    -- =========================================================
    IF p_soggetto_id IS NULL OR jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_contatto', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_id', p_soggetto_id,
                               'tipo_campi',  jsonb_typeof(v_campi)),
            NULL::uuid,
            'anagrafiche.fn_crea_contatto',
            'soggetto mancante o campi che non sono un oggetto');
    END IF;

    v_estranea := script.fn_prima_chiave_estranea(v_campi, c_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_contatto', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'soggetto_id', p_soggetto_id),
            NULL::uuid,
            v_estranea);
    END IF;

    v_manca := CASE
                   WHEN NULLIF(btrim(v_campi ->> 'nominativo'), '') IS NULL THEN 'nominativo'
                   WHEN COALESCE((v_campi ->> 'tipo_contatto_id')::integer, 0) <= 0 THEN 'tipo_contatto_id'
               END;
    IF v_manca IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_contatto', 'E_CONTATTO_INCOMPLETO',
            jsonb_build_object('campo', v_manca, 'soggetto_id', p_soggetto_id),
            NULL::uuid,
            v_manca);
    END IF;

    RETURN script.fn_scrivi_riga_da_jsonb(
               'anagrafiche.contatti'::regclass,
               v_campi || jsonb_build_object('soggetto_id',       p_soggetto_id,
                                             'soggetto_ruolo_id', p_soggetto_ruolo_id));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_contatto(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_campi jsonb)
IS 'BB (2026-10-17): crea un contatto del soggetto (p_soggetto_ruolo_id NULL) o di un suo ruolo, con le chiavi di p_campi: tipo_contatto_id, nominativo, email, telefono, cellulare, pec, note, is_default, default_context, titolo_cortesia_id, unita_organizzativa_id, istanza_utility_id (le assenti al DEFAULT). Nominativo e tipo di contatto obbligatori e non vuoti: E_CONTATTO_INCOMPLETO col campo sul canale COLUMN. Chiave estranea: E_CAMPO_NON_AMMESSO. Soggetto mancante o campi non oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA. Ritorna la riga creata (jsonb). Scrive con script.fn_scrivi_riga_da_jsonb; i guard della tabella (coerenza col ruolo, contatto di default) scattano come sempre. Non controlla il permesso (dominio anagrafiche, B-5). INVOKER. Regola del 2: sede unica dell''INSERT che era in SoggettiRepository.crea_contatto (2b-2), anagrafiche.fn_crea_soggetto_pf, fn_crea_soggetto_pg, script.fn_crea_utente_tecnico e dbops.fn_pgtap_crea_soggetto_pg. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 3).';
```

---
{% include-markdown "signature-core.md" %}
