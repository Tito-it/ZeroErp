{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_emittente_fiscale.md" %}
# ⚙️ Funzione `fn_crea_emittente_fiscale`

```sql
CREATE FUNCTION fn_crea_emittente_fiscale(p_soggetto_id uuid, p_codice character varying, p_campi jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_emittente_fiscale(p_soggetto_id uuid, p_codice character varying, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(emittente_fiscale_id bigint, soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi    jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_estranea text;
    v_sr_id    anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_ef_id    anagrafiche.emittenti_fiscali.id%TYPE;
    -- Le chiavi opzionali: le stesse del backend (_CREATE_COLS).
    c_ammesse  CONSTANT text[] := ARRAY[
        'attivo', 'regime_fiscale_rf', 'bollo_auto', 'bollo_soglia',
        'rounding_policy', 'valuta_id'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare l'emittente fiscale di un soggetto: il ruolo EF
    --   (get_or_create) e la riga di emittenti_fiscali con le
    --   chiavi opzionali di p_campi (le assenti al DEFAULT).
    --   Un regime dichiarato e' confermato. Ritorna
    --   (emittente_fiscale_id, soggetto_ruolo_id).
    --
    -- Regole:
    --   - una chiave fuori elenco si rifiuta: E_CAMPO_NON_AMMESSO;
    --   - duplicati e regime fuori catalogo escono dai vincoli;
    --   - i registri e il mapping di default li fanno i trigger.
    -- =========================================================
    IF jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_emittente_fiscale', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_campi', jsonb_typeof(v_campi)),
            NULL::uuid,
            'anagrafiche.fn_crea_emittente_fiscale',
            'i campi non sono un oggetto');
    END IF;

    v_estranea := script.fn_prima_chiave_estranea(v_campi, c_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_emittente_fiscale', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'soggetto_id', p_soggetto_id),
            NULL::uuid,
            v_estranea);
    END IF;

    v_sr_id := script.fn_get_or_create_soggetto_ruolo(
                   p_soggetto_id  := p_soggetto_id,
                   p_cd_int_ruolo := 'EF');

    v_ef_id := (script.fn_scrivi_riga_da_jsonb(
                    'anagrafiche.emittenti_fiscali'::regclass,
                    v_campi || jsonb_build_object('soggetto_ruolo_id', v_sr_id,
                                                  'codice',            p_codice))
                ->> 'id')::bigint;

    -- Il regime dichiarato si conferma: UPDATE OF regime_fiscale_rf
    -- (trg_emittenti_fiscali_a20_regime_conferma_upd). Lo stesso
    -- valore va bene: conta la colonna nominata.
    IF jsonb_exists(v_campi, 'regime_fiscale_rf') THEN
        UPDATE anagrafiche.emittenti_fiscali ef
           SET regime_fiscale_rf = ef.regime_fiscale_rf
         WHERE ef.id = v_ef_id;
    END IF;

    RETURN QUERY SELECT v_ef_id, v_sr_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_emittente_fiscale(p_soggetto_id uuid, p_codice character varying, p_campi jsonb)
IS 'Madre (2026-10-17): crea l''emittente fiscale di un soggetto, cioe'' il ruolo EF (script.fn_get_or_create_soggetto_ruolo) e la riga di anagrafiche.emittenti_fiscali, in una sola istruzione. p_campi: le chiavi opzionali attivo, regime_fiscale_rf, bollo_auto, bollo_soglia, rounding_policy, valuta_id (le assenti al DEFAULT; una chiave estranea: E_CAMPO_NON_AMMESSO, col campo). Un regime dichiarato e'' CONFERMATO: dopo la INSERT, un UPDATE del regime (la INSERT non conferma mai). Registri di numerazione e mapping di default nascono dai trigger. Duplicati (uq_emittenti_fiscali_ruolo, uq:codice) e regime fuori catalogo (fk_emittenti_fiscali_regimi_fiscali) escono dai vincoli, che il backend traduce per nome. Non controlla la partita IVA del soggetto (pre-check del backend, debito dichiarato) ne'' il permesso (dominio anagrafiche: al backend, precedente B-5). INVOKER. Ritorna (emittente_fiscale_id, soggetto_ruolo_id). Prende il posto di EmittentiFiscaliService.crea_emittente (2b-2) e dell''INSERT di dbops.fn_pgtap_crea_emittente. Brief: brief-db-processi-accensione-per-ambiente (2b-1).';
```

---
{% include-markdown "signature-core.md" %}
