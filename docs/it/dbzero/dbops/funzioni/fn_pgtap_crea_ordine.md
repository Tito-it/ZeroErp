{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ordine.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ordine`

```sql
CREATE FUNCTION fn_pgtap_crea_ordine(p_etichetta text, p_stato_codice_interno character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ordine(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying)
 RETURNS TABLE(ordine_id bigint, ordine_uid uuid, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer, stato_doc_ordine_id bigint, valuta_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un ORDINE di vendita del mondo
--   in una chiamata: azienda, operatore, cliente e testata.
-- Uso:
--   CREATE TEMP TABLE tmp_o AS
--   SELECT * FROM dbops.fn_pgtap_crea_ordine('rls ordini');
-- ⛔ Le righe NON le scrive: sono il caso del test.
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

    SELECT m.emittente_fiscale_id, m.emittente_soggetto_ruolo_id,
           m.auth_user_id, m.billing_account_id, m.istanza_utility_id,
           m.cliente_soggetto_ruolo_id, m.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_crea_mondo_cliente(p_etichetta) m;

    SELECT v.id INTO v_valuta_id
      FROM config.valute v ORDER BY v.id LIMIT 1;

    INSERT INTO vendite.ordini (
        soggetto_ruolo_id, billing_account_id, utility_id,
        stato_doc_ordine_id, valuta_id, emittente_fiscale_id, meta)
    VALUES (v_cli_sr_id, v_ba_id, v_utility,
            v_stato_id, v_valuta_id, v_ef_id,
            jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
    RETURNING id, uid INTO v_ordine, v_uid;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_ordine, v_uid, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id, v_utility,
           v_stato_id, v_valuta_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ordine(p_etichetta text, p_stato_codice_interno character varying)
IS 'Fixture pgTAP: un ORDINE di vendita del mondo in una chiamata: azienda, operatore e cliente (dbops.fn_pgtap_crea_mondo_cliente) e la testata nello stato scelto alla nascita, con l''emittente del mondo, il suo billing account, la sua utility e la prima valuta del catalogo. Numero, anno, registro e fatturazione_trigger li assegnano i trigger del dominio, come in produzione. ⛔ NON scrive righe: sono il caso del test. ⛔ Non cambia stato: vendite.ordini ha un guard di transizione, lo stato si sceglie col secondo parametro. ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE. Brief: brief-db-fixture-rls-documenti-costruiti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
