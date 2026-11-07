{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ordine.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ordine`

```sql
CREATE FUNCTION fn_pgtap_crea_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ordine(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_data date DEFAULT NULL::date)
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
--   -- l'ordine di una data passata (rev 20261025-03):
--   SELECT * FROM dbops.fn_pgtap_crea_ordine('chiusure', p_data => DATE '2026-08-05');
-- ⛔ Le righe NON le scrive: sono il caso del test.
-- ⭐ rev 2026-10-24 (20261024-23, brief-modello-documento-vendita N-1):
--   l'ordine NASCE nello stato iniziale (trigger della nascita); uno
--   stato diverso si raggiunge con dbops.fn_pgtap_porta_a_stato, sotto
--   i guard veri. Un passaggio che pretende cio' che il builder non
--   scrive (righe, indirizzi…) qui fallisce: il test lo scrive e porta
--   avanti da se'.
-- ⭐ rev 2026-10-25 (20261025-03, brief-db-pgtap-bolla-e-reso-costruiti
--   D-1): la data dell'ordine si sceglie ALLA NASCITA, nell'INSERT: fuori
--   bozza e' congelata, e un UPDATE dopo il builder dipenderebbe
--   dall'ordine della fixture. NULL = il default della colonna.
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
    -- Lo stato dalla sede della traduzione codice -> id
    -- (script.fn_doc_stato_id): solo uno stato ATTIVO e' una destinazione.
    v_stato_id := script.fn_doc_stato_id('vendite.ordini'::regclass, p_stato_codice_interno);

    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ordine: nessuno stato documento ordine attivo con codice_interno = %',
            p_stato_codice_interno;
    END IF;

    SELECT c.emittente_fiscale_id, c.emittente_soggetto_ruolo_id,
           c.auth_user_id, c.billing_account_id, c.istanza_utility_id,
           c.cliente_soggetto_ruolo_id, c.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_cliente_del_builder(
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_ordine') c;

    -- La valuta dalla catena del dominio (vendite.fn_get_valuta_id:
    -- billing account, poi emittente, poi gestore), come la risolvono i
    -- trigger di default dei documenti: non la prima del catalogo.
    v_valuta_id := vendite.fn_get_valuta_id(v_ba_id, v_ef_sr_id);

    -- ⚠️ data e' NOT NULL con un DEFAULT di tabella: NULL vuol dire
    --   «quello della tabella». Due rami invece di ricopiare qui il
    --   default: la sede del default resta il DDL.
    IF p_data IS NULL THEN
        INSERT INTO vendite.ordini (
            soggetto_ruolo_id, billing_account_id, utility_id,
            valuta_id, emittente_fiscale_id, meta)
        VALUES (v_cli_sr_id, v_ba_id, v_utility,
                v_valuta_id, v_ef_id,
                jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
        RETURNING id, uid INTO v_ordine, v_uid;
    ELSE
        INSERT INTO vendite.ordini (
            soggetto_ruolo_id, billing_account_id, utility_id,
            valuta_id, emittente_fiscale_id, data, meta)
        VALUES (v_cli_sr_id, v_ba_id, v_utility,
                v_valuta_id, v_ef_id, p_data,
                jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
        RETURNING id, uid INTO v_ordine, v_uid;
    END IF;

    -- Lo stato chiesto (rev 20261024-23): il documento e' nato nello stato
    -- iniziale; se il test ne vuole un altro, ci arriva per la matrice.
    IF v_stato_id IS DISTINCT FROM script.fn_doc_stato_iniziale_id('vendite.ordini'::regclass) THEN
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

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_data date)
IS 'Fixture pgTAP: un ORDINE di vendita del mondo in una chiamata: azienda, operatore e cliente (dbops.fn_pgtap_cliente_del_builder: quello del terzo parametro, verificato dell''azienda di chi agisce, o uno nuovo del mondo) e la testata, con l''emittente del mondo, il billing account, la sua utility e la valuta della catena del dominio (vendite.fn_get_valuta_id: billing account, poi emittente, poi gestore). Numero, anno, registro e fatturazione_trigger li assegnano i trigger del dominio, come in produzione. Quarto parametro: la data dell''ordine, scritta alla nascita (NULL = il default della colonna). Lo stato: lo traduce script.fn_doc_stato_id, quindi uno stato spento o inesistente solleva prima di costruire; l''ordine nasce nello stato iniziale della testata (script.fn_doc_stato_iniziale_id) e, se il secondo parametro ne chiede un altro, ci arriva per la matrice con dbops.fn_pgtap_porta_a_stato, sotto i guard veri; un passaggio che pretende cio'' che il builder non scrive (le righe, per la conferma) si ferma: il test chiede la bozza, scrive le righe e porta avanti da se''. ⛔ NON scrive righe: sono il caso del test (le scrive dbops.fn_pgtap_crea_ordine_con_righe). ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
