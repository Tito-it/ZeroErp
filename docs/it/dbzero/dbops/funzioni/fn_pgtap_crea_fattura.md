{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_fattura.md" %}
# ⚙️ Funzione `fn_pgtap_crea_fattura`

```sql
CREATE FUNCTION fn_pgtap_crea_fattura(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_spoglia_indirizzi boolean, p_spoglia_intestazione boolean, p_minimo boolean, p_totale_a_pagare numeric, p_termine_pagamento_id bigint, p_senza_utility boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_fattura(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_spoglia_indirizzi boolean DEFAULT false, p_spoglia_intestazione boolean DEFAULT false, p_minimo boolean DEFAULT false, p_totale_a_pagare numeric DEFAULT NULL::numeric, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_senza_utility boolean DEFAULT false)
 RETURNS TABLE(fattura_id bigint, registro_id bigint, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer, tipo_doc_fiscale_id bigint, stato_doc_fiscale_id bigint, valuta_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una FATTURA del mondo in una
--   chiamata — azienda, operatore, cliente, registro coerente e
--   testata —
--   con l'ordine obbligato dentro l'oggetto invece che nel file.
-- Uso:
--   CREATE TEMP TABLE tmp_f AS
--   SELECT * FROM dbops.fn_pgtap_crea_fattura('sistemazioni');
--   -- la seconda fattura dello STESSO cliente:
--   SELECT * FROM dbops.fn_pgtap_crea_fattura(
--              'sistemazioni 2', 'DRAFT',
--              (SELECT billing_account_id FROM tmp_f));
--   -- fuori bozza, ma senza indirizzi ne' intestazione:
--   SELECT * FROM dbops.fn_pgtap_crea_fattura(
--              'nuda', 'DEFINITIVA', NULL, true, true);
-- ⛔ Righe, scadenze, contabili e movimenti NON li scrive: sono il
--   caso del test.
-- ⭐ rev 2026-10-24 (20261024-25, brief-modello-documento-vendita N-1):
--   la fattura NASCE nello stato iniziale (trigger della nascita); uno
--   stato diverso si raggiunge con dbops.fn_pgtap_porta_a_stato, sotto
--   i guard veri. Un passaggio che pretende cio' che il builder non
--   scrive (righe, indirizzi…) qui fallisce: il test lo scrive e porta
--   avanti da se'.
-- ⭐ rev 2026-10-24 (20261024-27, Q-2): p_spoglia_indirizzi e
--   p_spoglia_intestazione. La spoliazione si fa nell'ultimo stato
--   non congelato del percorso (congela_fiscale = false), letto dal
--   vocabolario: li' i guard di congelamento non scattano.
-- ⭐ rev 2026-10-24 (20261024-36, R-5): minimo, totale a pagare e
--   termine di pagamento alla nascita, nell'INSERT.
-- ⭐ rev 2026-10-24 (20261024-42): p_senza_utility, la fattura senza
--   utility (la colonna e' nullable: e' il caso dei fondi).
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_tipo_id   config.tipi_doc_fiscale.id%TYPE;
    v_stato_id  config.stati_doc_fiscale.id%TYPE;
    v_ordine    config.stati_doc_fiscale.ordine%TYPE;
    v_sosta     config.stati_doc_fiscale.codice_interno%TYPE;
    v_valuta_id config.valute.id%TYPE;
    v_registro  vendite.registri_fatturazione.id%TYPE;
    v_fattura   vendite.fatture.id%TYPE;
    v_spoglia   boolean := COALESCE(p_spoglia_indirizzi, false)
                           OR COALESCE(p_spoglia_intestazione, false);
BEGIN
    -- 0. Lo stato si giudica PRIMA di costruire.
    -- Lo stato dalla sede della traduzione codice -> id
    -- (script.fn_doc_stato_id): solo uno stato ATTIVO e' una destinazione.
    v_stato_id := script.fn_doc_stato_id('vendite.fatture'::regclass, p_stato_codice_interno);
    SELECT s.ordine INTO v_ordine
      FROM config.stati_doc_fiscale s
     WHERE s.id = v_stato_id;

    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_fattura: nessuno stato documento fiscale attivo con codice_interno = %',
            p_stato_codice_interno;
    END IF;

    IF v_spoglia THEN
        IF v_stato_id = script.fn_doc_stato_iniziale_id('vendite.fatture'::regclass) THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_fattura: % e'' lo stato iniziale, e una fattura che resta in bozza nasce gia'' senza indirizzi e intestazione: non c''e'' niente da spogliare',
                p_stato_codice_interno;
        END IF;

        -- La sosta: l'ultimo stato non congelato prima di quello
        -- chiesto (o lui stesso), dal vocabolario.
        SELECT s.codice_interno INTO v_sosta
          FROM config.stati_doc_fiscale s
         WHERE s.attivo IS TRUE
           AND s.iniziale IS FALSE
           AND s.congela_fiscale IS FALSE
           AND s.ordine <= v_ordine
         ORDER BY s.ordine DESC, s.id
         LIMIT 1;

        IF v_sosta IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_fattura: nessuno stato non congelato (congela_fiscale = false) prima di % in cui spogliare la fattura',
                p_stato_codice_interno;
        END IF;
    END IF;

    -- 1. Il mondo. Senza p_billing_account_id costruisce anche il
    --    cliente; con, riusa quello e prende solo l'azienda di chi
    --    agisce, senza costruire un cliente in piu'
    --    (dbops.fn_pgtap_cliente_del_builder, rev 20261024-40).
    SELECT c.emittente_fiscale_id, c.emittente_soggetto_ruolo_id,
           c.auth_user_id, c.billing_account_id, c.istanza_utility_id,
           c.cliente_soggetto_ruolo_id, c.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_cliente_del_builder(
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_fattura') c;

    -- 2. La coppia (emittente, utility) NON si scrive piu' (rev
    --    20261021-17, brief-db-modelli-documento-standard §10.7 R-4):
    --    senza la riga valgono i parametri di sistema dell'utility
    --    (anagrafiche.fn_parametri_importo_utility), e una testata
    --    fiscale non la pretende piu'. Scriverla nascondeva ai test
    --    proprio il caso dell'emittente nuovo.

    -- 3. Il catalogo si SCEGLIE, e ogni scelta ha il suo ORDER BY.
    SELECT t.id INTO v_tipo_id
      FROM config.tipi_doc_fiscale t
     WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1;

    -- La valuta dalla catena del dominio (vendite.fn_get_valuta_id:
    -- billing account, poi emittente, poi gestore), come la risolvono i
    -- trigger di default dei documenti: non la prima del catalogo.
    v_valuta_id := vendite.fn_get_valuta_id(v_ba_id, v_ef_sr_id);

    -- 4. Il registro dell'azienda di chi agisce: lo crea se non
    --    c'e', e non ne pesca uno di un'altra (il guard
    --    trgfn_fatture_guard_registro_emittente lo rifiuterebbe).
    v_registro := script.fn_pgtap_registro_fattura(v_ef_sr_id);

    INSERT INTO vendite.fatture (
        registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
        tipo_doc_fiscale_id, valuta_id, utility_id, meta,
        minimo, totale_a_pagare, termine_pagamento_id)
    VALUES (v_registro, (SELECT script.fn_data_operativa()), v_ef_sr_id, v_ba_id,
            v_tipo_id, v_valuta_id,
            CASE WHEN COALESCE(p_senza_utility, false) THEN NULL ELSE v_utility END,
            jsonb_build_object('test_scope', 'pgtap_' || p_etichetta),
            COALESCE(p_minimo, false), p_totale_a_pagare, p_termine_pagamento_id)
    RETURNING id INTO v_fattura;

    -- Lo stato chiesto (rev 20261024-25): il documento e' nato nello stato
    -- iniziale; se il test ne vuole un altro, ci arriva per la matrice.
    -- Per uscire dalla bozza la fattura vuole indirizzi e
    -- intestazione congelati: li scrive, come la pipeline prima
    -- di emettere, coi suoi building block. Righe con IVA,
    -- scadenze e numero restano del test.
    IF v_stato_id IS DISTINCT FROM script.fn_doc_stato_iniziale_id('vendite.fatture'::regclass) THEN
        PERFORM vendite.fn_snapshot_indirizzi_fattura(v_fattura);
        PERFORM vendite.fn_snapshot_intestazione_fattura(v_fattura);

        -- La spoliazione (rev 20261024-27): nella sosta i guard di
        -- congelamento non scattano; poi il resto del percorso.
        IF v_spoglia THEN
            PERFORM dbops.fn_pgtap_porta_a_stato('vendite.fatture'::regclass, v_fattura, v_sosta);

            IF COALESCE(p_spoglia_indirizzi, false) THEN
                DELETE FROM vendite.fatture_indirizzi fi
                 WHERE fi.fattura_id = v_fattura;
            END IF;

            IF COALESCE(p_spoglia_intestazione, false) THEN
                UPDATE vendite.fatture f
                   SET emittente_snapshot = NULL,
                       cliente_snapshot   = NULL
                 WHERE f.id = v_fattura;
            END IF;
        END IF;

        IF NOT v_spoglia OR v_sosta IS DISTINCT FROM p_stato_codice_interno THEN
            PERFORM dbops.fn_pgtap_porta_a_stato('vendite.fatture'::regclass, v_fattura, p_stato_codice_interno);
        END IF;
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    -- utility_id: quella scritta sulla testata (NULL con p_senza_utility).
    RETURN QUERY
    SELECT v_fattura, v_registro, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id,
           CASE WHEN COALESCE(p_senza_utility, false) THEN NULL ELSE v_utility END,
           v_tipo_id, v_stato_id, v_valuta_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_fattura(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_spoglia_indirizzi boolean, p_spoglia_intestazione boolean, p_minimo boolean, p_totale_a_pagare numeric, p_termine_pagamento_id bigint, p_senza_utility boolean)
IS 'Fixture pgTAP: una FATTURA del mondo in una chiamata: azienda, operatore e cliente (dbops.fn_pgtap_cliente_del_builder: quello del terzo parametro, verificato dell''azienda di chi agisce, o uno nuovo del mondo), il registro coerente con l''emittente di chi agisce (script.fn_pgtap_registro_fattura) e la testata nello stato scelto. Esiste per la catena d''ordine: cliente legato a chi agisce, registro dell''azienda giusta, valuta risolvibile, che su un database ricostruito non esistono. La valuta dalla catena del dominio (vendite.fn_get_valuta_id: billing account, poi emittente, poi gestore). Lo stato: lo traduce script.fn_doc_stato_id, quindi uno stato spento o inesistente solleva prima di costruire; la fattura nasce nello stato iniziale della testata (script.fn_doc_stato_iniziale_id) e, se il test ne chiede un altro, ci arriva per la matrice (dbops.fn_pgtap_porta_a_stato) sotto i guard veri, con indirizzi e intestazione scritti dai building block come fa la pipeline. Quarto e quinto parametro: la fattura arriva nello stato chiesto senza indirizzi e/o senza intestazione congelata; si spoglia nell''ultimo stato non congelato del percorso (congela_fiscale = false, letto dal vocabolario); spogliare una fattura che resta in bozza solleva. Dal sesto all''ottavo: minimo, totale a pagare e termine di pagamento, scritti alla nascita. Nono, p_senza_utility: la fattura nasce senza utility (la colonna e'' nullable). ⛔ NON scrive righe, scadenze, contabili ne'' movimenti: sono il caso del test. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
