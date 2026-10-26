{% include-markdown "it/dbzero/vendite/manual/fn_offerta_proietta_stato_revisione.md" %}
# ⚙️ Funzione `fn_offerta_proietta_stato_revisione`

```sql
CREATE FUNCTION fn_offerta_proietta_stato_revisione(p_offerta_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_proietta_stato_revisione(p_offerta_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: portare un'offerta nello stato che le sue revisioni
--   vive dicono.
--   revisione viva, non superata      -> superamento;
--   nessuna revisione viva, superata  -> emissione;
--   ogni altro caso                   -> niente.
--   La transizione passa dalla matrice
--   (trgfn_offerte_commerciali_guard_transizione).
-- Consumatori: vendite.trgfn_offerte_commerciali_revisione
--   (nascita di una revisione), vendite.trgfn_offerte_
--   commerciali_rientro_padre (annullo di una revisione).
-- Brief: brief-modello-documento-vendita §13 (O-2).
-- =========================================================
DECLARE
    v_superato     config.stati_doc_offerte.is_superato%TYPE;
    v_target_id    config.stati_doc_offerte.id%TYPE;
    -- Esito di un predicato e un conteggio: nessuna colonna
    -- da ancorare.
    v_viva         boolean;
    v_n_stati      integer;
BEGIN
    IF p_offerta_id IS NULL OR p_offerta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_offerta_proietta_stato_revisione',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_offerta_id', p_offerta_id),
            NULL::uuid, 'vendite.fn_offerta_proietta_stato_revisione',
            'p_offerta_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Lo stato di oggi. Offerta assente: niente.
    SELECT s.is_superato
      INTO v_superato
      FROM vendite.offerte_commerciali o
      JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
     WHERE o.id = p_offerta_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Una revisione viva: una figlia il cui stato non e'
    -- d'annullo (una revisione abortita non rimpiazza nessuno).
    v_viva := EXISTS (
        SELECT 1
          FROM vendite.offerte_commerciali f
          JOIN config.stati_doc_offerte sf ON sf.id = f.stato_doc_offerta_id
         WHERE f.revisione_padre_id = p_offerta_id
           AND sf.is_abortito IS FALSE);

    IF v_viva AND NOT COALESCE(v_superato, false) THEN
        -- ⛔ Guard sull'ARITA' (dal trigger della revisione,
        --   20260828-11): zero righe e due righe sono lo stesso
        --   difetto, il catalogo non dice quale.
        SELECT count(*), min(s.id)
          INTO v_n_stati, v_target_id
          FROM config.stati_doc_offerte s
         WHERE s.is_superato IS TRUE
           AND s.attivo      IS TRUE;

        IF v_n_stati <> 1 THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.fn_offerta_proietta_stato_revisione',
                'E_CONFIG_MANCANTE',
                jsonb_build_object('tabella', 'config.stati_doc_offerte',
                                   'colonna', 'is_superato',
                                   'attesi',  1,
                                   'trovati', v_n_stati),
                NULL::uuid,
                'config.stati_doc_offerte: atteso esattamente uno stato attivo '
                || 'con is_superato = true, trovati ' || v_n_stati::text);
        END IF;

    ELSIF NOT v_viva AND COALESCE(v_superato, false) THEN
        -- Lo stato da cui una revisione nasce: quello
        -- d'emissione, dal vocabolario (vendite.fn_crea_
        -- revisione_offerta revisiona solo un'offerta emessa).
        v_target_id := script.fn_stato_emissione_id('vendite.offerte_commerciali'::regclass);

        IF v_target_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.fn_offerta_proietta_stato_revisione',
                'E_CONFIG_MANCANTE',
                jsonb_build_object('tabella', 'config.stati_doc_offerte',
                                   'colonna', 'emissione',
                                   'attesi',  1,
                                   'trovati', 0),
                NULL::uuid,
                'config.stati_doc_offerte: nessuno stato con emissione = true '
                || 'per il rientro del padre');
        END IF;

    ELSE
        RETURN;
    END IF;

    -- Il target e' sempre diverso dallo stato di oggi (rami
    -- sopra). La matrice e il rientro senza figlie vive li
    -- giudica il guard di transizione, all'UPDATE.
    PERFORM script.fn_doc_scrivi_stato('vendite.offerte_commerciali'::regclass,
                                       p_offerta_id, v_target_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_proietta_stato_revisione(p_offerta_id bigint)
IS 'BB dei passaggi di PROCESSO dell''offerta (manuale = false), brief-modello-documento-vendita §13 (O-2, Tid 2026-10-26): porta un''offerta nello stato che le sue revisioni vive (figlie non abortite) dicono. Una revisione viva e l''offerta non superata: lo stato di superamento (is_superato, guard sull''arita'': E_CONFIG_MANCANTE). Nessuna revisione viva e l''offerta superata: lo stato di emissione (script.fn_stato_emissione_id; prima il letterale ''EMESSA''). Altrimenti niente. Scrive con script.fn_doc_scrivi_stato attraverso la porta; la matrice e la regola «nessun rientro con una figlia viva» (E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA) le giudica il guard di transizione. La chiamano i trigger _z90_ della testata: vendite.trgfn_offerte_commerciali_revisione (nascita di una revisione) e vendite.trgfn_offerte_commerciali_rientro_padre (annullo di una revisione). SECURITY DEFINER (la porta vuole il proprietario; lo stato e'' la conseguenza delle revisioni, non di cio'' che vede chi chiama); EXECUTE all''applicazione, perche'' i trigger girano come chi scrive. Gemella di vendite.fn_preventivo_proietta_stato_smistamento e vendite.fn_ordine_proietta_stato_evasione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
