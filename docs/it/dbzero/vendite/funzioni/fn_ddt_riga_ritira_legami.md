# ⚙️ Funzione `fn_ddt_riga_ritira_legami`

```sql
CREATE FUNCTION fn_ddt_riga_ritira_legami(p_ddt_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_riga_ritira_legami(p_ddt_riga_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: ritirare i legami di UNA riga di DDT con la sua origine
--   (fulfillment verso la riga d'ordine, ponte di ri-consegna verso
--   la riga di reso) e riproiettare gli ordini toccati
--   (vendite.fn_ordine_proietta_stato_evasione). Il reso non ha uno
--   stato da riproiettare: la sua copertura si ricalcola.
--   La porta del guard del legame (GUC zeroerp.ddt_riga_ritira_legame =
--   id della riga) si apre qui e si richiude subito. Il guard la onora
--   solo con la bolla in bozza, o dentro l'annullo (seconda porta,
--   zeroerp.ddt_annullo, aperta dal verbo vendite.fn_annulla_ddt).
-- Ritorna: quanti legami ha ritirato (un CONTEGGIO: tipo nudo).
-- Consumatori: vendite.trgfn_dlt_block_ordrig_ddtrig (la riga si toglie
--   in bozza, D-3) e vendite.fn_annulla_ddt (la bolla si annulla, D-8).
-- Brief: brief-db-ddt-righe-evase-dall-ordine (D-3, D-7, D-8).
-- =========================================================
DECLARE
    -- bigint[] esplicito: `colonna%TYPE[]` non esiste.
    v_ordini    bigint[];
    v_ordine_id vendite.ordini.id%TYPE;
    v_n_ful     integer;
    v_n_ric     integer;
BEGIN
    IF p_ddt_riga_id IS NULL OR p_ddt_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_ddt_riga_ritira_legami',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_ddt_riga_id', p_ddt_riga_id),
            NULL::uuid, 'vendite.fn_ddt_riga_ritira_legami',
            'p_ddt_riga_id (obbligatorio, maggiore di zero)');
    END IF;

    PERFORM set_config('zeroerp.ddt_riga_ritira_legame', p_ddt_riga_id::text, true);

    WITH ritirati AS (
        DELETE FROM vendite.ordini_righe_fulfillment f
         WHERE f.ddt_riga_id = p_ddt_riga_id
        RETURNING f.ordine_riga_id
    )
    SELECT array_agg(DISTINCT orr.ordine_id), count(*)
      INTO v_ordini, v_n_ful
      FROM ritirati r
      JOIN vendite.ordini_righe orr ON orr.id = r.ordine_riga_id;

    DELETE FROM vendite.resi_righe_riconsegne rr
     WHERE rr.ddt_riga_id = p_ddt_riga_id;
    GET DIAGNOSTICS v_n_ric = ROW_COUNT;

    PERFORM set_config('zeroerp.ddt_riga_ritira_legame', '', true);

    -- Il residuo torna all'ordine: lo stato si riproietta.
    IF v_ordini IS NOT NULL THEN
        FOREACH v_ordine_id IN ARRAY v_ordini LOOP
            PERFORM vendite.fn_ordine_proietta_stato_evasione(v_ordine_id);
        END LOOP;
    END IF;

    RETURN COALESCE(v_n_ful, 0) + v_n_ric;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_riga_ritira_legami(p_ddt_riga_id bigint)
IS 'Building block (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-3, D-7, D-8): ritira i legami di UNA riga di DDT con la sua origine — fulfillment (riga d''ordine) e ponte di ri-consegna (riga di reso) — e riproietta gli ordini toccati con vendite.fn_ordine_proietta_stato_evasione (il residuo torna all''ordine; ultimo legame -> CONFERMATO). Il reso non ha stato da riproiettare: la sua copertura da ri-consegnare si ricalcola. Apre e richiude la porta del guard del legame (GUC transazionale zeroerp.ddt_riga_ritira_legame = id della riga): il guard la onora solo con la bolla in bozza, o dentro l''annullo (porta zeroerp.ddt_annullo del verbo vendite.fn_annulla_ddt, dal proprietario). Ritorna quanti legami ha ritirato. Consumatori: vendite.trgfn_dlt_block_ordrig_ddtrig (riga tolta in bozza) e vendite.fn_annulla_ddt (bolla annullata). Parametro non valido: E_VENDITE_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
