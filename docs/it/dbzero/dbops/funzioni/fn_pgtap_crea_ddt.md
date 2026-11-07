{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ddt.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ddt`

```sql
CREATE FUNCTION fn_pgtap_crea_ddt(p_billing_account_id bigint, p_destinatario_sr_id bigint, p_causale_codice character varying, p_magazzino_id bigint, p_magazzino_arrivo_id bigint, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ddt(p_billing_account_id bigint, p_destinatario_sr_id bigint, p_causale_codice character varying, p_magazzino_id bigint DEFAULT NULL::bigint, p_magazzino_arrivo_id bigint DEFAULT NULL::bigint, p_data date DEFAULT NULL::date)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-25 (20261025-33, brief-db-pgtap-reso-costruito E-5): p_data,
--   la data della bolla alla nascita (NULL = data operativa, come prima).
-- rev 2026-10-20 (20261020-62, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi DDT diventa DDT_VENDITA, il codice della
--   sorgente; firma e RETURNS ancorati.
-- Scopo: una bolla in bozza per un pgTAP, costruita e non pescata.
-- Uso: v_ddt := dbops.fn_pgtap_crea_ddt(<ba>, <sr cliente>, 'VENDITA', <mag>);
DECLARE
    v_ef      vendite.ddt.emittente_fiscale_id%TYPE;
    v_draft   config.stati_doc_ddt.id%TYPE;
    v_causale config.causali_trasporto.id%TYPE;
    v_utility vendite.ddt.utility_id%TYPE;
    v_valuta  vendite.ddt.valuta_id%TYPE;
    v_id      vendite.ddt.id%TYPE;
BEGIN
    v_ef := script.fn_pgtap_emittente_operatore();
    IF v_ef IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_ddt: nessun emittente per l''operatore in sessione — chiamare prima fn_pgtap_set_contesto_operatore';
    END IF;
    -- La bolla nasce nello stato iniziale della testata, dalla sede
    -- (script.fn_doc_stato_iniziale_id), non da un codice scritto qui.
    v_draft := script.fn_doc_stato_iniziale_id('vendite.ddt'::regclass);
    SELECT c.id INTO v_causale FROM config.causali_trasporto c WHERE c.codice = script.fn_codice_normalizzato(p_causale_codice) AND c.attivo;
    IF v_draft IS NULL OR v_causale IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_ddt: stato iniziale della bolla o causale di trasporto % assenti — sono seed di 80_data', p_causale_codice;
    END IF;
    SELECT ba.utility_id INTO v_utility FROM anagrafiche.billing_account ba WHERE ba.id = p_billing_account_id;
    -- La valuta dalla catena del dominio (vendite.fn_get_valuta_id:
    -- billing account, poi emittente, poi gestore), come la risolvono i
    -- trigger di default dei documenti: non la prima del catalogo.
    v_valuta := vendite.fn_get_valuta_id(
                    p_billing_account_id,
                    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = v_ef));

    INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                             billing_account_id, utility_id, valuta_id, emittente_fiscale_id,
                             causale_trasporto_id, magazzino_id, magazzino_arrivo_id,
                             storicizza, meta)
    VALUES (COALESCE(p_data, (SELECT script.fn_data_operativa())), v_draft, p_destinatario_sr_id,
            p_billing_account_id, v_utility, v_valuta, v_ef,
            v_causale, p_magazzino_id, p_magazzino_arrivo_id,
            false, jsonb_build_object('test_scope', 'pgtap_crea_ddt'))
    RETURNING id INTO v_id;

    -- Gli indirizzi che l'emissione pretende per l'ambito DDT.
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_id, ti.id, '{"display":"pgtap"}'::jsonb
      FROM config.tipi_indirizzi ti
     WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA', NULL))
    ON CONFLICT DO NOTHING;

    SET CONSTRAINTS ALL IMMEDIATE;
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ddt(p_billing_account_id bigint, p_destinatario_sr_id bigint, p_causale_codice character varying, p_magazzino_id bigint, p_magazzino_arrivo_id bigint, p_data date)
IS 'Fixture pgTAP: una bolla nello stato iniziale della testata (script.fn_doc_stato_iniziale_id) dell''emittente dell''operatore in sessione (script.fn_pgtap_emittente_operatore), per il cliente passato dal test (costruito dal suo mondo, non pescato), con la causale di trasporto per codice (normalizzato con script.fn_codice_normalizzato), la data (NULL = data operativa), i magazzini scelti (NULL = il default del predefinito) e gli indirizzi obbligatori dell''ambito DDT_VENDITA. La valuta dalla catena del dominio, vendite.fn_get_valuta_id (billing account, poi emittente, poi gestore), come la risolvono i trigger di default. Le righe restano al test. Esce con i vincoli IMMEDIATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
