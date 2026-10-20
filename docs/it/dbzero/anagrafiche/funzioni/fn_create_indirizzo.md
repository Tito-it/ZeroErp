{% include-markdown "it/dbzero/anagrafiche/manual/fn_create_indirizzo.md" %}
# ⚙️ Funzione `fn_create_indirizzo`

```sql
CREATE FUNCTION fn_create_indirizzo(p_stradario_id integer, p_toponomastica_id integer, p_descrizione_via character varying, p_comune_id integer, p_codice_postale_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_create_indirizzo(p_stradario_id integer DEFAULT NULL::integer, p_toponomastica_id integer DEFAULT NULL::integer, p_descrizione_via character varying DEFAULT NULL::character varying, p_comune_id integer DEFAULT NULL::integer, p_codice_postale_id integer DEFAULT NULL::integer, p_civico integer DEFAULT NULL::integer, p_estensione_civico character varying DEFAULT NULL::character varying, p_palazzina character varying DEFAULT NULL::character varying, p_scala character varying DEFAULT NULL::character varying, p_piano character varying DEFAULT NULL::character varying, p_interno character varying DEFAULT NULL::character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stradario_gen_id config.stradario_generale.id%TYPE;
    v_stradario_id     config.stradario.id%TYPE := p_stradario_id;
    v_descrizione_via  config.stradario_generale.descrizione%TYPE;
    v_indirizzo_id     bigint;
BEGIN
    -- ----------------------------------------------------
    -- 1) Ramo "via nuova": upsert stradario_generale + stradario
    --    (idempotenti), solo se non e' stato passato uno
    --    stradario_id gia' risolto.
    -- ----------------------------------------------------
    IF v_stradario_id IS NULL THEN
        v_descrizione_via := btrim(p_descrizione_via);

        INSERT INTO config.stradario_generale (
            toponomastica_id, descrizione, descrizione_breve)
        VALUES (p_toponomastica_id, v_descrizione_via, v_descrizione_via)
        ON CONFLICT (toponomastica_id, descrizione) DO UPDATE
           SET descrizione = EXCLUDED.descrizione
        RETURNING id INTO v_stradario_gen_id;

        INSERT INTO config.stradario (
            stradario_generale_id, comune_id, codice_postale_id)
        VALUES (v_stradario_gen_id, p_comune_id, p_codice_postale_id)
        ON CONFLICT (comune_id, stradario_generale_id, codice_postale_id) DO UPDATE
           SET comune_id = EXCLUDED.comune_id
        RETURNING id INTO v_stradario_id;
    END IF;

    -- ----------------------------------------------------
    -- 2) Dettaglio civico (figlia DB idempotente).
    -- ----------------------------------------------------
    v_indirizzo_id := anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        v_stradario_id, p_civico, p_estensione_civico,
        p_palazzina, p_scala, p_piano, p_interno);

    RETURN v_indirizzo_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_create_indirizzo(p_stradario_id integer, p_toponomastica_id integer, p_descrizione_via character varying, p_comune_id integer, p_codice_postale_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying)
IS 'Funzione madre atomica: risolve/crea lo stradario (upsert generale + civico-strada) e l''indirizzo di dettaglio in un''unica statement (o tutto o rollback). SECURITY INVOKER. Le validazioni via-nuova restano pre-check del service. Piano: analisi-fix-transazioni Classe D #13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
