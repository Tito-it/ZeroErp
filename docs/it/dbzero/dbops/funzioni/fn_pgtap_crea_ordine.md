{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ordine.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ordine`

```sql
CREATE FUNCTION fn_pgtap_crea_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ordine(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ordine_id bigint, ordine_uid uuid, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer, stato_doc_ordine_id bigint, valuta_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un ORDINE di vendita del mondo
--   in una chiamata: azienda, operatore, cliente e testata.
-- Uso:
--   CREATE TEMP TABLE tmp_o AS
--   SELECT * FROM dbops.fn_pgtap_crea_ordine('rls ordini');
--   -- il secondo ordine dello STESSO cliente (rev 20261022-10):
--   SELECT * FROM dbops.fn_pgtap_crea_ordine(
--              'rls ordini 2', 'DRAFT',
--              (SELECT billing_account_id FROM tmp_o));
-- ⛔ Le righe NON le scrive: sono il caso del test.
-- ⭐ rev 2026-10-24 (20261024-23, brief-modello-documento-vendita N-1):
--   l'ordine NASCE nello stato iniziale (trigger della nascita); uno
--   stato diverso si raggiunge con dbops.fn_pgtap_porta_a_stato, sotto
--   i guard veri. Un passaggio che pretende cio' che il builder non
--   scrive (righe, indirizzi…) qui fallisce: il test lo scrive e porta
--   avanti da se'.
-- ⚠️ Senza contesto aperto, il mondo lo apre sull'operatore che
--   costruisce. Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_stato_id  config.stati_doc_ordini.id%TYPE;
    v_valuta_id config.valute.id%TYPE;
    v_ordine    vendite.ordini.id%TYPE;
    v_uid       vendite.ordini.uid%TYPE;
BEGIN
    -- Il guard sul parametro PRIMA di costruire: uno stato
    -- sbagliato non deve lasciare un mondo a meta'.
    SELECT s.id INTO v_stato_id
      FROM config.stati_doc_ordini s
     WHERE s.codice_interno = p_stato_codice_interno;

    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ordine: nessuno stato documento ordine con codice_interno = %',
            p_stato_codice_interno;
    END IF;

    SELECT c.emittente_fiscale_id, c.emittente_soggetto_ruolo_id,
           c.auth_user_id, c.billing_account_id, c.istanza_utility_id,
           c.cliente_soggetto_ruolo_id, c.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_cliente_del_builder(
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_ordine') c;

    SELECT v.id INTO v_valuta_id
      FROM config.valute v ORDER BY v.id LIMIT 1;

    INSERT INTO vendite.ordini (
        soggetto_ruolo_id, billing_account_id, utility_id,
        valuta_id, emittente_fiscale_id, meta)
    VALUES (v_cli_sr_id, v_ba_id, v_utility,
            v_valuta_id, v_ef_id,
            jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
    RETURNING id, uid INTO v_ordine, v_uid;

    -- Lo stato chiesto (rev 20261024-23): il documento e' nato nello stato
    -- iniziale; se il test ne vuole un altro, ci arriva per la matrice.
    IF v_stato_id IS DISTINCT FROM script.fn_stato_iniziale_id('config.stati_doc_ordini'::regclass) THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini'::regclass, v_ordine, p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_ordine, v_uid, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id, v_utility,
           v_stato_id, v_valuta_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint)
IS 'Fixture pgTAP: un ORDINE di vendita del mondo in una chiamata: azienda, operatore e cliente (dbops.fn_pgtap_crea_mondo_cliente) e la testata, con l''emittente del mondo, il suo billing account, la sua utility e la prima valuta del catalogo. Numero, anno, registro e fatturazione_trigger li assegnano i trigger del dominio, come in produzione. ⭐ Lo stato: l''ordine NASCE nello stato iniziale (trigger della nascita) e, se il secondo parametro ne chiede un altro, ci arriva per la matrice con dbops.fn_pgtap_porta_a_stato, sotto i guard veri; un passaggio che pretende cio'' che il builder non scrive (le righe, per la conferma) si ferma: il test chiede la bozza, scrive le righe e porta avanti da se''. Uno stato inesistente solleva prima di costruire. ⛔ NON scrive righe: sono il caso del test. ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE. Brief: brief-db-fixture-rls-documenti-costruiti. ⚠️ Terzo parametro (rev 2026-10-22, 20261022-10, richiesta BE R-3): il billing account di un cliente gia'' costruito, per il secondo ordine dello stesso cliente; verificato dell''azienda di chi agisce da dbops.fn_pgtap_cliente_ba_del_mondo, e un BA di un''altra azienda solleva. Rev 2026-10-24 (20261024-23, brief-modello-documento-vendita N-1): nascita in bozza; COMMENT allineato dal 20261024-29.';
```

</div>

---
{% include-markdown "signature-core.md" %}
