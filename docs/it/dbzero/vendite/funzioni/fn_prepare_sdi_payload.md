{% include-markdown "it/dbzero/vendite/manual/fn_prepare_sdi_payload.md" %}
# ⚙️ Funzione `fn_prepare_sdi_payload`

```sql
CREATE FUNCTION fn_prepare_sdi_payload(p_lotto_id bigint, p_stato_sdi_codice_interno character varying, p_force_new_tentativo boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_prepare_sdi_payload(p_lotto_id bigint, p_stato_sdi_codice_interno character varying DEFAULT 'DA_INVIARE'::character varying, p_force_new_tentativo boolean DEFAULT false)
 RETURNS TABLE(fattura_sdi_id bigint, fattura_id bigint, tentativo_num smallint, stato_sdi_id bigint, codice_documento text, numero_fattura bigint, data_fattura date, billing_account_id bigint, emittente_soggetto_ruolo_id bigint, valuta_id integer, totale_a_pagare numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_sdi_id config.stati_sdi.id%TYPE;
    v_exists_lotto BOOLEAN := FALSE;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_prepare_sdi_payload', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_stato_sdi_codice_interno IS NULL OR btrim(p_stato_sdi_codice_interno) = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_prepare_sdi_payload', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_stato_sdi_codice_interno', 'valore', p_stato_sdi_codice_interno), NULL::uuid, 'p_stato_sdi_codice_interno obbligatorio');
    END IF;

    SELECT EXISTS (SELECT 1 FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id) INTO v_exists_lotto;

    IF NOT COALESCE(v_exists_lotto, FALSE) THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_prepare_sdi_payload', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    SELECT s.id INTO v_stato_sdi_id
      FROM config.stati_sdi s
     WHERE s.codice_interno = p_stato_sdi_codice_interno AND s.attivo IS TRUE
     ORDER BY s.ordine NULLS LAST, s.id LIMIT 1;

    IF v_stato_sdi_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_prepare_sdi_payload', 'E_CODICE',
            jsonb_build_object('codice_interno', p_stato_sdi_codice_interno), NULL::uuid, p_stato_sdi_codice_interno, 'config.stati_sdi');
    END IF;

    -- Upsert fatture_sdi + RETURN QUERY (logica invariata dall'originale)
    RETURN QUERY
    WITH target_fatture AS (
        -- rev 2026-07-28: si porta dietro anche totale_a_pagare,
        -- letto qui dalla testata invece che ricostruito a valle.
        SELECT f.id AS f_id, f.numero, f.data, f.billing_account_id,
               f.emittente_soggetto_ruolo_id, f.valuta_id,
               f.totale_a_pagare,
               COALESCE(f.anno::text, '') || COALESCE(f.serie, '') || COALESCE(f.numero::text, '') AS codice_doc
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture f ON f.id = lf.fattura_id
         WHERE lf.lotto_id = p_lotto_id AND lf.esclusa IS FALSE
    ), upserted AS (
        INSERT INTO vendite.fatture_sdi (fattura_id, tentativo, stato_sdi_id, meta)
        SELECT tf.f_id,
               COALESCE((SELECT MAX(fs2.tentativo) FROM vendite.fatture_sdi fs2 WHERE fs2.fattura_id = tf.f_id), 0)
                 + CASE WHEN p_force_new_tentativo THEN 1 ELSE 0 END,
               v_stato_sdi_id, '{}'::jsonb
          FROM target_fatture tf
         WHERE p_force_new_tentativo IS TRUE
            OR NOT EXISTS (SELECT 1 FROM vendite.fatture_sdi fs3 WHERE fs3.fattura_id = tf.f_id)
        ON CONFLICT (fattura_id, tentativo) DO UPDATE SET stato_sdi_id = v_stato_sdi_id, data_update = now()
        RETURNING vendite.fatture_sdi.id AS fs_id, vendite.fatture_sdi.fattura_id AS fs_fattura_id, vendite.fatture_sdi.tentativo AS fs_tentativo, vendite.fatture_sdi.stato_sdi_id AS fs_stato_sdi_id
    )
    SELECT u.fs_id, u.fs_fattura_id, u.fs_tentativo, u.fs_stato_sdi_id,
           tf.codice_doc, tf.numero, tf.data, tf.billing_account_id,
           tf.emittente_soggetto_ruolo_id, tf.valuta_id,
           -- rev 2026-07-28: era SUM(ri.totale_riga) su
           -- vendite.fatture_riepiloghi_iva, colonna INESISTENTE
           -- (errore latente: plpgsql pianifica alla prima
           -- esecuzione). Il totale dovuto e' quello che
           -- fn_ricalcola_totali_fattura ha gia' calcolato,
           -- fondi e arrotondamento inclusi.
           COALESCE(tf.totale_a_pagare, 0)
      FROM upserted u
      JOIN target_fatture tf ON tf.f_id = u.fs_fattura_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_prepare_sdi_payload(p_lotto_id bigint, p_stato_sdi_codice_interno character varying, p_force_new_tentativo boolean)
IS 'Prepara dataset SDI per lotto e apre/riusa tentativi su fatture_sdi. rev 2026-07-28: il totale documento viene letto da vendite.fatture.totale_a_pagare — prima sommava fatture_riepiloghi_iva.totale_riga, colonna che su quella tabella NON esiste (le sue colonne di importo sono imponibile, imposta, arrotondamento). Era un errore latente: plpgsql pianifica alla prima esecuzione, quindi sarebbe esploso al primo lotto portato a INVIATA. totale_a_pagare e'' il valore prodotto da fn_ricalcola_totali_fattura, fondi e arrotondamento dell''emittente-utility inclusi: ricostruirlo qui sarebbe una seconda implementazione della stessa regola fiscale. NB: `totale_riga` esiste, ma come colonna calcolata delle viste di riepilogo IVA degli ALTRI documenti (vw_ordini_riepilogo_iva_dettaglio e sorelle) — omonimia, non la stessa cosa. brief-fix-importi-riga-fattura-zero §4.4 (D2).';
```

---
{% include-markdown "signature-core.md" %}
