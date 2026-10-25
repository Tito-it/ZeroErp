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
    v_chi     text := 'anagrafiche.fn_get_or_create_indirizzo_dettaglio';
    v_id      anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_attivo  anagrafiche.indirizzi_dettaglio.attivo%TYPE;
    -- record: gli OUT di fn_build_indirizzo_normalizzato, ancorati
    -- li' alle colonne di indirizzi_dettaglio
    v_k       record;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Trova o crea l'indirizzo dettaglio (una riga per
    --   indirizzo fisico) e ne restituisce l'id, mai NULL.
    --
    -- Regole:
    --   - p_stradario_id obbligatorio, > 0, esistente;
    --   - la chiave sono i valori COME LI SALVA il trigger
    --     (fn_build_indirizzo_normalizzato); via non risolta:
    --     errore, non una ricerca a vuoto;
    --   - lookup IS NOT DISTINCT FROM, allineato a
    --     uq_indirizzi_dettaglio_norm_v2 (NULLS NOT DISTINCT);
    --   - riga trovata ma disattivata: si riattiva;
    --   - corsa concorrente: unique_violation -> ri-lettura.
    -- =========================================================

    -- Guard: p_stradario_id obbligatorio
    IF p_stradario_id IS NULL OR p_stradario_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi,
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_stradario_id',
                               'valore', p_stradario_id),
            NULL::uuid,
            'p_stradario_id obbligatorio e deve essere > 0.'
        );
    END IF;

    -- Guard: lo stradario esiste
    IF NOT EXISTS (
        SELECT 1 FROM config.stradario WHERE id = p_stradario_id
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi,
            'E_CODICE',
            jsonb_build_object('stradario_id', p_stradario_id),
            NULL::uuid,
            p_stradario_id::text, 'config.stradario'
        );
    END IF;

    -- D1: la chiave come la salva il trigger
    SELECT * INTO v_k
      FROM anagrafiche.fn_build_indirizzo_normalizzato(
          p_stradario_id, p_civico, p_estensione_civico,
          p_palazzina, p_scala, p_piano, p_interno);

    -- D4: via non risolta -> tutti gli o_* sono NULL, e la
    --     ricerca troverebbe la riga SNC nuda della via
    IF v_k.o_via_norm IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi,
            'E_INDIRIZZO_VIA_NON_RISOLTA',
            jsonb_build_object('campo', 'stradario_id',
                               'stradario_id', p_stradario_id),
            NULL::uuid,
            p_stradario_id::text
        );
    END IF;

    -- Ricerca per chiave naturale.
    -- NOTA: la stessa query e' ripetuta nel blocco EXCEPTION WHEN
    -- unique_violation (pattern SELECT -> INSERT -> ri-SELECT,
    -- scelto il 2026-03-13). Se la chiave cambia, si aggiornano
    -- entrambe, insieme all'indice.
    SELECT d.id, d.attivo
      INTO v_id, v_attivo
      FROM anagrafiche.indirizzi_dettaglio d
     WHERE d.stradario_id = p_stradario_id
       AND d.civico            IS NOT DISTINCT FROM p_civico
       AND d.estensione_civico IS NOT DISTINCT FROM v_k.o_estensione_civico
       AND d.palazzina         IS NOT DISTINCT FROM v_k.o_palazzina
       AND d.scala             IS NOT DISTINCT FROM v_k.o_scala
       AND d.piano             IS NOT DISTINCT FROM v_k.o_piano
       AND d.interno           IS NOT DISTINCT FROM v_k.o_interno;

    IF v_id IS NULL THEN
        -- Creazione. I trigger calcolano via_norm, civico_norm,
        -- indirizzo_normalizzato, audit, tx_id, e giudicano la
        -- chiave (trgfn_indirizzi_dettaglio_guard_chiave).
        BEGIN
            INSERT INTO anagrafiche.indirizzi_dettaglio (
                stradario_id, civico, estensione_civico,
                palazzina, scala, piano, interno
            )
            VALUES (
                p_stradario_id, p_civico, v_k.o_estensione_civico,
                v_k.o_palazzina, v_k.o_scala, v_k.o_piano, v_k.o_interno
            )
            RETURNING id INTO v_id;

            RETURN v_id;

        EXCEPTION WHEN unique_violation THEN
            -- Corsa concorrente: un'altra sessione ha inserito lo
            -- stesso indirizzo fra la SELECT e l'INSERT. Rileggiamo.
            SELECT d.id, d.attivo
              INTO v_id, v_attivo
              FROM anagrafiche.indirizzi_dettaglio d
             WHERE d.stradario_id = p_stradario_id
               AND d.civico            IS NOT DISTINCT FROM p_civico
               AND d.estensione_civico IS NOT DISTINCT FROM v_k.o_estensione_civico
               AND d.palazzina         IS NOT DISTINCT FROM v_k.o_palazzina
               AND d.scala             IS NOT DISTINCT FROM v_k.o_scala
               AND d.piano             IS NOT DISTINCT FROM v_k.o_piano
               AND d.interno           IS NOT DISTINCT FROM v_k.o_interno;

            IF v_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'database', v_chi,
                    'E_INDIRIZZO_DETTAGLIO_NON_RILETTO',
                    jsonb_build_object('stradario_id', p_stradario_id,
                                       'civico', p_civico,
                                       'estensione_civico', v_k.o_estensione_civico,
                                       'palazzina', v_k.o_palazzina,
                                       'scala', v_k.o_scala,
                                       'piano', v_k.o_piano,
                                       'interno', v_k.o_interno),
                    NULL::uuid,
                    v_k.o_indirizzo_normalizzato
                );
            END IF;
        END;
    END IF;

    -- D5: la riga c'e' ma e' spenta -> torna in uso
    IF NOT v_attivo THEN
        UPDATE anagrafiche.indirizzi_dettaglio
           SET attivo = true
         WHERE id = v_id;
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_or_create_indirizzo_dettaglio(p_stradario_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying)
IS 'Building block: trova o crea l''indirizzo dettaglio (una riga per indirizzo fisico) e ne restituisce l''id, mai NULL. La chiave sono i valori come li salva il trigger (anagrafiche.fn_build_indirizzo_normalizzato), confrontati IS NOT DISTINCT FROM come l''indice uq_indirizzi_dettaglio_norm_v2. Via non risolta in script.vw_indirizzo_completo: E_INDIRIZZO_VIA_NON_RISOLTA. Riga trovata ma disattivata: si riattiva. Corsa concorrente: unique_violation e ri-lettura; ri-lettura vuota: E_INDIRIZZO_DETTAGLIO_NON_RILETTO. Rev 2026-10-25 (20261025-25, brief-db-unicita-civico-indirizzi-dettaglio D1, D4, D5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
