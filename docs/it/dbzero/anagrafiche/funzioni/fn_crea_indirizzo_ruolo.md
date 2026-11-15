{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzo_ruolo.md" %}
# ⚙️ Funzione `fn_crea_indirizzo_ruolo`

```sql
CREATE FUNCTION fn_crea_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi      CONSTANT text := 'anagrafiche.fn_crea_indirizzo_ruolo';
    v_istanza  anagrafiche.indirizzi.istanza_utility_id%TYPE;
    v_el       jsonb;
    v_id       anagrafiche.indirizzi.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere UN indirizzo di un ruolo, e ritornarne l'id.
    --   p_indirizzo: un oggetto con il tipo (id o codice
    --   interno) e l'indirizzo in una delle tre forme di
    --   anagrafiche.fn_indirizzo_elemento; in piu', facoltativa,
    --   l'istanza (istanza_utility_id).
    --
    -- Regole:
    --   - l'istanza la legge questa madre: il BB dell'elemento
    --     e' comune al soggetto, che istanze non ne ha;
    --   - il tipo (gia' presente nella chiave ruolo + istanza,
    --     ammesso dal tipo di ruolo) lo giudica
    --     fn_check_tipo_indirizzo_ruolo: qui si solleva il suo
    --     primo motivo, il predicato non si ricopia;
    --   - ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO.
    -- =========================================================
    IF NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                    WHERE sr.id = p_soggetto_ruolo_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            COALESCE(p_soggetto_ruolo_id::text, '-'));
    END IF;

    IF jsonb_typeof(p_indirizzo) = 'object' THEN
        v_istanza := (p_indirizzo ->> 'istanza_utility_id')::bigint;
    END IF;

    v_el := anagrafiche.fn_indirizzo_elemento(
                CASE WHEN jsonb_typeof(p_indirizzo) = 'object'
                     THEN p_indirizzo - 'istanza_utility_id'
                     ELSE p_indirizzo END,
                c_chi,
                jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id));

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', c_chi,
        anagrafiche.fn_check_tipo_indirizzo_ruolo(
            p_soggetto_ruolo_id, v_istanza,
            (v_el ->> 'tipo_indirizzo_id')::integer),
        'tipo_indirizzo_codice_interno');

    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
        indirizzo_dettaglio_id, indirizzo_libero,
        stato_id, comune_id, codice_postale_id,
        administrative_area, locality, sublocality, postal_code)
    VALUES (
        p_soggetto_ruolo_id, (v_el ->> 'tipo_indirizzo_id')::integer, v_istanza,
        anagrafiche.fn_indirizzo_elemento_dettaglio(v_el),
        NULLIF(btrim(v_el ->> 'indirizzo_libero'), ''),
        (v_el ->> 'stato_id')::integer,
        (v_el ->> 'comune_id')::integer,
        (v_el ->> 'codice_postale_id')::integer,
        v_el ->> 'administrative_area',
        v_el ->> 'locality',
        v_el ->> 'sublocality',
        v_el ->> 'postal_code')
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo jsonb)
IS 'Madre singolare: scrive UN indirizzo di un ruolo (anagrafiche.indirizzi), anche di un''istanza (chiave facoltativa istanza_utility_id), e ne ritorna l''id. L''elemento ha la grammatica di anagrafiche.fn_indirizzo_elemento (tipo per id o codice interno; forma libera, dettaglio gia'' risolto o via da risolvere; chiavi estranee E_CAMPO_NON_AMMESSO); l''istanza la legge questa madre, perche'' il BB e'' comune al soggetto. Il tipo lo giudica anagrafiche.fn_check_tipo_indirizzo_ruolo sulla chiave (ruolo, istanza), di cui si solleva il primo motivo prima di scrivere (campo tipo_indirizzo_codice_interno): tipo gia'' presente E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE, tipo non ammesso dal tipo di ruolo E_TIPO_INDIRIZZO_NON_PERMESSO. Il salto dei tipi presenti e'' della plurale anagrafiche.fn_crea_indirizzi_ruolo, che scrive un elenco e usa questa. Ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO. La forma dell''indirizzo libero la dice il guard della tabella; restano sulla tabella, per ogni altra strada e contro la corsa, il guard trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo e gli indici uq_indirizzi_ruolo_tipo_no_istanza e uq_indirizzi_ruolo_istanza_tipo. Gemella di anagrafiche.fn_crea_indirizzo_soggetto. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
