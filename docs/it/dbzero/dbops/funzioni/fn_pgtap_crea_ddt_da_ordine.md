{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ddt_da_ordine.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ddt_da_ordine`

```sql
CREATE FUNCTION fn_pgtap_crea_ddt_da_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_quantita numeric, p_prezzo numeric, p_articolo_id uuid, p_fatturazione_trigger character varying, p_ordine_id bigint, p_qta_da_evadere numeric, p_righe jsonb, p_data date, p_causale_codice character varying, p_data_ordine date, p_righe_ordine jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ddt_da_ordine(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'CONSEGNATO'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_quantita numeric DEFAULT NULL::numeric, p_prezzo numeric DEFAULT NULL::numeric, p_articolo_id uuid DEFAULT NULL::uuid, p_fatturazione_trigger character varying DEFAULT NULL::character varying, p_ordine_id bigint DEFAULT NULL::bigint, p_qta_da_evadere numeric DEFAULT NULL::numeric, p_righe jsonb DEFAULT NULL::jsonb, p_data date DEFAULT NULL::date, p_causale_codice character varying DEFAULT 'VENDITA'::character varying, p_data_ordine date DEFAULT NULL::date, p_righe_ordine jsonb DEFAULT NULL::jsonb)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint, quantita numeric, ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint, articolo_id uuid, billing_account_id bigint, cliente_soggetto_ruolo_id bigint, emittente_fiscale_id bigint, auth_user_id integer, stato_doc_ddt_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una BOLLA nata da un ordine
--   confermato, nello stato chiesto (default CONSEGNATO), per la
--   strada vera del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_b AS
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi');
--   -- due spedizioni dalla stessa riga, 4 e 6:
--   CREATE TEMP TABLE tmp_a AS
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('sped', p_quantita => 10,
--                                                    p_qta_da_evadere => 4);
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('sped',
--              p_ordine_id => (SELECT ordine_id FROM tmp_a), p_qta_da_evadere => 6);
--   -- la bolla in bozza, per scriverle cio' che il test prova:
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('bozza', 'DRAFT');
-- rev 2026-10-25 (20261025-02): uno stato abortito si rifiuta prima
--   di costruire — la bolla da ordine ha i legami, e il suo annullo
--   passa dal verbo vendite.fn_annulla_ddt (caso del test).
-- rev 2026-10-25 (20261025-32, brief-db-pgtap-reso-costruito E-1): l'ordine
--   costruito viene da dbops.fn_pgtap_crea_ordine_con_righe (la copia della
--   strada che stava qui si ritira); p_righe_ordine inoltra piu' righe,
--   sconto e date di consegna.
-- rev 2026-10-25 (20261025-04, D-1): p_data_ordine, la data dell'ordine
--   costruito (dbops.fn_pgtap_crea_ordine la scrive alla nascita). Chi da'
--   alla bolla una data passata da' anche quella dell'ordine: una bolla piu'
--   vecchia del suo ordine e' una fixture incoerente col modello.
-- ⛔ Restituisce la PRIMA riga della bolla: con piu' righe il test
--   le legge da se'.
-- ⚠️ Senza contesto aperto, il mondo lo apre sull'operatore che
--   costruisce. Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_stato_id   config.stati_doc_ddt.id%TYPE;
    v_abortito   config.stati_doc_ddt.is_abortito%TYPE;
    v_causale_id config.causali_trasporto.id%TYPE;
    v_ordine     vendite.ordini.id%TYPE;
    v_ordine_uid vendite.ordini.uid%TYPE;
    v_riga_ord   vendite.ordini_righe.id%TYPE;
    v_ba_id      anagrafiche.billing_account.id%TYPE;
    v_cli_sr_id  vendite.ordini.soggetto_ruolo_id%TYPE;
    v_ef_id      vendite.ordini.emittente_fiscale_id%TYPE;
    v_user_id    anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_righe      jsonb;      -- la grammatica della madre
    v_ddt        vendite.ddt.id%TYPE;
    v_n          integer;    -- righe d'ordine attive: un conteggio
BEGIN
    -- 0. I parametri si giudicano PRIMA di costruire: un errore
    --    del chiamante non deve lasciare un mondo a meta'.
    SELECT s.id, s.is_abortito INTO v_stato_id, v_abortito
      FROM config.stati_doc_ddt s
     WHERE s.codice_interno = p_stato_codice_interno
       AND s.attivo IS TRUE;
    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_da_ordine: nessuno stato attivo della bolla con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;

    -- Uno stato abortito non e' una strada della fixture: la bolla
    -- nata da un ordine ha i legami, e il loro annullo lo dichiara
    -- il verbo (E_DOC_ANNULLO_CON_LEGAMI sull'UPDATE della matrice).
    IF v_abortito THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_da_ordine: % e'' uno stato abortito — la bolla nata da un ordine ha i legami e si annulla col verbo vendite.fn_annulla_ddt: chiedere EMESSO e annullare dal test',
            p_stato_codice_interno;
    END IF;

    SELECT c.id INTO v_causale_id
      FROM config.causali_trasporto c
     WHERE c.codice = p_causale_codice
       AND c.attivo IS TRUE;
    IF v_causale_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_da_ordine: nessuna causale di trasporto attiva con codice = %',
            coalesce(p_causale_codice::text, 'NULL');
    END IF;

    IF p_righe IS NOT NULL AND p_qta_da_evadere IS NOT NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_da_ordine: p_righe e p_qta_da_evadere insieme — la quantita'' da evadere sta gia'' in p_righe';
    END IF;

    -- Cliente, riga e trigger sono dell'ordine: con un ordine
    -- gia' costruito non si scelgono qui.
    IF p_ordine_id IS NOT NULL
       AND (p_billing_account_id IS NOT NULL OR p_quantita IS NOT NULL
            OR p_prezzo IS NOT NULL OR p_articolo_id IS NOT NULL
            OR p_fatturazione_trigger IS NOT NULL OR p_data_ordine IS NOT NULL
            OR p_righe_ordine IS NOT NULL) THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_da_ordine: con p_ordine_id cliente, righe, data e trigger di fatturazione sono quelli dell''ordine — non si passano';
    END IF;

    -- 1. L'ordine confermato: quello del test, o uno del builder dell'ordine
    --    con le righe (la strada sta li', una volta).
    IF p_ordine_id IS NULL THEN
        SELECT o.ordine_id, o.ordine_uid, o.billing_account_id,
               o.cliente_soggetto_ruolo_id, o.emittente_fiscale_id, o.auth_user_id
          INTO v_ordine, v_ordine_uid, v_ba_id, v_cli_sr_id, v_ef_id, v_user_id
          FROM dbops.fn_pgtap_crea_ordine_con_righe(
                   p_etichetta, 'CONFERMATO', p_billing_account_id,
                   p_quantita, p_prezzo, p_articolo_id, p_fatturazione_trigger,
                   p_data_ordine, p_righe_ordine) o;
    ELSE
        SELECT o.id, o.uid, o.billing_account_id, o.soggetto_ruolo_id, o.emittente_fiscale_id
          INTO v_ordine, v_ordine_uid, v_ba_id, v_cli_sr_id, v_ef_id
          FROM vendite.ordini o
         WHERE o.id = p_ordine_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_ddt_da_ordine: ordine id = % non esiste o non e'' visibile',
                p_ordine_id;
        END IF;
        v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    END IF;

    -- La quantita' da evadere vale per LA riga: con piu' righe il test dice
    -- quale con p_righe.
    IF p_qta_da_evadere IS NOT NULL THEN
        SELECT count(*), min(r.id) INTO v_n, v_riga_ord
          FROM vendite.ordini_righe r
         WHERE r.ordine_id = v_ordine
           AND r.attivo IS TRUE;
        IF v_n <> 1 THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_ddt_da_ordine: p_qta_da_evadere vuole un ordine con una sola riga attiva (l''ordine % ne ha %) — usare p_righe',
                v_ordine, v_n;
        END IF;
    END IF;

    -- 2. La bolla dalla madre: tutto il residuo, o cio' che il test chiede.
    v_righe := COALESCE(p_righe,
        CASE WHEN p_qta_da_evadere IS NOT NULL THEN
            jsonb_build_array(jsonb_build_object(
                'ordine_riga_id', v_riga_ord, 'qta_da_evadere', p_qta_da_evadere))
        END);
    v_ddt := vendite.fn_genera_ddt_da_ordine(v_ordine, v_righe, p_data);

    -- 3. Cio' che l'emissione pretende: la causale e gli indirizzi
    --    obbligatori che la cascata dall'ordine non ha portato.
    UPDATE vendite.ddt d
       SET causale_trasporto_id = v_causale_id
     WHERE d.id = v_ddt;

    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_ddt, ti.id, jsonb_build_object('display', 'pgTAP ' || ti.codice_interno)
      FROM config.tipi_indirizzi ti
     WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti(
               'DDT_VENDITA',
               (SELECT array_agg(di.tipo_indirizzo_id)::integer[]
                  FROM vendite.ddt_indirizzi di
                 WHERE di.ddt_id = v_ddt)))
    ON CONFLICT DO NOTHING;

    -- 4. Lo stato chiesto, per la matrice: la bolla e' nata nello
    --    stato iniziale (trigger della nascita).
    IF v_stato_id IS DISTINCT FROM script.fn_doc_stato_iniziale_id('vendite.ddt'::regclass) THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt'::regclass, v_ddt, p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT d.id, d.uid, dr.id, dr.quantita,
           v_ordine, v_ordine_uid, f.ordine_riga_id, dr.articolo_id,
           v_ba_id, v_cli_sr_id, v_ef_id, v_user_id, d.stato_doc_ddt_id
      FROM vendite.ddt d
      JOIN LATERAL (
          SELECT r.id, r.quantita, r.articolo_id
            FROM vendite.ddt_righe r
           WHERE r.ddt_id = d.id
           ORDER BY r.riga_nr, r.id
           LIMIT 1) dr ON true
      LEFT JOIN LATERAL (
          SELECT ff.ordine_riga_id
            FROM vendite.ordini_righe_fulfillment ff
           WHERE ff.ddt_riga_id = dr.id
           ORDER BY ff.id
           LIMIT 1) f ON true
     WHERE d.id = v_ddt;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ddt_da_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_quantita numeric, p_prezzo numeric, p_articolo_id uuid, p_fatturazione_trigger character varying, p_ordine_id bigint, p_qta_da_evadere numeric, p_righe jsonb, p_data date, p_causale_codice character varying, p_data_ordine date, p_righe_ordine jsonb)
IS 'Fixture pgTAP: una BOLLA nata da un ORDINE confermato, nello stato chiesto (secondo parametro, default CONSEGNATO), per la strada vera del dominio. ⭐ Esiste per la TRAPPOLA D''ORDINE che ogni file ricopiava: ordine in bozza con la riga, conferma, bolla dalla madre vendite.fn_genera_ddt_da_ordine, causale e indirizzi che l''emissione pretende, passaggi per la matrice. L''ordine lo costruisce dbops.fn_pgtap_crea_ordine_con_righe, confermato (terzo parametro: il billing account di un cliente gia'' costruito): UNA riga di p_quantita (default 10) a p_prezzo (default 25), dell''articolo p_articolo_id o di uno costruito (merce non gestita), oppure le righe di p_righe_ordine (piu'' righe, sconto, date di consegna, nella grammatica di quel builder); il trigger di fatturazione p_fatturazione_trigger (scritto in bozza; NULL = quello ereditato dal billing account). p_data_ordine: la data dell''ordine costruito, scritta alla nascita (NULL = data operativa): chi da'' alla bolla una data passata da'' anche quella dell''ordine. Con p_ordine_id la bolla nasce invece da un ordine gia'' costruito e confermato dal test, e cliente, riga, data e trigger non si passano (solleva). La quantita'': tutto il residuo; p_qta_da_evadere per l''unica riga attiva dell''ordine; p_righe nella grammatica della madre (i due insieme sollevano). p_data: la data della bolla (NULL = data operativa). p_causale_codice: la causale di trasporto per codice (default VENDITA). Gli indirizzi obbligatori dell''ambito DDT_VENDITA che la cascata dall''ordine non ha portato li scrive come dbops.fn_pgtap_crea_ddt. Lo stato si raggiunge con dbops.fn_pgtap_porta_a_stato, sotto i guard veri: chi deve scrivere sulla bolla in bozza (una riga a mano, un legame, un prezzo tolto) la chiede in DRAFT e la porta avanti da se''. Restituisce bolla, PRIMA riga della bolla con la sua quantita'' base, ordine e riga d''ordine evasa, articolo, cliente, emittente, operatore e stato. Uno stato, una causale o un ordine inesistenti sollevano prima di costruire; cosi'' uno stato abortito (is_abortito, per esempio ANNULLATO): la bolla nata da un ordine ha i legami e il suo annullo passa dal verbo vendite.fn_annulla_ddt, che il test chiama dopo aver chiesto EMESSO. ⛔ La bolla in bozza per il magazzino, senza ordine, resta di dbops.fn_pgtap_crea_ddt. ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE. Brief: brief-db-pgtap-bolla-e-reso-costruiti (giro 1), 2026-10-25. Rev 20261025-02: lo stato abortito si rifiuta prima di costruire. Rev 20261025-04 (D-1): p_data_ordine, DROP + CREATE. Rev 20261025-32 (E-1): l''ordine dal builder dell''ordine con le righe, p_righe_ordine; DROP + CREATE. Rev 2026-10-27 (20261027-34, brief-modello-documento-vendita §15.13): lo stato iniziale dalla testata (vendite.ddt) con script.fn_doc_stato_iniziale_id, non dal vocabolario.';
```

</div>

---
{% include-markdown "signature-core.md" %}
