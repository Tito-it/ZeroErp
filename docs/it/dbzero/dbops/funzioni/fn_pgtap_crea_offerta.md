{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_offerta.md" %}
# ⚙️ Funzione `fn_pgtap_crea_offerta`

```sql
CREATE FUNCTION fn_pgtap_crea_offerta(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_listino_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_offerta(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'BOZZA'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_listino_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(offerta_id bigint, offerta_codice text, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer, listino_id bigint, stato_doc_offerta_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un'OFFERTA COMMERCIALE del mondo in
--   una chiamata: azienda, operatore, cliente, listino e testata nello
--   stato chiesto. Vedi l'intestazione del changeSet.
-- Uso:
--   CREATE TEMP TABLE tmp_o AS
--   SELECT * FROM dbops.fn_pgtap_crea_offerta('guard offerta', 'EMESSA');
--   -- sul cliente di un'altra fixture:
--   SELECT * FROM dbops.fn_pgtap_crea_offerta(
--              'seconda', 'BOZZA', (SELECT billing_account_id FROM tmp_o));
-- ⛔ Eccezioni, righe e scheda di fornitura NON le scrive: sono il
--   caso del test. Un passaggio che le pretende fallisce qui: il test
--   le scrive e porta avanti da se' (dbops.fn_pgtap_porta_a_stato).
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_listino   vendite.offerte_commerciali.listino_id%TYPE;
    v_stato_id  vendite.offerte_commerciali.stato_doc_offerta_id%TYPE;
    v_offerta   vendite.offerte_commerciali.id%TYPE;
    v_codice    vendite.offerte_commerciali.codice%TYPE;
BEGIN
    -- 0. Lo stato si giudica PRIMA di costruire, dalla sede della
    --    traduzione codice -> id (script.fn_doc_stato_id): solo uno
    --    stato attivo e' una destinazione.
    IF script.fn_doc_stato_id('vendite.offerte_commerciali'::regclass, p_stato_codice_interno) IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_offerta: nessuno stato offerta attivo con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;

    -- 1. Il cliente: senza billing account il mondo intero, con
    --    quello di un'altra fixture l'azienda di chi agisce.
    SELECT c.emittente_fiscale_id, c.emittente_soggetto_ruolo_id,
           c.auth_user_id, c.billing_account_id, c.istanza_utility_id,
           c.cliente_soggetto_ruolo_id, c.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_cliente_del_builder(
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_offerta') c;

    -- 2. Il listino: quello del test, altrimenti uno del mondo per
    --    l'utility del cliente, con una versione attiva (l'emissione
    --    la congela).
    v_listino := p_listino_id;
    IF v_listino IS NULL THEN
        SELECT l.listino_id INTO v_listino
          FROM dbops.fn_pgtap_crea_listino(v_utility, p_etichetta) l;
    END IF;

    -- 3. La nascita, come dal backend: niente stato (lo mette il
    --    trigger della nascita), niente versione di listino (la
    --    congela l'emissione), niente codice (lo genera il trigger).
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, meta)
    VALUES (v_ef_id, v_ba_id, v_ist_id, v_utility,
            v_listino, (SELECT script.fn_data_operativa()),
            jsonb_build_object('test_scope', 'pgtap_' || p_etichetta))
    RETURNING id, codice INTO v_offerta, v_codice;

    -- L'indirizzo di default dall'anagrafica del cliente: la stessa
    -- chiamata del repository del backend alla creazione.
    PERFORM vendite.fn_doc_indirizzo_default('OFFERTA_COMMERCIALE', v_offerta);

    -- 4. Lo stato chiesto: il documento e' nato nello stato iniziale;
    --    se il test ne vuole un altro, ci arriva per la matrice, dal
    --    verbo, sotto i guard veri.
    IF script.fn_doc_stato_id('vendite.offerte_commerciali'::regclass, p_stato_codice_interno)
       IS DISTINCT FROM script.fn_doc_stato_iniziale_id('vendite.offerte_commerciali'::regclass) THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali'::regclass, v_offerta, p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    SELECT o.stato_doc_offerta_id INTO v_stato_id
      FROM vendite.offerte_commerciali o
     WHERE o.id = v_offerta;

    RETURN QUERY
    SELECT v_offerta, v_codice, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id, v_utility, v_listino, v_stato_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_offerta(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_listino_id bigint)
IS 'Fixture pgTAP: un''OFFERTA COMMERCIALE del mondo in una chiamata. Il cliente da dbops.fn_pgtap_cliente_del_builder (il mondo intero, o il billing account di un''altra fixture verificato sull''azienda di chi agisce); il listino del test, altrimenti dbops.fn_pgtap_crea_listino per l''utility del cliente; la testata nasce come dal backend, senza stato (trigger della nascita), senza versione di listino (la congela l''emissione) e senza codice (trigger), poi l''indirizzo di default da vendite.fn_doc_indirizzo_default. Lo stato chiesto (codice_interno) si giudica prima di costruire con script.fn_doc_stato_id e si raggiunge con dbops.fn_pgtap_porta_a_stato, per la matrice e dal verbo vendite.fn_cambia_stato_offerta, sotto i guard veri. Eccezioni, righe e scheda di fornitura non le scrive; SUPERATA, che e'' di processo, non la raggiunge. Esce con i vincoli IMMEDIATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
