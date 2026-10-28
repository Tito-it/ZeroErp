{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_contratto.md" %}
# ⚙️ Funzione `fn_pgtap_crea_contratto`

```sql
CREATE FUNCTION fn_pgtap_crea_contratto(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_offerta_id bigint, p_valido_dal date, p_valido_al date, p_data date, p_listino_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_contratto(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_offerta_id bigint DEFAULT NULL::bigint, p_valido_dal date DEFAULT NULL::date, p_valido_al date DEFAULT NULL::date, p_data date DEFAULT NULL::date, p_listino_id bigint DEFAULT NULL::bigint)
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
--   -- il figlio di un'offerta ACCETTATA, poi annullato:
--   SELECT * FROM dbops.fn_pgtap_crea_contratto(
--              'figlio', 'ANNULLATO', NULL,
--              (SELECT offerta_id FROM tmp_offerta));
-- ⛔ Righe, eccezioni e scheda di fornitura NON le scrive: sono il
--   caso del test (un figlio le eredita dall'offerta, dalla push).
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
-- rev 2026-10-24 (20261024-28, brief-modello-documento-vendita
--   Q-2): p_offerta_id, il figlio nasce dalla push.
-- rev 2026-10-24 (20261024-33, R-2): periodo, data e listino del
--   test, alla madre.
-- rev 2026-10-26 (20261026-13, brief-modello-documento-vendita §11):
--   ATTIVO dal verbo, per la fixture degli stati (con la porta un
--   UPDATE dello stato e' rifiutato).
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
    v_ba_off    vendite.offerte_commerciali.billing_account_id%TYPE;
    -- CONTEGGIO dei legami da confermare all'annullo.
    v_legami    integer;
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

    -- 0-bis. L'offerta: il figlio ha il cliente della madre, e
    --    periodo e listino glieli da' la push.
    IF p_offerta_id IS NOT NULL
       AND (p_valido_dal IS NOT NULL OR p_valido_al IS NOT NULL
            OR p_data IS NOT NULL OR p_listino_id IS NOT NULL) THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_contratto: il figlio dell''offerta % nasce dalla push, che decide periodo, data e listino dall''offerta: non si chiedono insieme',
            p_offerta_id;
    END IF;
    IF p_offerta_id IS NOT NULL THEN
        SELECT o.billing_account_id INTO v_ba_off
          FROM vendite.offerte_commerciali o
         WHERE o.id = p_offerta_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_contratto: nessuna offerta con id = % visibile a chi agisce',
                p_offerta_id;
        END IF;
        IF p_billing_account_id IS NOT NULL
           AND p_billing_account_id IS DISTINCT FROM v_ba_off THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_contratto: il billing account % non e'' quello dell''offerta % (%): il figlio nasce sul cliente della madre',
                p_billing_account_id, p_offerta_id, v_ba_off;
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
               p_etichetta, COALESCE(p_billing_account_id, v_ba_off), 'fn_pgtap_crea_contratto') c;

    IF p_offerta_id IS NOT NULL THEN
        -- 2-3. Il figlio nasce dalla push: listino, indirizzi,
        --    righe e utility dall'offerta; stato e idempotenza li
        --    giudica lei.
        v_contratto := vendite.fn_push_offerta_a_contratto(p_offerta_id, NULL, false);

        SELECT k.numero INTO v_numero
          FROM vendite.contratti k
         WHERE k.id = v_contratto;
    ELSE
        -- 2. Il listino, solo per ATTIVO: un contratto si attiva su un
        --    listino con una versione attiva, o con una riga AGGIUNTA
        --    con prezzo (trgfn_contratti_freeze_listino_versione). Le
        --    righe sono del test; il listino del mondo e' quello di
        --    chi agisce, per l'utility del cliente
        --    (dbops.fn_pgtap_crea_listino). DRAFT e ANNULLATO nascono
        --    senza: il listino lo sceglie il test.
        --    Il listino del test, se lo da' (rev 20261024-33).
        v_listino := p_listino_id;
        IF p_stato_codice_interno = 'ATTIVO' AND v_listino IS NULL THEN
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
                       'valido_dal',           p_valido_dal,
                       'valido_al',            p_valido_al,
                       'data',                 p_data,
                       'meta', jsonb_build_object('test_scope', 'pgtap_' || p_etichetta)))) c;
    END IF;

    -- 4. Lo stato, per la strada dell'applicazione.
    IF p_stato_codice_interno = 'ATTIVO' THEN
        -- Il verbo, dalla fixture degli stati (rev 2026-10-26): concede
        -- l'azione del passaggio all'operatore. Il guard di transizione
        -- giudica: prezzi, indirizzi, righe, contratto sovrapposto.
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, v_contratto, 'ATTIVO');
    ELSIF p_stato_codice_interno = 'ANNULLATO' THEN
        -- Il verbo. I legami (un figlio ha la sua offerta) si
        -- dichiarano come fa chi conferma: contati dalla sede unica.
        SELECT count(*)::integer INTO v_legami
          FROM vendite.fn_documento_legami('CONTRATTO', v_contratto);
        PERFORM vendite.fn_annulla_contratto(v_contratto, NULLIF(v_legami, 0));
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

COMMENT ON FUNCTION dbops.fn_pgtap_crea_contratto(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_offerta_id bigint, p_valido_dal date, p_valido_al date, p_data date, p_listino_id bigint)
IS 'Fixture pgTAP (e smoke): un CONTRATTO del mondo in una chiamata — azienda, operatore e cliente (dbops.fn_pgtap_crea_mondo_cliente) e la testata nello stato scelto — e ritorna tutte le chiavi. ⭐ Nasce dalla MADRE di produzione vendite.fn_create_contratto (numero, testata DRAFT, indirizzo di default), con l''emittente di chi agisce dichiarato. ⚠️ Terzo parametro: il billing account di un cliente gia'' costruito (per esempio quello di una commessa, perche'' un contratto citato da una riga deve essere del BA della sua commessa); viene verificato, e un BA di un''altra azienda solleva. ⭐ Quarto parametro: l''offerta da cui il contratto nasce, dalla push vendite.fn_push_offerta_a_contratto (stato ACCETTATA e idempotenza li giudica lei; listino, indirizzi, righe e utility dall''offerta), sul cliente dell''offerta: un billing account diverso solleva. Quinto-ottavo parametro (rev 20261024-33): periodo (valido_dal, valido_al), data e listino del test, passati alla madre; NULL = quelli della madre, e con ATTIVO senza listino il builder ne costruisce uno del mondo; insieme al figlio di un''offerta sollevano (li decide la push). Stati (D-2 di Tid, 2026-10-21): DRAFT; ATTIVO per la strada del guard di transizione (senza righe nessun motivo scatta; un secondo ATTIVO sovrapposto sullo stesso BA lo rifiuta il modello); ANNULLATO dal verbo vendite.fn_annulla_contratto, con i legami dichiarati da vendite.fn_documento_legami (il figlio ha la sua offerta). ⛔ CESSATO e ogni altro codice sollevano prima di scrivere: CESSATO vuole valido_al e passa da ATTIVO, e'' il caso del test. ⛔ NON scrive righe, eccezioni ne'' scheda di fornitura. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper. Richiesta BE R-1 del 2026-10-21 (smoke-group-attivita-contratto). Rev 2026-10-22: il billing account del terzo parametro lo verifica il building block dbops.fn_pgtap_cliente_ba_del_mondo (regola del 2, estratto alla terza copia). Rev 2026-10-24 (20261024-28, brief-modello-documento-vendita Q-2): il figlio di un''offerta, DROP + CREATE; 20261024-33 (R-2): periodo, data e listino. Rev 2026-10-24 (20261024-40, §4-octies): col billing account del test non costruisce piu'' un cliente in piu'' (dbops.fn_pgtap_cliente_del_builder). rev 2026-10-26 (20261026-13, brief-modello-documento-vendita §11): ATTIVO dal verbo del contratto, attraverso dbops.fn_pgtap_porta_a_stato (la porta rifiuta l''UPDATE dello stato; la fixture concede emetti_contratto all''operatore).';
```

</div>

---
{% include-markdown "signature-core.md" %}
