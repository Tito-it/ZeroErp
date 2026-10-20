{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_totali_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_totali_fattura`

```sql
CREATE FUNCTION fn_ricalcola_totali_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_totali_fattura(p_fattura_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: ricalcola imponibile, imposta, fondi, arrotondamento e
--        totale a pagare della fattura, aggiornando il saldo
--        dell'ambito di compensazione.
-- Regole: da D-N pezzo 2 il saldo d'ambito si legge AL NETTO del
--         contributo gia' dato da questa fattura
--         (`saldo - COALESCE(arrotondamento_attuale, 0)`): cosi' una
--         riesecuzione RIPETE il primo calcolo invece di inseguirlo,
--         e la scomposizione in testata resta vera — e' quella che
--         va in stampa. Da D-N pezzo 1 l'ambito comprende anche le
--         condizioni di pagamento della fattura. Da 3b.3 l'utility
--         si LEGGE dalla testata invece di essere dedotta. Da K-7
--         (20261021-02) decimali, metodo e soglie sono quelli effettivi
--         di anagrafiche.fn_parametri_importo_utility: la riga
--         dell'emittente se c'e', se no il valore di sistema
--         dell'utility. Senza la riga la fattura si chiude. Da R-2
--         (20261021-16) arrotonda con script.fn_arrotonda_importo.
DECLARE
    v_imponibile_tot  vendite.fatture.imponibile_tot%TYPE;
    v_imposta_tot     vendite.fatture.imposta_tot%TYPE;
    v_totale_doc      vendite.fatture.totale_doc%TYPE;
    v_totale_fondi    vendite.fatture_fondi_fattura.importo%TYPE;
    v_totale_a_pagare vendite.fatture.totale_a_pagare%TYPE;
    v_raw_totale      vendite.fatture.totale_a_pagare%TYPE;
    v_round_totale    vendite.fatture.totale_a_pagare%TYPE;
    v_arro_attuale    vendite.fatture.arrotondamento_attuale%TYPE;
    v_arro_precedente vendite.fatture.arrotondamento_precedente%TYPE;
    v_arro_proprio    vendite.fatture.arrotondamento_attuale%TYPE;
    v_saldo_scope     vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
    v_billing_account_id          vendite.fatture.billing_account_id%TYPE;
    v_tipo_doc_fiscale_id         vendite.fatture.tipo_doc_fiscale_id%TYPE;
    v_emittente_soggetto_ruolo_id vendite.fatture.emittente_soggetto_ruolo_id%TYPE;
    v_valuta_id      vendite.fatture.valuta_id%TYPE;
    v_termine_id     vendite.fatture.termine_pagamento_id%TYPE;
    v_modalita_id    vendite.fatture.modalita_pagamento_id%TYPE;
    v_utility_id     config.utilities.id%TYPE;
    v_min_soglia_min anagrafiche.emittenti_fiscali_utilities.minimo_soglia_min%TYPE;
    v_min_soglia_max anagrafiche.emittenti_fiscali_utilities.minimo_soglia_max%TYPE;
    v_decimali       anagrafiche.emittenti_fiscali_utilities.arrotondamento_importi_dec%TYPE;
    v_metodo         anagrafiche.emittenti_fiscali_utilities.metodo_arrotondamento_importi%TYPE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_totali_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    -- Le condizioni di pagamento entrano qui perche' da D-N fanno
    -- parte dell'ambito; `arrotondamento_attuale` serve allo storno.
    -- ⚠️ 3b.3: `utility_id` si legge dalla testata. Prima veniva
    -- dedotto con COALESCE(lotto, BA) — una seconda derivazione
    -- dello stesso fatto, che pero' partiva dal BA della fattura
    -- (il PADRE) mentre la chiave usa quello dell'attivita' (il
    -- FIGLIO): appena la gerarchia esiste, il documento verrebbe
    -- arrotondato con la configurazione emittente/utility di
    -- un'altra utility. Una riga senza utility_id non si indovina:
    -- cade su E_CONFIG_MANCANTE poche righe sotto, che e' il
    -- comportamento voluto.
    SELECT f.billing_account_id, f.tipo_doc_fiscale_id, f.emittente_soggetto_ruolo_id, f.valuta_id,
           f.termine_pagamento_id, f.modalita_pagamento_id, f.arrotondamento_attuale, f.utility_id
      INTO v_billing_account_id, v_tipo_doc_fiscale_id, v_emittente_soggetto_ruolo_id, v_valuta_id,
           v_termine_id, v_modalita_id, v_arro_proprio, v_utility_id
      FROM vendite.fatture f WHERE f.id = p_fattura_id;

    SELECT COALESCE(SUM(r.imponibile), 0), COALESCE(SUM(r.imposta), 0)
      INTO v_imponibile_tot, v_imposta_tot
      FROM vendite.fatture_riepiloghi_iva r WHERE r.fattura_id = p_fattura_id;

    v_totale_fondi := vendite.fn_get_totale_fondi_fattura(p_fattura_id);
    v_totale_doc := COALESCE(v_imponibile_tot, 0) + COALESCE(v_imposta_tot, 0);

    -- K-7 (20261021-02): i parametri effettivi, dal BB. La riga
    -- dell'emittente e' un override: senza, valgono quelli di sistema
    -- dell'utility. Zero righe solo se l'utility manca (anche NULL).
    SELECT p.minimo_soglia_min, p.minimo_soglia_max, p.arrotondamento_importi_dec, p.metodo_arrotondamento_importi
      INTO v_min_soglia_min, v_min_soglia_max, v_decimali, v_metodo
      FROM anagrafiche.fn_parametri_importo_utility(v_emittente_soggetto_ruolo_id, v_utility_id) p;

    IF v_decimali IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_totali_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('emittente', v_emittente_soggetto_ruolo_id, 'utility_id', v_utility_id, 'fattura_id', p_fattura_id),
            NULL::uuid, concat('utility mancante o sconosciuta per fattura ', p_fattura_id));
    END IF;

    -- D-N pezzo 2: il saldo d'ambito AL NETTO del proprio contributo.
    -- Senza lo storno, la riesecuzione parte da un saldo che contiene
    -- gia' il proprio arrotondamento e converge altrove: il totale
    -- resta simile, la scomposizione in testata diventa falsa.
    v_saldo_scope := vendite.fn_get_arrotondamento_scope(
        v_billing_account_id, v_utility_id, v_tipo_doc_fiscale_id,
        v_emittente_soggetto_ruolo_id, v_valuta_id,
        v_termine_id, v_modalita_id);
    v_arro_precedente := COALESCE(v_saldo_scope, 0) - COALESCE(v_arro_proprio, 0);

    v_raw_totale := v_totale_doc + COALESCE(v_totale_fondi, 0) + COALESCE(v_arro_precedente, 0);
    -- R-2 (20261021-16): la regola d'arrotondamento vive in un punto
    -- solo, script.fn_arrotonda_importo (vocabolario 20260728-07). Prima
    -- qui c'era una copia delle quattro formule, con un ripiego muto su
    -- HALF_UP per un metodo sconosciuto: ora un metodo fuori vocabolario
    -- si ferma (i CHECK sulle colonne non lo lasciano arrivare).
    v_round_totale := script.fn_arrotonda_importo(v_raw_totale, v_decimali, v_metodo);

    v_arro_attuale := v_round_totale - v_raw_totale;
    v_totale_a_pagare := v_raw_totale + v_arro_attuale;

    PERFORM vendite.fn_set_arrotondamento_scope(
        v_billing_account_id, v_utility_id, v_tipo_doc_fiscale_id,
        v_emittente_soggetto_ruolo_id, v_valuta_id,
        COALESCE(v_arro_precedente, 0) + COALESCE(v_arro_attuale, 0),
        v_termine_id, v_modalita_id);

    UPDATE vendite.fatture f
       SET imponibile_tot = v_imponibile_tot, imposta_tot = v_imposta_tot, totale_doc = v_totale_doc,
           arrotondamento_precedente = v_arro_precedente, arrotondamento_attuale = v_arro_attuale, totale_a_pagare = v_totale_a_pagare,
           minimo = ((v_min_soglia_min IS NOT NULL AND v_totale_a_pagare >= v_min_soglia_min) AND (v_min_soglia_max IS NULL OR v_totale_a_pagare <= v_min_soglia_max)),
           data_update = now(), user_update = current_user
     WHERE f.id = p_fattura_id;

    PERFORM vendite.fn_sync_contabili_fondo_fattura(p_fattura_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_totali_fattura(p_fattura_id bigint)
IS 'Ricalcola totali e arrotondamento della fattura. D-N pezzo 1: l''ambito di compensazione comprende (termine_pagamento_id, modalita_pagamento_id). D-N pezzo 2: il saldo d''ambito si legge al netto del contributo gia'' dato da questa fattura, cosi'' la riesecuzione ripete il primo calcolo invece di inseguirlo e la scomposizione precedente/attuale in testata resta vera. Da 3b.3 l''utility si legge da vendite.fatture.utility_id: la deduzione COALESCE(lotto, BA) partiva dal BA della fattura (il padre) mentre la chiave usa quello dell''attivita'' (il figlio), quindi con la gerarchia attiva avrebbe scelto la configurazione di arrotondamento di un''altra utility. Da K-7 (2026-10-21, brief-db-modelli-documento-standard §10.3, D-7): decimali, metodo e soglie dal BB anagrafiche.fn_parametri_importo_utility, cioe'' la riga dell''emittente se c''e'' e altrimenti il valore di sistema dell''utility; E_CONFIG_MANCANTE resta solo per una fattura senza utility. Da R-2 (2026-10-21, §10.7): l''arrotondamento del totale e'' script.fn_arrotonda_importo, la sede unica delle quattro regole, al posto di una copia delle formule.';
```

---
{% include-markdown "signature-core.md" %}
