{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_fattura_header.md" %}
# ⚙️ Funzione `fn_get_or_create_fattura_header`

```sql
CREATE FUNCTION fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: recupera o crea la testata DRAFT della fattura a cui
--        l'attivita' appartiene, dentro il lotto dato.
-- Regole: il `WHERE` del lookup e la INSERT devono nominare gli
--         STESSI elementi della chiave prodotta da
--         fn_build_fattura_key (§6). Se la chiave separa e il
--         lookup no, le due meta' si annullano e le attivita'
--         tornano nella stessa fattura.
DECLARE
    v_key          JSONB;
    v_fattura_id   vendite.fatture.id%TYPE;
    v_stato_doc_id config.stati_doc_fiscale.id%TYPE;
    v_registro_id  vendite.registri_fatturazione.id%TYPE;
    v_ba_id        anagrafiche.billing_account.id%TYPE;
    v_tipo_doc_id  config.tipi_doc_fiscale.id%TYPE;
    v_valuta_id    config.valute.id%TYPE;
    v_utility_id   config.utilities.id%TYPE;
    v_emittente_id anagrafiche.soggetti_ruoli.id%TYPE;
    v_reseller_id  anagrafiche.soggetti_ruoli.id%TYPE;
    v_termine_id   config.termini_pagamento.id%TYPE;
    v_modalita_id  config.modalita_pagamento.id%TYPE;
BEGIN
    -- Guard: parametri obbligatori
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 OR p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_fattura_header', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id/p_attivita_id', 'lotto_id', p_lotto_id, 'attivita_id', p_attivita_id),
            NULL::uuid, 'p_lotto_id e p_attivita_id obbligatori e > 0'
        );
    END IF;

    -- Chiave documento dall'attivita': nove elementi, e da qui in
    -- giu' vanno usati tutti e nove.
    v_key := vendite.fn_build_fattura_key(p_attivita_id);
    v_ba_id        := (v_key->>'billing_account_id')::BIGINT;
    v_tipo_doc_id  := (v_key->>'tipo_doc_fiscale_id')::BIGINT;
    v_valuta_id    := (v_key->>'valuta_id')::INTEGER;
    v_emittente_id := (v_key->>'emittente_soggetto_ruolo_id')::BIGINT;
    v_reseller_id  := NULLIF(v_key->>'reseller_soggetto_ruolo_id', '')::BIGINT;
    v_utility_id   := NULLIF(v_key->>'utility_id', '')::INTEGER;
    v_registro_id  := (v_key->>'registro_id')::BIGINT;
    v_termine_id   := NULLIF(v_key->>'termine_pagamento_id', '')::BIGINT;
    v_modalita_id  := NULLIF(v_key->>'modalita_pagamento_id', '')::INTEGER;

    -- Completezza della chiave: si pretendono solo gli elementi
    -- che NON possono legittimamente mancare. utility_id entra
    -- nell'elenco perche' anagrafiche.billing_account.utility_id e'
    -- NOT NULL: se qui arriva vuoto, la chiave e' rotta, non
    -- «senza utility». Termine e modalita' restano fuori, e non e'
    -- una dimenticanza: la modalita' e' NULL nella maggioranza dei
    -- casi (nessun default inventato, finirebbe sulla FatturaPA) e
    -- il termine ha il default TP_1RATA della catena — la sua
    -- assenza la presidia la Fase 4 al momento di generare le rate.
    IF v_ba_id IS NULL OR v_tipo_doc_id IS NULL OR v_valuta_id IS NULL
       OR v_emittente_id IS NULL OR v_utility_id IS NULL OR v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_fattura_header', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id, 'chiave', v_key),
            NULL::uuid, concat('chiave documento incompleta per attivita_id ', p_attivita_id)
        );
    END IF;

    -- Stato DRAFT
    SELECT id INTO v_stato_doc_id
      FROM config.stati_doc_fiscale
     WHERE codice_interno = 'DRAFT' AND attivo IS TRUE
     ORDER BY id LIMIT 1;

    IF v_stato_doc_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_fattura_header', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'DRAFT'),
            NULL::uuid, 'stato DRAFT non trovato'
        );
    END IF;

    -- Cerca fattura gia' nel lotto con la stessa chiave.
    -- ⚠️ IS NOT DISTINCT FROM sui tre elementi nullable: con `=`
    -- il NULL non combacia mai, quindi ogni giro aprirebbe una
    -- fattura nuova per i casi — che sono la maggioranza — in cui
    -- reseller o modalita' non ci sono. E' la stessa trappola dei
    -- NULL gia' pagata in 3b.0-b sul WHERE della commessa e in
    -- 3b.4-bis sull'indice d'ambito, terza forma.
    SELECT f.id INTO v_fattura_id
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
       AND f.billing_account_id = v_ba_id
       AND f.tipo_doc_fiscale_id = v_tipo_doc_id
       AND f.valuta_id = v_valuta_id
       AND f.emittente_soggetto_ruolo_id = v_emittente_id
       AND f.reseller_soggetto_ruolo_id IS NOT DISTINCT FROM v_reseller_id
       AND f.utility_id IS NOT DISTINCT FROM v_utility_id
       AND f.registro_id = v_registro_id
       AND f.termine_pagamento_id IS NOT DISTINCT FROM v_termine_id
       AND f.modalita_pagamento_id IS NOT DISTINCT FROM v_modalita_id
     ORDER BY f.id LIMIT 1;

    IF v_fattura_id IS NOT NULL THEN RETURN v_fattura_id; END IF;

    -- Crea fattura + link lotto. Le colonne di testata sono il
    -- secondo specchio: quello che la chiave ha deciso, qui si
    -- scrive.
    INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
        emittente_soggetto_ruolo_id, billing_account_id, reseller_soggetto_ruolo_id,
        utility_id, valuta_id, tasso_cambio,
        termine_pagamento_id, modalita_pagamento_id, meta)
    VALUES (v_registro_id, current_date, v_tipo_doc_id, v_stato_doc_id,
        v_emittente_id, v_ba_id, v_reseller_id,
        v_utility_id, v_valuta_id, 1,
        v_termine_id, v_modalita_id, jsonb_build_object('lotto_id', p_lotto_id))
    RETURNING id INTO v_fattura_id;

    INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, esclusa, meta)
    VALUES (p_lotto_id, v_fattura_id, FALSE, jsonb_build_object('origine', 'bozza'));

    RETURN v_fattura_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
IS 'Recupera o crea testata fattura DRAFT per lotto dalla chiave documento dell''attivita''. Da 3b.3 il WHERE del lookup confronta TUTTI e nove gli elementi della chiave — utility_id (che mancava da sempre) e la coppia (termine, modalita'') entrata con D-7/D-B — con IS NOT DISTINCT FROM sui nullable, e la INSERT scrive in testata utility, termine e modalita''. Chiave e lookup disallineati si annullano a vicenda: cfr. §6 del piano, i tre specchi.';
```

---
{% include-markdown "signature-core.md" %}
