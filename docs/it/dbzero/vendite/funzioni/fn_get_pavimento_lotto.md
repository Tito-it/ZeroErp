{% include-markdown "it/dbzero/vendite/manual/fn_get_pavimento_lotto.md" %}
# ⚙️ Funzione `fn_get_pavimento_lotto`

```sql
CREATE FUNCTION fn_get_pavimento_lotto(p_lotto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_pavimento_lotto(p_lotto_id bigint)
 RETURNS TABLE(pavimento date, origine text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_pavimento vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    v_origine   text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Da quale data in poi TUTTE le fatture non ancora
    --   numerate di questo lotto possono prendere un numero, e
    --   QUALE pavimento ha deciso.
    --
    -- Regole:
    --   - un lotto puo' toccare piu' sezionali: si prende il
    --     MASSIMO dei loro pavimenti, cioe' il piu' restrittivo;
    --   - solo le fatture SENZA numero: quelle numerate non hanno
    --     piu' niente da chiedere;
    --   - a parita' di data vince SEQUENZA, perche' la sua frase
    --     puo' portare un bersaglio.
    -- =========================================================

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_pavimento_lotto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'lotto_id obbligatorio e maggiore di zero',
                'p_lotto_id', p_lotto_id),
            NULL::uuid,
            'vendite.fn_get_pavimento_lotto',
            'p_lotto_id (obbligatorio, maggiore di zero)');
    END IF;

    -- ⚠️ Il lotto ha la RLS: qui «non trovato» comprende «non
    --    visibile», ed e' giusto che le due risposte coincidano.
    --    Serve a distinguere «lotto che non c'e'» da «lotto senza
    --    pavimento», che tornerebbero entrambi NULL.
    PERFORM 1 FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_pavimento_lotto',
            'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- ⭐ SET-BASED SUI SEZIONALI DISTINTI, non per fattura: la
    --    composizione dipende da (registro, serie, competenza), e
    --    un lotto massivo ha molte fatture e pochi sezionali.
    -- ⭐ La serie si risolve come la risolve chi numera.
    -- ⚠️ La competenza e' quella DELLA FATTURA, con ripiego su
    --    quella del lotto: dal 2026-08-26 e' una proprieta' del
    --    documento, e le fatture nate prima possono averla a NULL.
    WITH sezionali AS (
        SELECT DISTINCT
               f.registro_id                                   AS registro_id,
               COALESCE(f.serie, r.serie_default, '')          AS serie,
               COALESCE(f.competenza_mese, fl.competenza_mese) AS competenza
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture f
            ON f.id = lf.fattura_id
          JOIN vendite.registri_fatturazione r
            ON r.id = f.registro_id
          JOIN vendite.fatturazione_lotti fl
            ON fl.id = lf.lotto_id
         WHERE lf.lotto_id = p_lotto_id
           AND f.numero IS NULL
    ),
    pavimenti AS (
        SELECT pv.pavimento AS pav,
               pv.origine   AS org
          FROM sezionali s
          CROSS JOIN LATERAL vendite.fn_get_pavimento_data_documento(
                     s.registro_id, s.serie, s.competenza) pv
         WHERE pv.pavimento IS NOT NULL
    )
    SELECT p.pav, p.org
      INTO v_pavimento, v_origine
      FROM pavimenti p
     -- ⚠️ Il piu' RESTRITTIVO fra i sezionali toccati, e a parita'
     --    di data vince SEQUENZA: stessa regola della sede
     --    composta, applicata qui fra sezionali diversi.
     ORDER BY p.pav DESC, (p.org = 'SEQUENZA') DESC
     LIMIT 1;

    -- ℹ️ Zero righe = nessun pavimento, e il SELECT INTO ha gia'
    --    azzerato le due variabili. Qui e' il comportamento
    --    voluto; altrove la stessa proprieta' e' una trappola.
    RETURN QUERY SELECT v_pavimento, v_origine;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_pavimento_lotto(p_lotto_id bigint)
IS 'Da quale data in poi TUTTE le fatture non ancora numerate di questo lotto possono prendere un numero, e QUALE pavimento ha deciso: il MASSIMO fra i pavimenti composti dei sezionali che il lotto tocca, cioe'' il piu'' restrittivo. ⭐ Un lotto puo'' contenere documenti di registri diversi — la natura instrada la nota di credito su un registro suo — quindi una risposta sola deve valere per tutti. ⛔ NON E'' PIU'' UN max(ultima_data): il pavimento si compone PER FATTURA (registro e serie del documento, competenza sua o del lotto) via vendite.fn_get_pavimento_data_documento, perche'' i registri hanno limiti di emissione diversi e un max sul solo contatore li ignorerebbe del tutto. ⭐ E resta SET-BASED: la composizione gira una volta per SEZIONALE DISTINTO e non per fattura — un lotto massivo ha molte fatture e pochi sezionali. ⚠️ La competenza si legge dalla FATTURA con ripiego su quella del lotto: dal 2026-08-26 e'' una proprieta'' del documento, e le fatture nate prima possono averla a NULL. ⚠️ A PARITA'' DI DATA VINCE SEQUENZA, come nella sede composta: la sua frase puo'' portare un bersaglio, quella del limite di emissione no. ℹ️ Solo le fatture SENZA numero: quelle gia'' numerate non hanno piu'' niente da chiedere. ℹ️ Torna SEMPRE una riga, mai zero: se nessun sezionale produce un pavimento, il SELECT INTO azzera le variabili e la risposta e'' (NULL, NULL) — «nessun vincolo». Chi chiama non deve distinguere «nessun vincolo» da «nessuna risposta». ⚠️ FAIL-OPEN sotto RLS, e va saputo: vendite.fatture ha le policy e questa funzione e'' SECURITY INVOKER, quindi una fattura del lotto non visibile a chi opera non entra nell''aggregazione e il pavimento esce PIU'' BASSO del vero. E'' accettabile solo perche'' questa e'' una TARGA e non un lucchetto — il cancello vero, in fn_get_next_progressivo, legge il contatore, che la RLS non ha. ⛔ Chi volesse usarla AL POSTO del cancello sappia che sta sostituendo un presidio con un suggerimento. ⚠️ Il lotto inesistente e il lotto non visibile danno la stessa risposta (E_LOTTO_NON_TROVATO), e il guard c''e'' per distinguerli da «lotto senza pavimento», che tornerebbe NULL come loro. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
