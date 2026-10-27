{% include-markdown "it/dbzero/vendite/manual/fn_sync_lotto_fatture_stato.md" %}
# ⚙️ Funzione `fn_sync_lotto_fatture_stato`

```sql
CREATE FUNCTION fn_sync_lotto_fatture_stato(p_lotto_id bigint, p_target_stato_doc_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_lotto_fatture_stato(p_lotto_id bigint, p_target_stato_doc_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- rev 2026-08-04 (D-M): via il predicato su lf.esclusa (sempre
--   vero) e l'argomento p_esclusa all'helper.
-- rev 2026-10-27 (20261027-11, brief-modello-documento-vendita
--   §15): le fatture seguono il lotto dal verbo della fattura
--   (vendite.fn_fattura_proietta_stato), una per una: la porta
--   non lascia passare l'UPDATE.
DECLARE
    v_stato_lotto vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_target      config.stati_doc_fiscale.id%TYPE;
    v_tipo_lotto  vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_inviata_id  config.stati_doc_fiscale.id%TYPE;
    v_fattura_id  vendite.fatture.id%TYPE;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_lotto_fatture_stato', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_target_stato_doc_fiscale_id IS NOT NULL AND p_target_stato_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_lotto_fatture_stato', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_target_stato_doc_fiscale_id', 'valore', p_target_stato_doc_fiscale_id), NULL::uuid, 'p_target_stato_doc_fiscale_id se fornito deve essere > 0');
    END IF;

    SELECT tipo_lotto, stato_doc_fiscale_id INTO v_tipo_lotto, v_stato_lotto
      FROM vendite.fatturazione_lotti WHERE id = p_lotto_id FOR UPDATE;

    IF v_stato_lotto IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_lotto_fatture_stato', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, p_lotto_id::text);
    END IF;

    v_target := COALESCE(p_target_stato_doc_fiscale_id, v_stato_lotto);

    IF v_target IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_lotto_fatture_stato', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale_target', 'lotto_id', p_lotto_id), NULL::uuid, concat('stato_doc_fiscale target obbligatorio per lotto ', p_lotto_id));
    END IF;

    -- Allinea stato fatture (escluse le critical), dal verbo
    -- della fattura: una per una, nell'ordine degli id.
    FOR v_fattura_id IN
        SELECT f.id
          FROM vendite.fatture f
          JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = f.id
         WHERE lf.lotto_id = p_lotto_id
           AND COALESCE(f.critical, FALSE) IS FALSE
           AND f.stato_doc_fiscale_id IS DISTINCT FROM v_target
         ORDER BY f.id
    LOOP
        PERFORM vendite.fn_fattura_proietta_stato(v_fattura_id, v_target);
    END LOOP;

    -- Sync stato_esecuzione sul ponte
    UPDATE vendite.fatturazione_lotti_fatture lf
       SET stato_doc_fiscale_id = f.stato_doc_fiscale_id,
           stato_esecuzione = vendite.fn_resolve_stato_esecuzione(
               p_stato_source => 'COMPLETATO',
               p_has_critical => COALESCE(f.critical, FALSE),
               p_fatturato => FALSE, p_default_stato_esecuzione => 'COMPLETED'),
           data_update = now(), user_update = current_user
      FROM vendite.fatture f WHERE lf.lotto_id = p_lotto_id AND lf.fattura_id = f.id;

    -- GIORNALIERO + INVIATA → chiusura lotto
    IF v_tipo_lotto = 'GIORNALIERO' THEN
        SELECT id INTO v_inviata_id FROM config.stati_doc_fiscale WHERE codice_interno = 'INVIATA' AND attivo IS TRUE ORDER BY ordine LIMIT 1;
        IF v_inviata_id IS NOT NULL AND v_target = v_inviata_id THEN
            UPDATE vendite.fatturazione_lotti SET stato_operativo = 'CHIUSO', data_update = now(), user_update = current_user WHERE id = p_lotto_id;
        END IF;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_sync_lotto_fatture_stato(p_lotto_id bigint, p_target_stato_doc_fiscale_id bigint)
IS 'Allinea stato fatture del lotto e sincronizza stato_esecuzione. GIORNALIERO+INVIATA chiude lotto. rev 2026-08-04 (D-M): via il predicato su lf.esclusa, che era una condizione sempre vera, e via l''argomento p_esclusa all''helper. rev 2026-10-27 (20261027-11, brief-modello-documento-vendita §15): le fatture (non critical, con lo stato diverso dal bersaglio) seguono il lotto dal verbo della fattura, vendite.fn_fattura_proietta_stato, una per una nell''ordine degli id: la porta della fattura non lascia passare l''UPDATE. Il letterale INVIATA resta (nessuna colonna del vocabolario dice lo stato dell''invio: debito dichiarato nel brief).';
```

</div>

---
{% include-markdown "signature-core.md" %}
