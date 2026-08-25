{% include-markdown "it/dbzero/vendite/manual/fn_get_data_minima_numerabile_lotto.md" %}
# ⚙️ Funzione `fn_get_data_minima_numerabile_lotto`

```sql
CREATE FUNCTION fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_pavimento vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Da quale data in poi TUTTE le fatture non ancora
    --   numerate di questo lotto possono prendere un numero.
    --
    -- Regole:
    --   - un lotto puo' toccare piu' sezionali (la nota di
    --     credito ha un registro suo): si prende il MASSIMO dei
    --     loro pavimenti, cioe' il piu' restrittivo;
    --   - solo le fatture SENZA numero: quelle numerate non
    --     hanno piu' niente da chiedere.
    -- =========================================================

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_data_minima_numerabile_lotto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'lotto_id obbligatorio e maggiore di zero',
                'p_lotto_id', p_lotto_id),
            NULL::uuid,
            'vendite.fn_get_data_minima_numerabile_lotto',
            'p_lotto_id (obbligatorio, maggiore di zero)');
    END IF;

    -- ⚠️ Il lotto ha la RLS: qui «non trovato» comprende «non
    --    visibile», ed e' giusto che le due risposte coincidano.
    --    Serve a distinguere «lotto che non c'e'» da «lotto senza
    --    pavimento», che tornerebbero entrambi NULL.
    PERFORM 1 FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_data_minima_numerabile_lotto',
            'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- ⭐ Set-based: un JOIN sul contatore, non una chiamata alla
    --    sorella per ogni fattura. Un lotto massivo ne ha molte e
    --    la risposta e' identica.
    -- ⭐ La serie si risolve come la risolve chi numera.
    SELECT max(rp.ultima_data)
      INTO v_pavimento
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f
        ON f.id = lf.fattura_id
      JOIN vendite.registri_fatturazione r
        ON r.id = f.registro_id
      JOIN vendite.registri_fatturazione_progressivi rp
        ON rp.registro_id = f.registro_id
       AND rp.serie       = COALESCE(f.serie, r.serie_default, '')
     WHERE lf.lotto_id = p_lotto_id
       AND f.numero IS NULL;

    RETURN v_pavimento;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)
IS 'Da quale data in poi TUTTE le fatture non ancora numerate di questo lotto possono prendere un numero: il MASSIMO dei pavimenti dei sezionali che il lotto tocca, cioe'' il piu'' restrittivo. ⭐ Un lotto puo'' contenere documenti di registri diversi — la natura instrada la nota di credito su un registro suo — quindi una risposta sola deve valere per tutti. ℹ️ Solo le fatture SENZA numero: quelle gia'' numerate non hanno piu'' niente da chiedere. NULL = nessun pavimento. ⚠️ FAIL-OPEN sotto RLS, e va saputo: vendite.fatture ha le policy e questa funzione e'' SECURITY INVOKER, quindi una fattura del lotto non visibile a chi opera non entra nell''aggregazione e il minimo esce PIU'' BASSO del vero. E'' accettabile solo perche'' questa e'' una TARGA e non un lucchetto — il cancello vero, in fn_get_next_progressivo, legge il contatore, che la RLS non ha. ⛔ Chi volesse usare questa funzione AL POSTO del cancello sappia che sta sostituendo un presidio con un suggerimento. ⚠️ Il lotto inesistente e il lotto non visibile danno la stessa risposta (E_LOTTO_NON_TROVATO), e il guard c''e'' per distinguerli da «lotto senza pavimento», che tornerebbe NULL come loro. ⭐ Set-based: un JOIN sul contatore, non una chiamata per fattura. Brief: docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md §4 DB-10.';
```

---
{% include-markdown "signature-core.md" %}
