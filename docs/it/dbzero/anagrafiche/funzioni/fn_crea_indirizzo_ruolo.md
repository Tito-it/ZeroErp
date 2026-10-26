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
    --   - un tipo gia' presente lo rifiuta il vincolo;
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
        v_istanza := (p_indirizzo ->> 'istanza_utility_id')::integer;
    END IF;

    v_el := anagrafiche.fn_indirizzo_elemento(
                CASE WHEN jsonb_typeof(p_indirizzo) = 'object'
                     THEN p_indirizzo - 'istanza_utility_id'
                     ELSE p_indirizzo END,
                c_chi,
                jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id));

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
IS 'MADRE SINGOLARE (2026-10-19): scrive UN indirizzo di un ruolo, anche di un''istanza (chiave facoltativa istanza_utility_id), e ne ritorna l''id. L''elemento ha la grammatica di anagrafiche.fn_indirizzo_elemento (tipo per id o codice interno; forma libera, dettaglio gia'' risolto o via da risolvere; chiavi estranee E_CAMPO_NON_AMMESSO); l''istanza la legge questa madre, perche'' il BB e'' comune al soggetto. Un tipo gia'' presente lo rifiuta il vincolo col suo nome (uq_indirizzi_ruolo_tipo_no_istanza / uq_indirizzi_ruolo_istanza_tipo): il salto dei tipi presenti e'' della plurale anagrafiche.fn_crea_indirizzi_ruolo, che scrive un elenco e usa questa. Ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO. Matrice dei tipi ammessi e forma dell''indirizzo libero: i trigger della tabella. Gemella di anagrafiche.fn_crea_indirizzo_soggetto (D-16a). Sede unica della INSERT di SoggettiRepository.crea_indirizzo_ruolo. R-BE-6, D-16a di Tid, brief-db-processi-accensione-per-ambiente §6.16.';
```

</div>

---
{% include-markdown "signature-core.md" %}
