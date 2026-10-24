{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_commessa.md" %}
# ⚙️ Funzione `fn_pgtap_crea_commessa`

```sql
CREATE FUNCTION fn_pgtap_crea_commessa(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_con_attivita boolean, p_con_sorgente_root boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_commessa(p_etichetta text DEFAULT 'pgTAP'::text, p_stato_codice_interno character varying DEFAULT NULL::character varying, p_billing_account_id bigint DEFAULT NULL::bigint, p_con_attivita boolean DEFAULT NULL::boolean, p_con_sorgente_root boolean DEFAULT false)
 RETURNS TABLE(commessa_id bigint, commessa_codice character varying, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer, attivita_id bigint, stato_commessa_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una COMMESSA del mondo in una
--   chiamata: azienda, operatore, cliente e commessa aperta
--   dalla madre del dominio, nello stato chiesto.
-- Uso:
--   CREATE TEMP TABLE tmp_c AS
--   SELECT * FROM dbops.fn_pgtap_crea_commessa('rls commesse');
--   -- una commessa emittibile del cliente di un'altra fixture:
--   SELECT * FROM dbops.fn_pgtap_crea_commessa(
--              'pull', 'PRONTA_FATTURAZIONE',
--              (SELECT billing_account_id FROM tmp_cliente));
-- ⛔ Le attivita' le scrive solo per uscire dalla bozza (o se
--   p_con_attivita lo chiede): UNA, da
--   dbops.fn_pgtap_crea_commessa_attivita. Le altre sono il
--   caso del test. La sorgente ROOT la scrive se
--   p_con_sorgente_root lo chiede (il pull la pretende).
-- ⚠️ Senza contesto aperto, il mondo lo apre sull'operatore che
--   costruisce. Esce con i vincoli IMMEDIATE, come ogni helper.
-- rev 2026-10-24 (20261024-26, brief-modello-documento-vendita
--   Q-2): stato, billing account del test e attivita'.
-- rev 2026-10-24 (20261024-32, R-3): la sorgente ROOT.
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_commessa  vendite.commesse.id%TYPE;
    v_codice    vendite.commesse.codice%TYPE;
    v_iniziale  vendite.stati_commessa.id%TYPE;
    v_target    vendite.stati_commessa.id%TYPE;
    v_attivita  vendite.commesse_attivita.id%TYPE;
    v_stato_id  vendite.commesse.stato_commessa_id%TYPE;
BEGIN
    -- 0. Lo stato si giudica PRIMA di costruire: un codice che
    --    non c'e' parla qui, nominando il builder.
    v_iniziale := script.fn_stato_iniziale_id('vendite.stati_commessa'::regclass);
    IF p_stato_codice_interno IS NOT NULL THEN
        SELECT s.id INTO v_target
          FROM vendite.stati_commessa s
         WHERE s.codice_interno = p_stato_codice_interno
           AND s.attivo IS TRUE;
        IF v_target IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_commessa: nessuno stato di commessa attivo con codice_interno = %',
                p_stato_codice_interno;
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
               p_etichetta, p_billing_account_id, 'fn_pgtap_crea_commessa') c;

    -- 2. La madre: codice, emittente e stato iniziale li decide lei.
    v_commessa := vendite.fn_get_or_create_commessa(
        p_billing_account_id => v_ba_id,
        p_utility_id         => v_utility,
        p_competenza_dal     => date_trunc('month', (SELECT script.fn_data_operativa()))::date,
        p_competenza_al      => (date_trunc('month', (SELECT script.fn_data_operativa()))
                                 + interval '1 month - 1 day')::date,
        p_meta               => jsonb_build_object('test_scope', 'pgtap_' || p_etichetta),
        p_force_new          => true);

    SELECT c.codice INTO v_codice
      FROM vendite.commesse c
     WHERE c.id = v_commessa;

    -- 2-bis. La sorgente ROOT: la commessa e' la radice di se'
    --    stessa. Sorgente COMMESSA, chiave = l'id (key_selector
    --    `id` della sorgente): la riga esiste per costruzione.
    IF p_con_sorgente_root THEN
        INSERT INTO vendite.commesse_sorgenti
            (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
        VALUES (v_commessa,
                (SELECT s.id FROM config.sorgenti s
                  WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE),
                v_commessa::text, 'ROOT');
    END IF;

    -- 3. Il lavoro, PRIMA del passaggio: l'uscita dalla bozza lo
    --    pretende, e in bozza le righe si scrivono.
    IF COALESCE(p_con_attivita,
                v_target IS NOT NULL AND v_target IS DISTINCT FROM v_iniziale) THEN
        SELECT a.attivita_id INTO v_attivita
          FROM dbops.fn_pgtap_crea_commessa_attivita(v_commessa) a;
    END IF;

    -- 4. Lo stato, per la matrice, sotto i guard veri.
    IF v_target IS NOT NULL AND v_target IS DISTINCT FROM v_iniziale THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse'::regclass, v_commessa,
                                             p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    SELECT c.stato_commessa_id INTO v_stato_id
      FROM vendite.commesse c
     WHERE c.id = v_commessa;

    RETURN QUERY
    SELECT v_commessa, v_codice, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id, v_utility,
           v_attivita, v_stato_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_commessa(p_etichetta text, p_stato_codice_interno character varying, p_billing_account_id bigint, p_con_attivita boolean, p_con_sorgente_root boolean)
IS 'Fixture pgTAP: una COMMESSA del mondo in una chiamata: azienda, operatore e cliente (dbops.fn_pgtap_crea_mondo_cliente) e la commessa aperta dalla madre vendite.fn_get_or_create_commessa (p_force_new), con competenza nel mese corrente. Codice, emittente e stato iniziale li decide la madre, come in produzione. ⭐ Secondo parametro: lo stato da raggiungere (NULL o l''iniziale: resta li''), per la matrice con dbops.fn_pgtap_porta_a_stato, sotto i guard veri. ⚠️ Terzo parametro: il billing account di un cliente gia'' costruito, verificato da dbops.fn_pgtap_cliente_ba_del_mondo (un BA di un''altra azienda solleva). Quarto parametro: scrive UN''attivita'' APPROVATA e NON_EMESSA (dbops.fn_pgtap_crea_commessa_attivita) prima del passaggio; NULL = solo se lo stato chiesto non e'' l''iniziale, perche'' l''uscita dalla bozza la pretende. Quinto parametro: scrive la sorgente ROOT (sorgente COMMESSA, chiave l''id della commessa), quella che il pull della fatturazione pretende. ⛔ Le altre attivita'' e le altre sorgenti sono il caso del test. Ritorna le chiavi, l''attivita'' scritta (o NULL) e lo stato raggiunto. ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE. Brief: brief-db-fixture-rls-documenti-costruiti. Rev 2026-10-24 (20261024-26, brief-modello-documento-vendita Q-2): stato, billing account e attivita'', DROP + CREATE; 20261024-32 (R-3): la sorgente ROOT. Rev 2026-10-24 (20261024-40, §4-octies): col billing account del test non costruisce piu'' un cliente in piu'' (dbops.fn_pgtap_cliente_del_builder).';
```

</div>

---
{% include-markdown "signature-core.md" %}
