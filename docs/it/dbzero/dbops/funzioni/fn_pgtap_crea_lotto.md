{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_lotto.md" %}
# ⚙️ Funzione `fn_pgtap_crea_lotto`

```sql
CREATE FUNCTION fn_pgtap_crea_lotto(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_tipo_doc_fiscale_id bigint, p_competenza_mese date, p_gruppo_key_trattenuto text, p_del_cliente boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_lotto(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT 'DRAFT'::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_competenza_mese date DEFAULT NULL::date, p_gruppo_key_trattenuto text DEFAULT NULL::text, p_del_cliente boolean DEFAULT false)
 RETURNS TABLE(lotto_id bigint, codice character varying, lock_batch_id uuid, emittente_soggetto_ruolo_id bigint, utility_id integer, billing_account_id bigint, tipo_doc_fiscale_id bigint, competenza_mese date, stato_doc_fiscale_id bigint, esito_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un LOTTO di fatturazione
--   dell'azienda di chi agisce in una chiamata, nato dalla madre
--   del dominio e portato allo stato chiesto per la matrice.
-- Uso:
--   CREATE TEMP TABLE tmp_l AS
--   SELECT * FROM dbops.fn_pgtap_crea_lotto('pull');
--   -- il lotto «altrui» che trattiene un gruppo del test:
--   SELECT * FROM dbops.fn_pgtap_crea_lotto(
--              'altrui', 'DRAFT',
--              (SELECT billing_account_id FROM tmp_cliente),
--              p_gruppo_key_trattenuto => (SELECT gruppo_key FROM tmp_g));
-- ⛔ Fatture e ponte NON li scrive: sono il caso del test.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_tipo_id   vendite.fatturazione_lotti.tipo_doc_fiscale_id%TYPE;
    v_mese      vendite.fatturazione_lotti.competenza_mese%TYPE;
    v_lotto     vendite.fatturazione_lotti.id%TYPE;
    v_esito     vendite.fatturazione_lotti_esiti.id%TYPE;
BEGIN
    -- 0. Lo stato si giudica PRIMA di costruire.
    IF NOT EXISTS (SELECT 1 FROM config.stati_doc_fiscale s
                    WHERE s.codice_interno = p_stato_codice_interno
                      AND s.applica_lotto IS TRUE
                      AND s.attivo IS TRUE) THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_lotto: nessuno stato fiscale attivo applicabile a un lotto con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;

    -- 1. Il mondo. Senza p_billing_account_id costruisce anche il
    --    cliente; con, riusa quello e prende solo l'azienda di chi
    --    agisce, senza costruire un cliente in piu'
    --    (dbops.fn_pgtap_cliente_del_builder, rev 20261024-40).
    SELECT c.emittente_soggetto_ruolo_id, c.billing_account_id, c.utility_id
      INTO v_ef_sr_id, v_ba_id, v_utility
      FROM dbops.fn_pgtap_cliente_del_builder(
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_lotto') c;

    -- 2. Il catalogo si SCEGLIE, con il suo ORDER BY: un tipo
    --    documento che ha un registro (la madre lo pretende).
    v_tipo_id := p_tipo_doc_fiscale_id;
    IF v_tipo_id IS NULL THEN
        SELECT t.id INTO v_tipo_id
          FROM config.tipi_doc_fiscale t
         WHERE t.attivo IS TRUE
           AND EXISTS (SELECT 1 FROM vendite.tipi_doc_fiscale_registri m
                        WHERE m.tipo_doc_fiscale_id = t.id)
         ORDER BY t.id
         LIMIT 1;
    END IF;

    v_mese := COALESCE(p_competenza_mese,
                       date_trunc('month', (SELECT script.fn_data_operativa()))::date);

    -- 3. La madre: codice, lock_batch_id e stato DRAFT li decide lei.
    v_lotto := vendite.fn_create_fatturazione_lotto(
        p_competenza_mese             => v_mese,
        p_tipo_doc_fiscale_id         => v_tipo_id,
        p_utility_id                  => v_utility,
        p_billing_account_id          => CASE WHEN p_del_cliente THEN v_ba_id END,
        p_lock_batch_id               => NULL,
        p_meta                        => jsonb_build_object('test_scope', 'pgtap_' || p_etichetta),
        p_emittente_soggetto_ruolo_id => v_ef_sr_id);

    -- 4. Lo stato, per la matrice, sul lotto ancora vuoto.
    IF p_stato_codice_interno IS DISTINCT FROM 'DRAFT'
       AND (SELECT s.codice_interno FROM vendite.fatturazione_lotti l
              JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id
             WHERE l.id = v_lotto) IS DISTINCT FROM p_stato_codice_interno THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.fatturazione_lotti'::regclass,
                                             v_lotto, p_stato_codice_interno);
    END IF;

    -- 5. L'esito che trattiene un gruppo, la forma dei pgTAP del pull.
    IF p_gruppo_key_trattenuto IS NOT NULL THEN
        INSERT INTO vendite.fatturazione_lotti_esiti
            (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
        VALUES (v_lotto, p_gruppo_key_trattenuto, 'ERRORE', 'E_PULL_COMMESSA',
                'pgTAP: gruppo trattenuto dal lotto ' || p_etichetta)
        RETURNING id INTO v_esito;
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT l.id, l.codice, l.lock_batch_id, l.emittente_soggetto_ruolo_id,
           l.utility_id, v_ba_id, l.tipo_doc_fiscale_id, l.competenza_mese,
           l.stato_doc_fiscale_id, v_esito
      FROM vendite.fatturazione_lotti l
     WHERE l.id = v_lotto;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_lotto(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_tipo_doc_fiscale_id bigint, p_competenza_mese date, p_gruppo_key_trattenuto text, p_del_cliente boolean)
IS 'Fixture pgTAP: un LOTTO di fatturazione dell''azienda di chi agisce in una chiamata. ⭐ Nasce dalla MADRE vendite.fn_create_fatturazione_lotto (codice, lock_batch_id, stato DRAFT), con emittente e utility del cliente: quello del terzo parametro (verificato da dbops.fn_pgtap_cliente_ba_del_mondo) o uno nuovo del mondo. Il lotto e'' dell''azienda (billing_account_id NULL); p_del_cliente => true lo lega al cliente. Secondo parametro: lo stato, raggiunto per la matrice con dbops.fn_pgtap_porta_a_stato sul lotto ancora vuoto. Tipo documento: quello chiesto o il primo attivo con un registro (vendite.tipi_doc_fiscale_registri). Competenza: quella chiesta o il mese della data operativa. p_gruppo_key_trattenuto: scrive l''esito ERRORE (E_PULL_COMMESSA) che trattiene quel gruppo nel lotto. ⛔ NON scrive fatture ne'' ponte: sono il caso del test, e un lotto con fatture si muove col verbo vendite.fn_sync_lotto_fatture_stato. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper. Brief: brief-modello-documento-vendita (R-4), 2026-10-24. Rev 2026-10-24 (20261024-40, §4-octies): col billing account del test non costruisce piu'' un cliente in piu'' (dbops.fn_pgtap_cliente_del_builder).';
```

</div>

---
{% include-markdown "signature-core.md" %}
