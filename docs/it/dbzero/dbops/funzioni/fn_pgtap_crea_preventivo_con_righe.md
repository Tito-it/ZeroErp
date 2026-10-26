# ⚙️ Funzione `fn_pgtap_crea_preventivo_con_righe`

```sql
CREATE FUNCTION fn_pgtap_crea_preventivo_con_righe(p_etichetta text, p_stato_codice_interno character varying, p_preventivo_id bigint, p_prezzo numeric, p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_preventivo_con_righe(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'EMESSO'::character varying, p_preventivo_id bigint DEFAULT NULL::bigint, p_prezzo numeric DEFAULT NULL::numeric, p_articolo_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(preventivo_id bigint, preventivo_uid uuid, preventivo_riga_id bigint, articolo_id uuid, billing_account_id bigint, emittente_fiscale_id bigint, auth_user_id integer, stato_doc_preventivo_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un PREVENTIVO con una riga
--   valida per l'emissione, nello stato chiesto (default
--   EMESSO), per la strada vera.
-- Uso:
--   CREATE TEMP TABLE tmp_p AS
--   SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('dash');
--   -- la testata del test, gia' in bozza, portata ad ACCETTATO:
--   SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('rif',
--              'ACCETTATO', p_preventivo_id => (SELECT id FROM tmp_t));
-- ⚠️ Senza contesto aperto, il mondo lo apre sull'operatore che
--   costruisce. Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_stato_id   config.stati_doc_preventivi.id%TYPE;
    v_preventivo vendite.preventivi.id%TYPE;
    v_ba_id      vendite.preventivi.billing_account_id%TYPE;
    v_ef_id      vendite.preventivi.emittente_fiscale_id%TYPE;
    v_user_id    anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_iva_id     config.iva.id%TYPE;
    v_natura_id  config.nature_vendita.id%TYPE;
    v_articolo   catalogo.articoli.id%TYPE;
    v_riga_id    vendite.preventivi_righe.id%TYPE;
BEGIN
    -- 0. I parametri si giudicano PRIMA di costruire.
    v_stato_id := script.fn_doc_stato_id('vendite.preventivi'::regclass, p_stato_codice_interno);
    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_preventivo_con_righe: nessuno stato attivo del preventivo con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;

    -- 1. La testata: quella del test, in bozza, o una nuova.
    IF p_preventivo_id IS NOT NULL THEN
        SELECT p.id, p.billing_account_id, p.emittente_fiscale_id
          INTO v_preventivo, v_ba_id, v_ef_id
          FROM vendite.preventivi p
         WHERE p.id = p_preventivo_id
           AND p.stato_doc_preventivo_id
               = script.fn_stato_iniziale_id('config.stati_doc_preventivi'::regclass);
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_preventivo_con_righe: preventivo id = % inesistente, invisibile o fuori bozza — le righe si scrivono in bozza',
                p_preventivo_id;
        END IF;
        v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    ELSE
        SELECT p.preventivo_id, p.billing_account_id, p.emittente_fiscale_id, p.auth_user_id
          INTO v_preventivo, v_ba_id, v_ef_id, v_user_id
          FROM dbops.fn_pgtap_crea_preventivo(p_etichetta, 'DRAFT') p;
    END IF;

    -- 2. La riga, in bozza. Il catalogo di sistema si SCEGLIE,
    --    col suo ORDER BY; l'articolo si costruisce (da zero il
    --    catalogo e' vuoto), di merce.
    SELECT i.id INTO v_iva_id
      FROM config.iva i
     WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
     ORDER BY i.id
     LIMIT 1;

    IF p_articolo_id IS NULL THEN
        SELECT nv.id INTO v_natura_id
          FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo IS TRUE
         ORDER BY nv.id
         LIMIT 1;
    END IF;

    v_articolo := COALESCE(p_articolo_id, dbops.fn_pgtap_crea_articolo(
        ('PGT-PRV-' || substr(md5(clock_timestamp()::text || v_preventivo::text), 1, 12))::varchar,
        false, p_natura_vendita_id => v_natura_id));

    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id,
                                          prezzo_unitario, qta_operativa)
    VALUES (v_preventivo, v_articolo, v_iva_id, COALESCE(p_prezzo, 10), 1)
    RETURNING id INTO v_riga_id;

    -- 3. Lo stato chiesto, per la matrice.
    IF v_stato_id IS DISTINCT FROM script.fn_stato_iniziale_id('config.stati_doc_preventivi'::regclass) THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi'::regclass, v_preventivo,
                                             p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT p.id, p.uid, v_riga_id, v_articolo, v_ba_id, v_ef_id, v_user_id,
           p.stato_doc_preventivo_id
      FROM vendite.preventivi p
     WHERE p.id = v_preventivo;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_preventivo_con_righe(p_etichetta text, p_stato_codice_interno character varying, p_preventivo_id bigint, p_prezzo numeric, p_articolo_id uuid)
IS 'Fixture pgTAP: un PREVENTIVO con una riga valida per l''emissione (articolo di merce costruito o p_articolo_id, prima aliquota positiva del catalogo, quantita 1, prezzo 10 o p_prezzo), nello stato chiesto (secondo parametro, default EMESSO), per la strada vera: la riga in bozza, poi lo stato per la matrice con dbops.fn_pgtap_porta_a_stato (il verbo, sotto la porta). ⭐ Esiste per la REGOLA DEL DOMINIO che i test ricopiavano: l''emissione chiede almeno una riga attiva (vendite.trgfn_preventivi_guard_transizione), e prima della porta i test emettevano preventivi senza righe. La testata e'' nuova (dbops.fn_pgtap_crea_preventivo, che resta senza righe) o quella del test (p_preventivo_id: in bozza, altrimenti solleva). Restituisce testata, la riga scritta, articolo, BA, emittente, utente di contesto e stato. ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE. Gemello di dbops.fn_pgtap_crea_ordine_con_righe. Brief: brief-modello-documento-vendita §8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
