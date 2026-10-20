{% include-markdown "it/dbzero/vendite/manual/fn_accoda_stampe_lotto.md" %}
# ⚙️ Funzione `fn_accoda_stampe_lotto`

```sql
CREATE FUNCTION fn_accoda_stampe_lotto(p_lotto_id bigint, p_tipo_documento_output_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_accoda_stampe_lotto(p_lotto_id bigint, p_tipo_documento_output_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sorgente_tipo_id config.sorgenti.id%TYPE;
    -- tipo esplicito: un conteggio, non una colonna
    v_accodate         integer := 0;
BEGIN
    -- Scopo: accoda un work-item di stampa PENDING per ogni
    --   fattura del lotto; delega numerazione+render al worker.
    --   Idempotente: il vincolo di esclusione scarta le righe vive
    --   che coprono gia' la fattura per quel tipo.
    -- rev 2026-08-04 (D-M): via il predicato su lf.esclusa. Il
    --   flag era dormiente, quindi «ogni fattura non esclusa»
    --   ha sempre voluto dire «ogni fattura».
    -- rev 2026-10-20 (20261020-30): il tipo di documento da
    --   stampare lo dice chi accoda; NULL = decide il DB alla
    --   stampa, se il candidato e' uno.

    -- Guard parametri ID: no NULL, no <= 0 (non normalizzare).
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_accoda_stampe_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;
    IF p_tipo_documento_output_id IS NOT NULL AND p_tipo_documento_output_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_accoda_stampe_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_documento_output_id',
                               'valore', p_tipo_documento_output_id),
            NULL::uuid, 'p_tipo_documento_output_id > 0 se indicato');
    END IF;

    -- Tipo sorgente FATTURA risolto da config (no hardcode dell'id).
    SELECT s.id INTO v_sorgente_tipo_id
      FROM config.sorgenti s
     WHERE s.codice_interno = 'FATTURA';

    IF v_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_accoda_stampe_lotto', 'E_VALORE_MANCANTE',
            jsonb_build_object('sorgente', 'FATTURA'),
            NULL::uuid, 'config.sorgenti FATTURA assente');
    END IF;

    -- Accoda le fatture del lotto.
    -- sorgente_uid = id::text (key_selector FATTURA).
    -- ON CONFLICT senza bersaglio: ex_fatture_stampa_coda_vivo e'
    -- un vincolo di esclusione, e l'unico altro vincolo e' la PK.
    INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, lotto_id,
         tipo_documento_output_id)
    SELECT v_sorgente_tipo_id, f.id, f.id::text, p_lotto_id,
           p_tipo_documento_output_id
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
    ON CONFLICT DO NOTHING;

    GET DIAGNOSTICS v_accodate = ROW_COUNT;
    RETURN v_accodate;
END;
$function$

COMMENT ON FUNCTION vendite.fn_accoda_stampe_lotto(p_lotto_id bigint, p_tipo_documento_output_id bigint)
IS 'Accoda in vendite.fatture_stampa_coda un work-item PENDING per ogni fattura del lotto (sorgente FATTURA, sorgente_uid=id::text), col tipo di documento da stampare p_tipo_documento_output_id (NULL = decide il DB alla stampa, se fra i modelli che possono stampare ce n''e'' uno solo). Idempotente via il vincolo di esclusione ex_fatture_stampa_coda_vivo (ON CONFLICT DO NOTHING): una riga viva per (fattura, tipo), e una riga col tipo NULL esclude le altre righe vive della stessa fattura. Ritorna il numero di righe effettivamente accodate. Chiamata dal task pipeline stampa_documenti_lotto; numerazione (backstop) e render vivono nel worker drainer. Brief: brief-db-processi-fatturazione-cockpit §4; rev 2026-08-04 (D-M): via il predicato su lf.esclusa; rev 2026-10-20 (brief-db-modelli-documento-standard §9): il parametro del tipo.';
```

---
{% include-markdown "signature-core.md" %}
