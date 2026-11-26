{% include-markdown "it/dbzero/anagrafiche/manual/fn_create_indirizzo.md" %}
# ⚙️ Funzione `fn_create_indirizzo`

```sql
CREATE FUNCTION fn_create_indirizzo(p_stradario_id integer, p_toponomastica_id integer, p_descrizione_via character varying, p_comune_id integer, p_codice_postale_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_create_indirizzo(p_stradario_id integer DEFAULT NULL::integer, p_toponomastica_id integer DEFAULT NULL::integer, p_descrizione_via character varying DEFAULT NULL::character varying, p_comune_id integer DEFAULT NULL::integer, p_codice_postale_id integer DEFAULT NULL::integer, p_civico integer DEFAULT NULL::integer, p_estensione_civico character varying DEFAULT NULL::character varying, p_palazzina character varying DEFAULT NULL::character varying, p_scala character varying DEFAULT NULL::character varying, p_piano character varying DEFAULT NULL::character varying, p_interno character varying DEFAULT NULL::character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi              CONSTANT text := 'anagrafiche.fn_create_indirizzo';
    v_stradario_gen_id config.stradario_generale.id%TYPE;
    v_stradario_id     config.stradario.id%TYPE := p_stradario_id;
    v_descrizione_via  config.stradario_generale.descrizione%TYPE;
    v_campo            text;   -- la colonna che manca
    v_cosa             text;   -- la stessa, come la legge una persona
    v_indirizzo_id     anagrafiche.indirizzi_dettaglio.id%TYPE;
BEGIN
    -- ----------------------------------------------------
    -- 1) Ramo "via nuova", solo se non e' stato passato uno
    --    stradario_id gia' risolto: si valida, si cerca, e si
    --    scrive solo cio' che manca.
    -- ----------------------------------------------------
    IF v_stradario_id IS NULL THEN
        v_descrizione_via := NULLIF(btrim(p_descrizione_via), '');

        -- D-T7a-5: la via nuova la valida il DB, col campo.
        IF p_toponomastica_id IS NULL THEN
            v_campo := 'toponomastica_id';  v_cosa := 'il tipo di toponimo (via, piazza…)';
        ELSIF v_descrizione_via IS NULL THEN
            v_campo := 'descrizione_via';   v_cosa := 'il nome della via';
        ELSIF p_comune_id IS NULL THEN
            v_campo := 'comune_id';         v_cosa := 'il comune';
        ELSIF p_codice_postale_id IS NULL THEN
            v_campo := 'codice_postale_id'; v_cosa := 'il CAP';
        END IF;

        IF v_campo IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', c_chi, 'E_INDIRIZZO_VIA_NUOVA_INCOMPLETA',
                jsonb_build_object(
                    'campo',             v_campo,
                    'toponomastica_id',  p_toponomastica_id,
                    'descrizione_via',   p_descrizione_via,
                    'comune_id',         p_comune_id,
                    'codice_postale_id', p_codice_postale_id),
                NULL::uuid,
                v_cosa);
        END IF;

        -- S-T7a-a: prima si cerca. Una via che esiste non si
        -- riscrive (lo storico della via e' continuo).
        SELECT g.id INTO v_stradario_gen_id
          FROM config.stradario_generale g
         WHERE g.toponomastica_id = p_toponomastica_id
           AND g.descrizione = v_descrizione_via;

        IF v_stradario_gen_id IS NULL THEN
            INSERT INTO config.stradario_generale (
                toponomastica_id, descrizione, descrizione_breve)
            VALUES (p_toponomastica_id, v_descrizione_via, left(v_descrizione_via, 50))
            ON CONFLICT (toponomastica_id, descrizione) DO NOTHING
            RETURNING id INTO v_stradario_gen_id;

            -- La corsa concorrente: l'ha scritta un'altra sessione.
            IF v_stradario_gen_id IS NULL THEN
                SELECT g.id INTO v_stradario_gen_id
                  FROM config.stradario_generale g
                 WHERE g.toponomastica_id = p_toponomastica_id
                   AND g.descrizione = v_descrizione_via;
            END IF;
        END IF;

        -- La via del comune, fra le vive: la chiave dell'indice
        -- parziale (una via soppressa non si riusa).
        SELECT s.id INTO v_stradario_id
          FROM config.stradario s
         WHERE s.comune_id = p_comune_id
           AND s.stradario_generale_id = v_stradario_gen_id
           AND s.codice_postale_id = p_codice_postale_id
           AND s.obsoleto_dal IS NULL;

        IF v_stradario_id IS NULL THEN
            INSERT INTO config.stradario (
                stradario_generale_id, comune_id, codice_postale_id)
            VALUES (v_stradario_gen_id, p_comune_id, p_codice_postale_id)
            -- L'indice e' parziale: l'ON CONFLICT nomina il predicato.
            ON CONFLICT (comune_id, stradario_generale_id, codice_postale_id)
               WHERE obsoleto_dal IS NULL
            DO NOTHING
            RETURNING id INTO v_stradario_id;

            IF v_stradario_id IS NULL THEN
                SELECT s.id INTO v_stradario_id
                  FROM config.stradario s
                 WHERE s.comune_id = p_comune_id
                   AND s.stradario_generale_id = v_stradario_gen_id
                   AND s.codice_postale_id = p_codice_postale_id
                   AND s.obsoleto_dal IS NULL;
            END IF;
        END IF;
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
IS 'Funzione madre atomica dell''indirizzo: risolve o crea la via (la via generale e la via del comune) e l''indirizzo di dettaglio, in una sola istruzione. Senza stradario_id la via nuova si valida qui: toponomastica, nome, comune e CAP, ciascuno mancante E_INDIRIZZO_VIA_NUOVA_INCOMPLETA col campo. Poi si cerca, e si scrive solo cio'' che manca: una via che esiste non si riscrive (lo storico della via resta senza versioni vuote); la corsa concorrente si chiude con ON CONFLICT DO NOTHING e la rilettura. La via del comune si cerca fra le vive: una via soppressa (config.stradario.obsoleto_dal) non si riusa, e se c''e'' solo lei nasce la via viva. Un indirizzo su una via soppressa passata per id lo rifiuta il guard del ritiro su anagrafiche.indirizzi_dettaglio. Il civico lo trova o lo crea anagrafiche.fn_get_or_create_indirizzo_dettaglio. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
