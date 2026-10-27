{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ddt_senza_ordine.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ddt_senza_ordine`

```sql
CREATE FUNCTION fn_pgtap_crea_ddt_senza_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_quantita numeric, p_prezzo numeric, p_articolo_id uuid, p_causale_codice character varying, p_data date, p_magazzino_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ddt_senza_ordine(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'CONSEGNATO'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_quantita numeric DEFAULT NULL::numeric, p_prezzo numeric DEFAULT NULL::numeric, p_articolo_id uuid DEFAULT NULL::uuid, p_causale_codice character varying DEFAULT 'VENDITA'::character varying, p_data date DEFAULT NULL::date, p_magazzino_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint, quantita numeric, articolo_id uuid, billing_account_id bigint, cliente_soggetto_ruolo_id bigint, emittente_fiscale_id bigint, auth_user_id integer, stato_doc_ddt_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una BOLLA SENZA ORDINE con una
--   riga prezzata, nello stato chiesto (default CONSEGNATO), per la
--   strada vera del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_b AS
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('rls resi',
--              p_billing_account_id => (SELECT billing_account_id FROM _m));
--   -- in bozza, a una data, con la causale del caso:
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('visione', 'DRAFT',
--              p_causale_codice => 'CONTO_VISIONE', p_data => DATE '2101-01-15');
-- ⛔ Merce gestita a magazzino: rifiutata (i test che muovono merce
--   scrivono righe e prelievi da se').
-- ⚠️ Senza contesto aperto, il mondo lo apre sull'operatore che
--   costruisce. Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_stato_id   config.stati_doc_ddt.id%TYPE;
    v_abortito   config.stati_doc_ddt.is_abortito%TYPE;
    v_ba_id      anagrafiche.billing_account.id%TYPE;
    v_cli_sr_id  anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_user_id    anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_gestito    catalogo.articoli.gestito_a_magazzino%TYPE;
    v_articolo   catalogo.articoli.id%TYPE;
    v_iva_id     config.iva.id%TYPE;
    v_ddt        vendite.ddt.id%TYPE;
    v_riga       vendite.ddt_righe.id%TYPE;
BEGIN
    -- 0. I parametri si giudicano PRIMA di costruire.
    SELECT s.id, s.is_abortito INTO v_stato_id, v_abortito
      FROM config.stati_doc_ddt s
     WHERE s.codice_interno = p_stato_codice_interno
       AND s.attivo IS TRUE;
    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_senza_ordine: nessuno stato attivo della bolla con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;
    IF v_abortito THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_senza_ordine: % e'' uno stato abortito — la bolla si annulla col verbo vendite.fn_annulla_ddt: chiedere EMESSO e annullare dal test',
            p_stato_codice_interno;
    END IF;

    IF p_articolo_id IS NOT NULL THEN
        SELECT a.gestito_a_magazzino INTO v_gestito
          FROM catalogo.articoli a
         WHERE a.id = p_articolo_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_ddt_senza_ordine: nessun articolo con id = %', p_articolo_id;
        END IF;
        IF v_gestito THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_ddt_senza_ordine: l''articolo % e'' gestito a magazzino — una bolla che muove merce ha righe e prelievi scritti dal test (dbops.fn_pgtap_crea_ddt)',
                p_articolo_id;
        END IF;
    END IF;

    -- 1. Il cliente, nell'azienda di chi agisce.
    SELECT c.billing_account_id, c.cliente_soggetto_ruolo_id, c.auth_user_id
      INTO v_ba_id, v_cli_sr_id, v_user_id
      FROM dbops.fn_pgtap_cliente_del_builder(
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_ddt_senza_ordine') c;

    -- 2. La testata: causale, magazzino, data alla nascita, indirizzi.
    --    (La causale inesistente la rifiuta il builder della testata.)
    v_ddt := dbops.fn_pgtap_crea_ddt(v_ba_id, v_cli_sr_id, p_causale_codice,
                                     p_magazzino_id, NULL, p_data);

    -- 3. La riga, in bozza: senza ordine il prezzo e l'aliquota li
    --    porta lei. L'articolo si costruisce: il catalogo, da zero, e' vuoto.
    v_articolo := COALESCE(p_articolo_id, dbops.fn_pgtap_crea_articolo(
        ('PGT-BOL-' || substr(md5(clock_timestamp()::text || v_ddt::text), 1, 12))::varchar,
        false));

    SELECT i.id INTO v_iva_id
      FROM config.iva i
     WHERE i.attivo IS TRUE
     ORDER BY i.id
     LIMIT 1;

    INSERT INTO vendite.ddt_righe (
        ddt_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, meta)
    VALUES (
        v_ddt, 1, v_articolo, left('Fixture pgTAP: ' || p_etichetta, 150),
        COALESCE(p_quantita, 10), COALESCE(p_quantita, 10), COALESCE(p_prezzo, 25),
        v_iva_id, jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
    RETURNING id INTO v_riga;

    -- 4. Lo stato chiesto, per la matrice: la bolla e' nata nello
    --    stato iniziale.
    IF v_stato_id IS DISTINCT FROM script.fn_doc_stato_iniziale_id('vendite.ddt'::regclass) THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt'::regclass, v_ddt, p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT d.id, d.uid, r.id, r.quantita, r.articolo_id,
           v_ba_id, v_cli_sr_id, d.emittente_fiscale_id, v_user_id, d.stato_doc_ddt_id
      FROM vendite.ddt d
      JOIN vendite.ddt_righe r ON r.id = v_riga
     WHERE d.id = v_ddt;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ddt_senza_ordine(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_quantita numeric, p_prezzo numeric, p_articolo_id uuid, p_causale_codice character varying, p_data date, p_magazzino_id bigint)
IS 'Fixture pgTAP: una BOLLA SENZA ORDINE con una riga prezzata, nello stato chiesto (secondo parametro, default CONSEGNATO), per la strada vera del dominio. ⭐ Esiste per la TRAPPOLA D''ORDINE che i file ricopiavano: testata con causale e indirizzi, riga che senza ordine porta da se'' prezzo e aliquota su un articolo merce, passaggi per la matrice. Il cliente: quello del terzo parametro o uno nuovo (dbops.fn_pgtap_cliente_del_builder, che apre il contesto se manca). La testata da dbops.fn_pgtap_crea_ddt: causale per codice (p_causale_codice, default VENDITA; inesistente solleva), magazzino (p_magazzino_id), data alla nascita (p_data; NULL = data operativa), indirizzi obbligatori. UNA riga di p_quantita (default 10) a p_prezzo (default 25), prima IVA attiva, articolo p_articolo_id o costruito (merce non gestita); un articolo gestito a magazzino solleva (la bolla muoverebbe merce: righe e prelievi li scrive il test, su dbops.fn_pgtap_crea_ddt). Lo stato con dbops.fn_pgtap_porta_a_stato, sotto i guard veri; uno stato abortito si rifiuta prima di costruire (l''annullo e'' del verbo vendite.fn_annulla_ddt). Restituisce bolla, riga con la sua quantita'' base, articolo, cliente, emittente, operatore e stato. Gemello di dbops.fn_pgtap_crea_ddt_da_ordine. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper. Brief: brief-db-pgtap-reso-costruito (E-5), 2026-10-25. Rev 2026-10-27 (20261027-35, brief-modello-documento-vendita §15.13): lo stato iniziale dalla testata (vendite.ddt) con script.fn_doc_stato_iniziale_id, non dal vocabolario.';
```

</div>

---
{% include-markdown "signature-core.md" %}
