{% include-markdown "it/dbzero/vendite/manual/fn_build_fattura_key.md" %}
# ⚙️ Funzione `fn_build_fattura_key`

```sql
CREATE FUNCTION fn_build_fattura_key(p_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_build_fattura_key(p_attivita_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: chiave logica di aggregazione del documento a partire da una
--        attivita' fatturabile. Da D-7/D-B comprende anche le
--        condizioni di pagamento: due attivita' con termini diversi
--        finiscono su due fatture.
-- Regole: le condizioni si risolvono con la catena UNICA
--         (fn_resolve_termini_pagamento, 3b.1) — questa e' la
--         chiamata che chiude C-13, perche' una catena riscritta e
--         mai invocata resta un secondo risolutore in attesa d'uso.
-- rev 2026-08-18 (brief nota di credito, N2b): il registro si
--         risolve passando ANCHE utility ed emittente.
-- rev 2026-08-18 (brief nota di credito, N3): la chiave porta la
--         NATURA e la SERIE. E' cio' che impedisce a un'attivita'
--         di rettifica di finire nella fattura ordinaria: undici
--         elementi, e da qui in giu' vanno usati tutti e undici.
DECLARE
    v_ba_id               anagrafiche.billing_account.id%TYPE;
    v_ba_fattura_id       anagrafiche.billing_account.id%TYPE;
    v_tipo_doc_fiscale_id config.tipi_doc_fiscale.id%TYPE;
    v_natura_doc_id       config.nature_doc_fiscale.id%TYPE;
    v_valuta_id           config.valute.id%TYPE;
    v_utility_id          config.utilities.id%TYPE;
    v_emittente_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_reseller_id         anagrafiche.soggetti_ruoli.id%TYPE;
    v_registro_id         vendite.registri_fatturazione.id%TYPE;
    v_serie               vendite.fatture.serie%TYPE;
    v_termine_id          config.termini_pagamento.id%TYPE;
    v_modalita_id         config.modalita_pagamento.id%TYPE;
BEGIN
    -- Guard: parametro obbligatorio
    IF p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_fattura_key', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_attivita_id', 'valore', p_attivita_id),
            NULL::uuid, 'p_attivita_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera BA, tipo doc, natura, valuta, utility dall'attivita'
    SELECT a.billing_account_id,
           COALESCE(ba.parent_account_id, a.billing_account_id),
           a.tipo_doc_fiscale_id,
           a.natura_doc_id,
           a.valuta_id,
           ba.utility_id
      INTO v_ba_id, v_ba_fattura_id, v_tipo_doc_fiscale_id, v_natura_doc_id,
           v_valuta_id, v_utility_id
      FROM vendite.attivita_fatturabili a
      JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id
     WHERE a.id = p_attivita_id;

    IF v_ba_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_fattura_key', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id),
            NULL::uuid, concat('attivita o BA non trovati per id ', p_attivita_id)
        );
    END IF;

    -- Emittente dal mapping BA → emittente fiscale
    v_emittente_id := anagrafiche.fn_get_emittente_fiscale_id(v_ba_fattura_id);

    -- Reseller dal mapping BA → reseller (opzionale)
    SELECT rb.reseller_soggetto_ruolo_id
      INTO v_reseller_id
      FROM anagrafiche.resellers_billing_account rb
     WHERE rb.billing_account_id = v_ba_fattura_id
     ORDER BY rb.id
     LIMIT 1;

    -- Registro E SERIE dal mapping (tipo documento, natura), con
    -- utility ed emittente a raffinare (N2b).
    SELECT g.registro_id, g.serie
      INTO v_registro_id, v_serie
      FROM vendite.fn_get_registro_id(
               p_tipo_doc_fiscale_id         => v_tipo_doc_fiscale_id,
               p_natura_doc_id               => v_natura_doc_id,
               p_utility_id                  => v_utility_id,
               p_emittente_soggetto_ruolo_id => v_emittente_id) g;

    -- Condizioni di pagamento: catena unica (3b.1).
    SELECT t.termine_pagamento_id, t.modalita_pagamento_id
      INTO v_termine_id, v_modalita_id
      FROM vendite.fn_resolve_termini_pagamento(p_attivita_id) t;

    RETURN jsonb_build_object(
        'billing_account_id', v_ba_fattura_id,
        'tipo_doc_fiscale_id', v_tipo_doc_fiscale_id,
        'natura_doc_id', v_natura_doc_id,
        'valuta_id', v_valuta_id,
        'emittente_soggetto_ruolo_id', v_emittente_id,
        'reseller_soggetto_ruolo_id', v_reseller_id,
        'utility_id', v_utility_id,
        'registro_id', v_registro_id,
        'serie', v_serie,
        'termine_pagamento_id', v_termine_id,
        'modalita_pagamento_id', v_modalita_id
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_build_fattura_key(p_attivita_id bigint)
IS 'Chiave logica di aggregazione del documento a partire da un''attivita'' fatturabile: due attivita'' con la stessa chiave finiscono sulla stessa fattura. Undici elementi dal 2026-08-18, e da qui in giu'' vanno usati tutti e undici — chi separa nella chiave e non separa nel lookup annulla le due meta'' e fa tornare le attivita'' nella stessa fattura. rev 2026-08-18 (brief-design-note-credito-resi N2b): il registro si risolve passando ANCHE utility ed emittente, senza i quali i sezionali intestati erano irraggiungibili. rev 2026-08-18 (N3): la chiave porta natura_doc_id e serie. ⭐ E'' qui che la separazione fisica della nota di credito finisce: lotto, testata, registro e numerazione si separano da soli, senza una riga di codice scritta per la NC. ⚠️ Da questo momento un LOTTO puo'' contenere documenti di natura diversa: chi lo legge non deve piu'' assumere «sono tutte fatture».';
```

---
{% include-markdown "signature-core.md" %}
