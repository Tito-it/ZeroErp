{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto.md" %}
# ⚙️ Funzione `fn_crea_indirizzo_soggetto`

```sql
CREATE FUNCTION fn_crea_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi CONSTANT text := 'anagrafiche.fn_crea_indirizzo_soggetto';
    v_el  jsonb;
    v_id  anagrafiche.indirizzi_soggetti.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere un indirizzo di un soggetto. p_indirizzo e' un
    --   oggetto col tipo (tipo_indirizzo_id o
    --   tipo_indirizzo_codice) e l'indirizzo in una di tre
    --   forme: libero (indirizzo_libero, stato, poi comune e CAP
    --   del catalogo oppure locality e postal_code), dettaglio
    --   gia' risolto (indirizzo_dettaglio_id), via da risolvere.
    --   Ritorna l'id della riga.
    --
    -- Regole:
    --   - la grammatica e la via sono dei BB fn_indirizzo_elemento
    --     e fn_indirizzo_elemento_dettaglio, comuni con
    --     fn_crea_indirizzi_ruolo;
    --   - la completezza e la forma le dice il guard della
    --     tabella (trgfn_indirizzi_guard_forma_libera); il tipo
    --     ammesso, trgfn_indirizzi_soggetti_guard_tipo_indirizzo;
    --     un tipo gia' presente, uq_indirizzi_soggetti_soggetto_tipo.
    -- =========================================================
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid,
            c_chi,
            'manca il soggetto');
    END IF;

    v_el := anagrafiche.fn_indirizzo_elemento(
                p_indirizzo, c_chi,
                jsonb_build_object('soggetto_id', p_soggetto_id));

    INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id,
        indirizzo_dettaglio_id, indirizzo_libero,
        stato_id, comune_id, codice_postale_id,
        administrative_area, locality, sublocality, postal_code)
    VALUES (
        p_soggetto_id, (v_el ->> 'tipo_indirizzo_id')::integer,
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

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo jsonb)
IS 'Madre: scrive un indirizzo di un soggetto (anagrafiche.indirizzi_soggetti). p_indirizzo: un oggetto col tipo (tipo_indirizzo_id o tipo_indirizzo_codice, codice interno) e l''indirizzo in una di tre forme: libero (indirizzo_libero con stato, poi comune e CAP del catalogo oppure locality e postal_code), dettaglio gia'' risolto (indirizzo_dettaglio_id), via da risolvere (stradario_id oppure toponomastica_id + descrizione_via + comune_id + codice_postale_id, piu'' il civico). Ritorna l''id della riga. Grammatica e via dai BB anagrafiche.fn_indirizzo_elemento e fn_indirizzo_elemento_dettaglio, gli stessi di fn_crea_indirizzi_ruolo. Rifiuti: soggetto mancante E_SCRIPT_CHIAMATA_NON_VALIDA, poi quelli del BB (E_SCRIPT_CHIAMATA_NON_VALIDA, E_CAMPO_NON_AMMESSO, E_TIPO_INDIRIZZO_NON_TROVATO); forma e completezza dal guard anagrafiche.trgfn_indirizzi_guard_forma_libera, tipo ammesso da trgfn_indirizzi_soggetti_guard_tipo_indirizzo, tipo gia'' presente da uq_indirizzi_soggetti_soggetto_tipo. INVOKER. Rev 2026-10-18 (D-4 di Tid): fino ad allora la firma era posizionale (sette parametri), senza i campi della forma estera, e pretendeva comune e CAP per ogni indirizzo libero. Richiesta BE in brief-db-processi-accensione-per-ambiente §6.11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
