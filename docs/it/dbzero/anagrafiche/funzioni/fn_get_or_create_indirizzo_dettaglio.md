{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_or_create_indirizzo_dettaglio.md" %}
# ⚙️ Funzione `fn_get_or_create_indirizzo_dettaglio`

```sql
CREATE FUNCTION fn_get_or_create_indirizzo_dettaglio(p_stradario_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_or_create_indirizzo_dettaglio(p_stradario_id integer, p_civico integer DEFAULT NULL::integer, p_estensione_civico character varying DEFAULT NULL::character varying, p_palazzina character varying DEFAULT NULL::character varying, p_scala character varying DEFAULT NULL::character varying, p_piano character varying DEFAULT NULL::character varying, p_interno character varying DEFAULT NULL::character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id  anagrafiche.indirizzi_dettaglio.id%TYPE;
BEGIN
    -- Guard: p_stradario_id obbligatorio
    IF p_stradario_id IS NULL OR p_stradario_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_get_or_create_indirizzo_dettaglio',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_stradario_id',
                              'valore', p_stradario_id),
            NULL::uuid,
            'p_stradario_id obbligatorio e deve essere > 0.'
        );
    END IF;

    -- Guard: verificare che lo stradario esista
    IF NOT EXISTS (
        SELECT 1 FROM config.stradario WHERE id = p_stradario_id
    ) THEN
        -- Fix: E_GENERICO → E_CODICE
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_get_or_create_indirizzo_dettaglio',
            'E_CODICE',
            jsonb_build_object('stradario_id', p_stradario_id),
            NULL::uuid,
            p_stradario_id::text, 'config.stradario'
        );
    END IF;

    -- Ricerca per chiave naturale
    -- Allineata al vincolo uq_indirizzi_dettaglio_norm
    SELECT id INTO v_id
    FROM anagrafiche.indirizzi_dettaglio
    WHERE stradario_id = p_stradario_id
      AND civico IS NOT DISTINCT FROM p_civico
      AND COALESCE(estensione_civico, '') = COALESCE(p_estensione_civico, '')
      AND COALESCE(palazzina, '')         = COALESCE(p_palazzina, '')
      AND COALESCE(scala, '')             = COALESCE(p_scala, '')
      AND COALESCE(piano, '')             = COALESCE(p_piano, '')
      AND COALESCE(interno, '')           = COALESCE(p_interno, '');

    IF v_id IS NOT NULL THEN
        -- Civico gia' esistente: restituisce id
        RETURN v_id;
    END IF;

    -- Creazione nuovo civico
    -- I trigger calcolano: via_norm, civico_norm,
    -- indirizzo_normalizzato, audit, tx_id
    --
    -- NOTA: la query di ricerca per chiave naturale e' volutamente
    -- duplicata nel blocco EXCEPTION WHEN unique_violation.
    -- Scelta progettuale: il pattern SELECT → INSERT → ri-SELECT
    -- e' piu' leggibile e manutenibile rispetto a INSERT ON CONFLICT
    -- DO NOTHING + fallback, e il caso race condition e' raro.
    -- Se la chiave naturale cambia, aggiornare entrambe le SELECT.
    BEGIN
        INSERT INTO anagrafiche.indirizzi_dettaglio (
            stradario_id, civico, estensione_civico,
            palazzina, scala, piano, interno
        )
        VALUES (
            p_stradario_id, p_civico, p_estensione_civico,
            p_palazzina, p_scala, p_piano, p_interno
        )
        RETURNING id INTO v_id;

        RETURN v_id;

    EXCEPTION WHEN unique_violation THEN
        -- Race condition: un'altra sessione ha inserito lo stesso
        -- civico tra la SELECT e l'INSERT. Rileggiamo.
        SELECT id INTO v_id
        FROM anagrafiche.indirizzi_dettaglio
        WHERE stradario_id = p_stradario_id
          AND civico IS NOT DISTINCT FROM p_civico
          AND COALESCE(estensione_civico, '') = COALESCE(p_estensione_civico, '')
          AND COALESCE(palazzina, '')         = COALESCE(p_palazzina, '')
          AND COALESCE(scala, '')             = COALESCE(p_scala, '')
          AND COALESCE(piano, '')             = COALESCE(p_piano, '')
          AND COALESCE(interno, '')           = COALESCE(p_interno, '');

        RETURN v_id;
    END;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_or_create_indirizzo_dettaglio(p_stradario_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying)
IS 'Building block: upsert indirizzo dettaglio (civico). Cerca per chiave naturale, crea se non esiste. Gestisce race condition. Riusabile da orchestratori.';
```

</div>

---
{% include-markdown "signature-core.md" %}
