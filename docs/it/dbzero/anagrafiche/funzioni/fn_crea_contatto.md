{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_contatto.md" %}
# ⚙️ Funzione `fn_crea_contatto`

```sql
CREATE FUNCTION fn_crea_contatto(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_contatto(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_campi jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi      CONSTANT text := 'anagrafiche.fn_crea_contatto';
    v_campi    jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_manca    text;   -- il nome della chiave obbligatoria che manca, non una colonna
    v_tipo_txt text;   -- il tipo come arriva, prima di sapere se e' un numero
    v_tipo     anagrafiche.contatti.tipo_contatto_id%TYPE;
    v_vincolo  text;
    c_ammesse  CONSTANT text[] := ARRAY[
        'tipo_contatto_id', 'nominativo', 'email', 'telefono', 'cellulare',
        'pec', 'note', 'is_default', 'titolo_cortesia_id',
        'unita_organizzativa_id', 'istanza_utility_id'];
    c_doppioni CONSTANT text[] := ARRAY[
        'uq_contatti_soggetto_tipo', 'uq_contatti_ruolo_tipo_no_istanza',
        'uq_contatti_ruolo_istanza_tipo'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare un contatto del soggetto (p_soggetto_ruolo_id
    --   NULL) o di un suo ruolo, con le chiavi di p_campi (le
    --   assenti al DEFAULT). Ritorna la riga creata.
    --
    -- Regole:
    --   - una chiave estranea si rifiuta: E_CAMPO_NON_AMMESSO;
    --   - nominativo e tipo di contatto obbligatori, non vuoti,
    --     il tipo un intero positivo: E_CONTATTO_INCOMPLETO col
    --     primo campo che manca;
    --   - il tipo esiste nel catalogo: E_TIPO_CONTATTO_NON_TROVATO;
    --   - un contatto per tipo nel contesto (i tre indici
    --     uq_contatti_*): E_CONTATTO_TIPO_DUPLICATO.
    -- =========================================================
    IF p_soggetto_id IS NULL OR jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', v_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_id', p_soggetto_id,
                               'tipo_campi',  jsonb_typeof(v_campi)),
            NULL::uuid,
            v_chi,
            'soggetto mancante o campi che non sono un oggetto');
    END IF;

    PERFORM script.fn_guard_campi_ammessi(
        v_campi, c_ammesse,
        'anagrafiche', v_chi,
        jsonb_build_object('soggetto_id', p_soggetto_id));

    -- Il tipo si legge come testo: il cast arriva solo su un intero.
    v_tipo_txt := btrim(v_campi ->> 'tipo_contatto_id');
    v_tipo := CASE WHEN v_tipo_txt ~ '^[0-9]{1,9}$' THEN v_tipo_txt::integer END;

    v_manca := CASE
                   WHEN NULLIF(btrim(v_campi ->> 'nominativo'), '') IS NULL THEN 'nominativo'
                   WHEN COALESCE(v_tipo, 0) <= 0 THEN 'tipo_contatto_id'
               END;
    IF v_manca IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', v_chi, 'E_CONTATTO_INCOMPLETO',
            jsonb_build_object('campo', v_manca, 'soggetto_id', p_soggetto_id,
                               'tipo_contatto_id', v_tipo_txt),
            NULL::uuid,
            v_manca);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM config.tipi_contatti t WHERE t.id = v_tipo) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', v_chi, 'E_TIPO_CONTATTO_NON_TROVATO',
            jsonb_build_object('campo', 'tipo_contatto_id', 'soggetto_id', p_soggetto_id,
                               'tipo_contatto_id', v_tipo),
            NULL::uuid,
            v_tipo::text);
    END IF;

    BEGIN
        RETURN script.fn_scrivi_riga_da_jsonb(
                   'anagrafiche.contatti'::regclass,
                   v_campi || jsonb_build_object('soggetto_id',       p_soggetto_id,
                                                 'soggetto_ruolo_id', p_soggetto_ruolo_id));
    EXCEPTION
        WHEN unique_violation THEN
            GET STACKED DIAGNOSTICS v_vincolo = CONSTRAINT_NAME;
            IF v_vincolo IS NULL OR NOT (v_vincolo = ANY (c_doppioni)) THEN
                RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', v_chi, 'E_CONTATTO_TIPO_DUPLICATO',
                jsonb_build_object('campo',              'tipo_contatto_id',
                                   'vincolo',            v_vincolo,
                                   'soggetto_id',        p_soggetto_id,
                                   'soggetto_ruolo_id',  p_soggetto_ruolo_id,
                                   'istanza_utility_id', v_campi ->> 'istanza_utility_id',
                                   'tipo_contatto_id',   v_tipo),
                NULL::uuid,
                (SELECT t.descrizione FROM config.tipi_contatti t WHERE t.id = v_tipo),
                CASE v_vincolo
                    WHEN 'uq_contatti_ruolo_istanza_tipo'    THEN 'per questo ruolo su questa istanza'
                    WHEN 'uq_contatti_ruolo_tipo_no_istanza' THEN 'per questo ruolo'
                    ELSE 'per questo soggetto'
                END);
    END;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_contatto(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_campi jsonb)
IS 'BB: crea un contatto del soggetto (p_soggetto_ruolo_id NULL) o di un suo ruolo, con le chiavi di p_campi: tipo_contatto_id, nominativo, email, telefono, cellulare, pec, note, is_default, titolo_cortesia_id, unita_organizzativa_id, istanza_utility_id (le assenti al DEFAULT). Chiave estranea: E_CAMPO_NON_AMMESSO. Nominativo e tipo di contatto obbligatori e non vuoti, il tipo un intero positivo: E_CONTATTO_INCOMPLETO col campo sul canale COLUMN. Il tipo che il catalogo config.tipi_contatti non ha: E_TIPO_CONTATTO_NON_TROVATO (campo tipo_contatto_id). Un secondo contatto dello stesso tipo nello stesso contesto (gli indici uq_contatti_soggetto_tipo, uq_contatti_ruolo_tipo_no_istanza, uq_contatti_ruolo_istanza_tipo, riconosciuti per nome): E_CONTATTO_TIPO_DUPLICATO (campo tipo_contatto_id, il tipo e il livello nella frase); ogni altra violazione risale com''e''. Soggetto mancante o campi non oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA. Ritorna la riga creata (jsonb). Scrive con script.fn_scrivi_riga_da_jsonb; i trigger della tabella (coerenza col ruolo e l''istanza, contatto predefinito) scattano come sempre. Non controlla il permesso (dominio anagrafiche, B-5). INVOKER. Regola del 2: sede unica dell''INSERT di un contatto, per le madri anagrafiche.fn_crea_soggetto_pf, fn_crea_soggetto_pg, script.fn_crea_utente_tecnico, per dbops.fn_pgtap_crea_soggetto_pg e per il backend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
