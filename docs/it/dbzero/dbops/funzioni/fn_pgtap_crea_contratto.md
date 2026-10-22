{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_contratto.md" %}
# ⚙️ Funzione `fn_pgtap_crea_contratto`

```sql
CREATE FUNCTION fn_pgtap_crea_contratto(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_contratto(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(contratto_id bigint, numero character varying, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer, stato_doc_contratto_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP (o a uno smoke) un CONTRATTO del
--   mondo in una chiamata — azienda, operatore, cliente e testata
--   nello stato scelto — nato dalla madre di produzione.
-- Uso:
--   CREATE TEMP TABLE tmp_k AS
--   SELECT * FROM dbops.fn_pgtap_crea_contratto('atto', 'ATTIVO');
--   -- il contratto del cliente di un'altra fixture:
--   SELECT * FROM dbops.fn_pgtap_crea_contratto(
--              'atto', 'ATTIVO',
--              (SELECT billing_account_id FROM tmp_commessa));
-- ⛔ Righe, eccezioni e scheda di fornitura NON le scrive: sono il
--   caso del test.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_contratto vendite.contratti.id%TYPE;
    v_numero    vendite.contratti.numero%TYPE;
    v_stato_id  vendite.contratti.stato_doc_contratto_id%TYPE;
    v_listino   vendite.contratti.listino_id%TYPE;
BEGIN
    -- 0. Lo stato si giudica PRIMA di costruire (D-2 di Tid):
    --    CESSATO vuole valido_al e passa da ATTIVO con la regola
    --    della cessazione, ed e' il caso del test.
    IF p_stato_codice_interno IS NULL
       OR p_stato_codice_interno NOT IN ('DRAFT', 'ATTIVO', 'ANNULLATO') THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_contratto: stato % non costruibile dal builder (DRAFT, ATTIVO, ANNULLATO). CESSATO vuole valido_al e passa da ATTIVO: lo costruisce il test',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;

    -- 1. Il mondo. Senza p_billing_account_id costruisce anche il
    --    cliente; con, riusa quello e prende solo l'azienda di chi
    --    agisce (il mondo la riusa quando un contesto c'e').
    SELECT m.emittente_fiscale_id, m.emittente_soggetto_ruolo_id,
           m.auth_user_id, m.billing_account_id, m.istanza_utility_id,
           m.cliente_soggetto_ruolo_id, m.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_crea_mondo_cliente(p_etichetta) m;

    IF p_billing_account_id IS NOT NULL THEN
        -- ⚠️ Il BA chiesto si VERIFICA prima di usarlo, dal building
        --   block (rev 20261022, regola del 2): uno di un'altra azienda
        --   solleva qui, nominando questo builder, invece che sul guard
        --   emittente/BA della testata piu' avanti.
        SELECT c.billing_account_id, c.istanza_utility_id,
               c.cliente_soggetto_ruolo_id, c.utility_id
          INTO v_ba_id, v_ist_id, v_cli_sr_id, v_utility
          FROM dbops.fn_pgtap_cliente_ba_del_mondo(
                   p_billing_account_id, v_ef_sr_id, 'fn_pgtap_crea_contratto') c;
    END IF;

    -- 2. Il listino, solo per ATTIVO: un contratto si attiva su un
    --    listino con una versione attiva, o con una riga AGGIUNTA
    --    con prezzo (trgfn_contratti_freeze_listino_versione). Le
    --    righe sono del test; il listino del mondo e' quello di
    --    chi agisce, per l'utility del cliente
    --    (dbops.fn_pgtap_crea_listino). DRAFT e ANNULLATO nascono
    --    senza: il listino lo sceglie il test.
    IF p_stato_codice_interno = 'ATTIVO' THEN
        SELECT l.listino_id INTO v_listino
          FROM dbops.fn_pgtap_crea_listino(v_utility, p_etichetta) l;
    END IF;

    -- 3. La nascita dalla madre: numero, testata DRAFT, indirizzo
    --    di default. L'emittente si dichiara: e' quello di chi
    --    agisce, a cui il BA e' legato.
    SELECT c.contratto_id, c.numero
      INTO v_contratto, v_numero
      -- jsonb_strip_nulls: senza listino la chiave non si
      -- manda, e la colonna prende il suo default.
      FROM vendite.fn_create_contratto(
               jsonb_strip_nulls(jsonb_build_object(
                   'billing_account_id',   v_ba_id,
                   'istanza_utility_id',   v_ist_id,
                   'utility_id',           v_utility,
                   'emittente_fiscale_id', v_ef_id,
                   'listino_id',           v_listino,
                   'meta', jsonb_build_object('test_scope', 'pgtap_' || p_etichetta)))) c;

    -- 4. Lo stato, per la strada dell'applicazione.
    IF p_stato_codice_interno = 'ATTIVO' THEN
        -- Il guard di transizione giudica: prezzi, indirizzi,
        -- righe, contratto sovrapposto.
        UPDATE vendite.contratti k
           SET stato_doc_contratto_id = (SELECT s.id
                                           FROM config.stati_doc_contratti s
                                          WHERE s.codice_interno = 'ATTIVO')
         WHERE k.id = v_contratto;
    ELSIF p_stato_codice_interno = 'ANNULLATO' THEN
        -- Il verbo: alla nascita nessun legame da confermare.
        PERFORM vendite.fn_annulla_contratto(v_contratto);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    SELECT k.stato_doc_contratto_id INTO v_stato_id
      FROM vendite.contratti k
     WHERE k.id = v_contratto;

    RETURN QUERY
    SELECT v_contratto, v_numero, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id, v_utility, v_stato_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_contratto(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint)
IS 'Fixture pgTAP (e smoke): un CONTRATTO del mondo in una chiamata — azienda, operatore e cliente (dbops.fn_pgtap_crea_mondo_cliente) e la testata nello stato scelto — e ritorna tutte le chiavi. ⭐ Nasce dalla MADRE di produzione vendite.fn_create_contratto (numero, testata DRAFT, indirizzo di default), con l''emittente di chi agisce dichiarato. ⚠️ Terzo parametro: il billing account di un cliente gia'' costruito (per esempio quello di una commessa, perche'' un contratto citato da una riga deve essere del BA della sua commessa); viene verificato, e un BA di un''altra azienda solleva. Stati (D-2 di Tid, 2026-10-21): DRAFT; ATTIVO per la strada del guard di transizione (senza righe nessun motivo scatta; un secondo ATTIVO sovrapposto sullo stesso BA lo rifiuta il modello); ANNULLATO dal verbo vendite.fn_annulla_contratto. ⛔ CESSATO e ogni altro codice sollevano prima di scrivere: CESSATO vuole valido_al e passa da ATTIVO, e'' il caso del test. ⛔ NON scrive righe, eccezioni ne'' scheda di fornitura. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper. Richiesta BE R-1 del 2026-10-21 (smoke-group-attivita-contratto). Rev 2026-10-22: il billing account del terzo parametro lo verifica il building block dbops.fn_pgtap_cliente_ba_del_mondo (regola del 2, estratto alla terza copia).';
```

</div>

---
{% include-markdown "signature-core.md" %}
