{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_fattura.md" %}
# ⚙️ Funzione `fn_get_saldo_fattura`

```sql
CREATE FUNCTION fn_get_saldo_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_fattura(p_fattura_id bigint)
 RETURNS TABLE(saldo numeric, in_lavorazione numeric, incassato numeric, has_movimenti boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_totale_a_pagare vendite.fatture.totale_a_pagare%TYPE;
    v_movimenti       vendite.fatture.totale_a_pagare%TYPE;
    v_incassato       vendite.fatture.totale_a_pagare%TYPE;
    v_in_lavorazione  vendite.fatture.totale_a_pagare%TYPE;
    v_has_movimenti   boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il saldo di un DOCUMENTO, in tre numeri:
    --     saldo          = totale_a_pagare - movimenti attivi
    --     in_lavorazione = dichiarato e non ancora registrato
    --     incassato      = quanto di registrato e' cassa vera
    --
    -- Rev 2026-08-25 (S5-1, lotto 8): le due colonne diventano
    -- quattro, la stessa forma e lo stesso ordine di
    -- fn_get_saldo_rata. Nessun predicato preesistente cambia:
    -- `saldo` e `has_movimenti` rispondono esattamente come
    -- prima.
    -- =========================================================

    -- Guard di parametro: un id nullo o non positivo non esce da
    -- nessuna interfaccia — lo produce solo un chiamante rotto,
    -- ed e' per questo che il codice e' TECNICO.
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.fn_get_saldo_fattura', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
        jsonb_build_object(
          'detail', 'fattura_id obbligatoria e maggiore di zero',
          'p_fattura_id', p_fattura_id
        ),
        NULL::uuid,
        'pagamenti.fn_get_saldo_fattura', 'p_fattura_id (obbligatorio, maggiore di zero)'
      );
    END IF;

    -- Recupera totale_a_pagare da fattura
    SELECT f.totale_a_pagare
      INTO v_totale_a_pagare
      FROM vendite.fatture f
     WHERE f.id = p_fattura_id;

    -- ⚠️ L'id e' valido: e' il documento a non esserci. Codice
    --    diverso dal guard di parametro perche' il rimedio e'
    --    diverso. E la tabella ha la RLS: «non esiste» e «non la
    --    vedi» arrivano qui allo stesso modo, per scelta.
    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.fn_get_saldo_fattura', 'E_FATTURA_NON_TROVATA',
        jsonb_build_object('detail','Fattura non trovata', 'fattura_id', p_fattura_id),
        NULL::uuid,
        p_fattura_id::text
      );
    END IF;

    -- =========================================================
    -- Cio' che e' REGISTRATO, e quanto di quello e' cassa vera.
    -- ⚠️ `incassato` pretende che il centro CI SIA e che non sia
    --    ne' fondo fattura ne' compensazione: un movimento senza
    --    centro non e' «denaro arrivato», e' un canale non
    --    dichiarato. Identico alla sorella della rata.
    -- =========================================================
    SELECT COALESCE(SUM(m.importo), 0),
           COALESCE(SUM(m.importo) FILTER (
               WHERE c.id IS NOT NULL
                 AND c.is_fondo_fattura IS FALSE
                 AND c.is_compensazione IS FALSE), 0),
           COUNT(*) > 0
      INTO v_movimenti, v_incassato, v_has_movimenti
      FROM pagamenti.vendite_movimenti m
      LEFT JOIN pagamenti.centri_riscossione c
        ON c.id = m.centro_riscossione_id
     WHERE m.fattura_id = p_fattura_id
       AND m.attivo IS TRUE;

    -- =========================================================
    -- Cio' che e' DICHIARATO e non ancora registrato.
    -- ⭐ Si CHIEDE alla funzione che gia' lo sa, non si riscrive
    --    il predicato: due sedi per la stessa regola divergono
    --    al primo aggiustamento, ed e' il vincolo «una sede sola
    --    per i saldi» che il backend costruisce sopra questa.
    -- =========================================================
    SELECT sc.saldo_contabile
      INTO v_in_lavorazione
      FROM pagamenti.fn_get_saldo_fattura_contabili(p_fattura_id) sc;

    RETURN QUERY SELECT
        COALESCE(v_totale_a_pagare, 0) - COALESCE(v_movimenti, 0),
        COALESCE(v_in_lavorazione, 0),
        COALESCE(v_incassato, 0),
        COALESCE(v_has_movimenti, false);
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldo_fattura(p_fattura_id bigint)
IS 'Il saldo di un DOCUMENTO, in tre numeri: `saldo` = totale_a_pagare meno i movimenti attivi; `in_lavorazione` = quanto e'' gia'' dichiarato su righe contabili pronte sotto una testata non finale; `incassato` = quanto di cio'' che e'' registrato e'' DENARO DAVVERO ARRIVATO. ⭐ Rev 2026-08-25 (S5-1): fino a ieri rispondeva DUE numeri mentre la sorella fn_get_saldo_rata ne rispondeva tre — cioe'' la distinzione fra registrato e incassato, che il dominio dichiara obbligatoria, esisteva sulla rata e NON sul documento, che e'' il livello guardato per primo e quello su cui nascera'' il saldo CLIENTE. Nessun predicato preesistente e'' cambiato: `saldo` e `has_movimenti` rispondono come prima. ⭐ `in_lavorazione` NON e'' ricalcolato qui: si delega a fn_get_saldo_fattura_contabili, che e'' la sede del dichiarato — riscriverne il predicato avrebbe creato la seconda sede proprio nel passo che costruisce la base unica dei saldi. Quella funzione resta anche perche'' da'' `has_righe_postabili`, che serve a vendite.fn_saldo_sorgente_fondo. ⚠️ `incassato` esclude i centri is_fondo_fattura e is_compensazione — NON SONO CASSA: un movimento li'' salda il documento perche'' il denaro si e'' mosso per trasferimento, ma in banca non e'' entrato niente. E un movimento SENZA centro non ci entra: «canale non dichiarato» non e'' «denaro arrivato», e su una misura di cassa si sta dalla parte prudente. ⚠️ `saldo` e `in_lavorazione` restano DUE colonne e non si sommano, o non si capisce piu'' che cosa si sta guardando. ⚠️ La fattura ha la RLS: «non esiste» e «non la vedi» danno lo stesso E_FATTURA_NON_TROVATA, per scelta. ⚠️ NON e'' dichiarata STABLE: il ramo d''errore scrive nel registro, e promettere stabilita'' su una funzione che in un ramo scrive autorizza il planner a scelte che quel ramo non regge. S5-1 del cantiere incassi, richiesta DB-10 del brief BE/FE.';
```

---
{% include-markdown "signature-core.md" %}
