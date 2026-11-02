-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP — il sezionale e la data che il documento prendera', in lista
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Piano: brief-db-registro-e-data-prevista-in-competenza §11.7 (DB-6)
--
-- Indice dei test:
--   1  fn_lookup_registro_id NON solleva con il tipo documento a NULL
--   2  fn_get_registro_id (involucro) solleva ancora, con SQLSTATE P0001
--   3  lookup e involucro danno lo STESSO registro su tutta la matrice
--   4  ⭐ i DUE ANCORAGGI, su un caso COSTRUITO: padre e figlio con utility
--      diversa -> BA di fatturazione dal PADRE, utility dalla RIGA
--   5  fn_resolve_registro_documento con billing account inesistente:
--      tutto NULL, nessun ripiego sul «registro di nessuno»
--   6  la vista attivita' SOPRAVVIVE a una riga senza tipo documento
--      (era il 500 sull'intera lista)
--   7  la vista non RE-IMPLEMENTA la data: coincide con fn_calcola_data_documento
--   8  D-9: dove la riga di fattura esiste, le colonne previsionali sono VUOTE
--   9  ⭐ D-2 su un caso COSTRUITO: gruppo con due sezionali -> codice e data VUOTI
--  10  ⭐ D-5 sullo stesso caso: il gruppo compare sotto ENTRAMBI i sezionali
--  11  registri_n e' sempre cardinality(registri_ids)
--  (security_invoker: presidiato da rls/test-rls-viste-security-invoker.sql,
--   non piu' qui — vedi la nota in coda al file)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Il taglio lettore / involucro (L0, L1)
-- ============================================================

-- 1. ⛔ E' il difetto che ha fatto nascere DB-0: il CHECK ammette il tipo
--    documento a NULL su una riga non approvata, e una vista che chiamasse
--    l'involucro non mostrerebbe una colonna vuota — farebbe morire la lista.
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_lookup_registro_id(NULL, NULL, NULL, NULL)),
  1,
  'lookup: con il tipo documento a NULL torna UNA riga e non solleva'
);

-- 2. L'involucro invece deve continuare a fermare chi SCRIVE.
--    ⚠️ Con lo SQLSTATE: senza, throws_ok accetterebbe anche il crash del guard.
SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_get_registro_id(NULL) $$,
  'P0001',
  NULL,
  'involucro: con il tipo documento a NULL solleva ancora un errore di dominio'
);

-- 3. Equivalenza su TUTTA la matrice di configurazione (tipo x natura x
--    emittente): l'estrazione non ha cambiato nessuna risposta.
SELECT is(
  (SELECT count(*)::int
     FROM (SELECT DISTINCT m.tipo_doc_fiscale_id, m.natura_doc_id, r.emittente_soggetto_ruolo_id
             FROM vendite.tipi_doc_fiscale_registri m
             JOIN vendite.registri_fatturazione r ON r.id = m.registro_id) c
     CROSS JOIN LATERAL vendite.fn_get_registro_id(
              p_tipo_doc_fiscale_id         => c.tipo_doc_fiscale_id,
              p_natura_doc_id               => c.natura_doc_id,
              p_utility_id                  => NULL,
              p_emittente_soggetto_ruolo_id => c.emittente_soggetto_ruolo_id) v
     CROSS JOIN LATERAL vendite.fn_lookup_registro_id(
              p_tipo_doc_fiscale_id         => c.tipo_doc_fiscale_id,
              p_natura_doc_id               => c.natura_doc_id,
              p_utility_id                  => NULL,
              p_emittente_soggetto_ruolo_id => c.emittente_soggetto_ruolo_id) n
    WHERE v.registro_id IS DISTINCT FROM n.registro_id
       OR v.serie       IS DISTINCT FROM n.serie),
  0,
  'lookup e involucro rispondono identici su tutta la matrice di configurazione'
);

-- ============================================================
-- ⭐ I DUE ANCORAGGI (L2) — il caso si COSTRUISCE, non si cerca
-- ============================================================
-- ⚠️ E' il cuore della prova, e va costruito: i due ancoraggi si distinguono
--    SOLO dove parent_account_id e' valorizzato, e quella colonna e' nullable —
--    un confronto sulla popolazione esistente esercita i rami che quella
--    popolazione per caso contiene, e su un ramo opzionale non garantisce nulla.
-- ⚠️ Si fa variare la UTILITY e non l'emittente: fn_guard_albero_ba_emittente
--    impone che padre e figlio abbiano lo stesso emittente, quindi un figlio con
--    emittente diverso verrebbe RIFIUTATO e il test non partirebbe nemmeno.

CREATE TEMP TABLE tmp_albero AS
WITH padre AS (
    SELECT ba.id, ba.utility_id, ba.istanza_utility_id, ba.soggetto_ruolo_id,
           ba.categoria_cliente_id, ba.fatturazione_ordini, ba.canale_origine
      FROM anagrafiche.billing_account ba
     WHERE ba.parent_account_id IS NULL
     ORDER BY ba.id
     LIMIT 1
), utility_diversa AS (
    SELECT u.id FROM config.utilities u, padre p
     WHERE u.id IS DISTINCT FROM p.utility_id
     ORDER BY u.id LIMIT 1
)
SELECT p.id AS padre_id, p.utility_id AS utility_padre,
       (SELECT id FROM utility_diversa) AS utility_figlio
  FROM padre p;

INSERT INTO anagrafiche.billing_account
       (istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id,
        codice, categoria_cliente_id, fatturazione_ordini, canale_origine)
SELECT ba.istanza_utility_id, ba.soggetto_ruolo_id, t.utility_figlio, t.padre_id,
       'ZZ-PGTAP-FIGLIO', ba.categoria_cliente_id, ba.fatturazione_ordini, ba.canale_origine
  FROM tmp_albero t
  JOIN anagrafiche.billing_account ba ON ba.id = t.padre_id
 WHERE t.utility_figlio IS NOT NULL;

-- 4. ⭐ LA PROVA: il BA di fatturazione viene dal PADRE, la utility dalla RIGA.
--    ⚠️ Scambiarli non darebbe nessun errore, solo un sezionale sbagliato.
SELECT CASE
  WHEN (SELECT utility_figlio FROM tmp_albero) IS NULL
    THEN skip('una sola utility a catalogo: il caso dei due ancoraggi non e'' costruibile', 1)
  ELSE is(
        (SELECT ARRAY[r.ba_fatturazione_id, r.utility_id::bigint]
           FROM anagrafiche.billing_account f
           CROSS JOIN LATERAL vendite.fn_resolve_registro_documento(
                    f.id,
                    (SELECT min(tipo_doc_fiscale_id) FROM vendite.tipi_doc_fiscale_registri),
                    NULL) r
          WHERE f.codice = 'ZZ-PGTAP-FIGLIO'),
        (SELECT ARRAY[t.padre_id, t.utility_figlio::bigint] FROM tmp_albero t),
        'i due ancoraggi: BA di fatturazione dal PADRE, utility dalla RIGA'
      )
END;

-- 5. Billing account non raggiungibile: tutto NULL. ⛔ Non si ripiega sul
--    livello meno specifico della gerarchia — un sezionale generico sarebbe
--    plausibile e sbagliato, e nessuno se ne accorgerebbe.
--    ℹ️ «Non trovato» e «non visibile sotto RLS» percorrono lo STESSO ramo
--    (`IF FOUND`), quindi questa asserzione copre il meccanismo di entrambi.
SELECT ok(
  (SELECT bool_and(ba_fatturazione_id IS NULL AND utility_id IS NULL
                   AND emittente_soggetto_ruolo_id IS NULL AND registro_id IS NULL)
     FROM vendite.fn_resolve_registro_documento(999999999::bigint, NULL, NULL)),
  'billing account irraggiungibile: tutto NULL, nessun ripiego sul registro generico'
);

-- ============================================================
-- La vista attivita' (L4)
-- ============================================================

-- 6. ⛔ Il difetto che DB-0 esiste per evitare, verificato dove morde: una riga
--    senza tipo documento non deve spegnere la lista da cui si fattura.
CREATE TEMP TABLE tmp_senza_tipo AS
SELECT ca.id
  FROM vendite.commesse_attivita ca
 WHERE ca.stato_emissione <> 'EMESSA'
 ORDER BY ca.id
 LIMIT 1;

UPDATE vendite.commesse_attivita
   SET stato_approvazione = 'BOZZA', tipo_doc_fiscale_id = NULL
 WHERE id IN (SELECT id FROM tmp_senza_tipo);

SELECT lives_ok(
  $$ SELECT count(*) FROM vendite.vw_dash_competenza_attivita $$,
  'la vista attivita'' si legge anche con una riga senza tipo documento'
);

-- 7. La vista non RE-IMPLEMENTA il calcolo della data: lo delega.
--    ⚠️ E' l'asserzione che impedisce a qualcuno di «semplificare» la colonna
--    con un date_trunc scritto a mano, che il giorno del primo clamp mentirebbe.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_attivita a
    WHERE a.registro_id IS NOT NULL
      AND a.data_documento_prevista IS DISTINCT FROM
          vendite.fn_calcola_data_documento(
              p_registro_id     => a.registro_id,
              p_competenza_mese => a.competenza_mese,
              p_serie           => (SELECT r.serie
                                      FROM vendite.fn_resolve_registro_documento(
                                               a.billing_account_id,
                                               (SELECT ca.tipo_doc_fiscale_id
                                                  FROM vendite.commesse_attivita ca
                                                 WHERE ca.id = a.commessa_attivita_id),
                                               (SELECT ca.natura_doc_id
                                                  FROM vendite.commesse_attivita ca
                                                 WHERE ca.id = a.commessa_attivita_id)) r),
              p_data_dichiarata => NULL)),
  0,
  'la data prevista e'' quella di fn_calcola_data_documento, non una riscrittura'
);

-- 8. ✅ D-9: dove il documento ESISTE GIA', nessuna previsione.
--    ⚠️ Il discriminante e' la riga di fattura, non lo stadio.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_attivita
    WHERE fattura_riga_id IS NOT NULL
      AND (registro_id IS NOT NULL OR data_documento_prevista IS NOT NULL)),
  0,
  'D-9: con la riga di fattura gia'' esistente le colonne previsionali sono vuote'
);

-- ============================================================
-- ⭐ La vista gruppi (L5) — «uno oppure N», anche qui COSTRUITO
-- ============================================================
-- ⚠️ Non si cerca un gruppo multi-sezionale nella popolazione: si sceglie un
--    gruppo dove il caso sia COSTRUIBILE e lo si costruisce. ⚠️ E non basta
--    cambiare il tipo documento a caso: con natura NOTA_CREDITO tutti i tipi
--    convergono sullo stesso sezionale, quindi il candidato si cerca a natura
--    INVARIATA e verificando che porti davvero a un registro diverso.

CREATE TEMP TABLE tmp_multi(gruppo_key text, competenza_mese date, stadio text,
                            reg_uno bigint, reg_due bigint);

DO $costruisci$
DECLARE
    c record; v_ca bigint; v_ba bigint; v_natura bigint;
    v_reg_o bigint; v_reg_n bigint; v_tipo_n bigint;
BEGIN
    FOR c IN
        SELECT g.gruppo_key, g.competenza_mese, g.stadio
          FROM vendite.vw_dash_competenza_gruppi g
         WHERE g.n_attivita >= 2 AND g.registri_n = 1 AND g.stadio = 'DA_EMETTERE'
         ORDER BY g.gruppo_key, g.competenza_mese
    LOOP
        SELECT a.commessa_attivita_id, a.registro_id, a.billing_account_id
          INTO v_ca, v_reg_o, v_ba
          FROM vendite.vw_dash_competenza_attivita a
         WHERE a.gruppo_key = c.gruppo_key AND a.competenza_mese = c.competenza_mese
           AND a.stadio = c.stadio
         ORDER BY a.commessa_attivita_id LIMIT 1;

        SELECT ca.natura_doc_id INTO v_natura
          FROM vendite.commesse_attivita ca WHERE ca.id = v_ca;

        SELECT m.tipo_doc_fiscale_id, k.registro_id INTO v_tipo_n, v_reg_n
          FROM (SELECT DISTINCT tipo_doc_fiscale_id FROM vendite.tipi_doc_fiscale_registri) m
          CROSS JOIN LATERAL vendite.fn_resolve_registro_documento(v_ba, m.tipo_doc_fiscale_id, v_natura) k
         WHERE k.registro_id IS DISTINCT FROM v_reg_o AND k.registro_id IS NOT NULL
         ORDER BY 1 LIMIT 1;

        IF v_tipo_n IS NOT NULL THEN
            UPDATE vendite.commesse_attivita SET tipo_doc_fiscale_id = v_tipo_n WHERE id = v_ca;
            INSERT INTO tmp_multi VALUES (c.gruppo_key, c.competenza_mese, c.stadio, v_reg_o, v_reg_n);
            EXIT;
        END IF;
    END LOOP;
END
$costruisci$;

-- 9. ✅ D-2: con piu' di un sezionale, codice e data restano VUOTI.
--    ⛔ Mai il primo che capita: sarebbe un valore plausibile che descrive
--    meta' di cio' che sta per succedere.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_multi)
    THEN skip('nessun gruppo dove il caso multi-sezionale sia costruibile', 1)
  ELSE is(
        (SELECT ARRAY[g.registri_n::text,
                      COALESCE(g.registro_codice, '<vuoto>'),
                      COALESCE(g.data_documento_prevista::text, '<vuoto>')]
           FROM vendite.vw_dash_competenza_gruppi g
           JOIN tmp_multi t ON t.gruppo_key = g.gruppo_key
                           AND t.competenza_mese = g.competenza_mese
                           AND t.stadio = g.stadio),
        ARRAY['2', '<vuoto>', '<vuoto>'],
        'D-2: due sezionali nel gruppo -> registri_n = 2, codice e data VUOTI'
      )
END;

-- 10. ✅ D-5: il filtro per sezionale trova il gruppo sotto ENTRAMBI.
--     ⛔ E' il motivo per cui il filtro lavora su registri_ids e non su
--     registro_codice, che li' e' NULL: filtrandoci sopra, il gruppo
--     multi-sezionale sparirebbe da tutti e due i filtri.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_multi)
    THEN skip('nessun gruppo multi-sezionale costruibile', 1)
  ELSE is(
        (SELECT ARRAY[
            (SELECT count(*)::int FROM vendite.vw_dash_competenza_gruppi g, tmp_multi t
              WHERE g.gruppo_key = t.gruppo_key AND g.competenza_mese = t.competenza_mese
                AND t.reg_uno = ANY(g.registri_ids)),
            (SELECT count(*)::int FROM vendite.vw_dash_competenza_gruppi g, tmp_multi t
              WHERE g.gruppo_key = t.gruppo_key AND g.competenza_mese = t.competenza_mese
                AND t.reg_due = ANY(g.registri_ids))]),
        ARRAY[1, 1],
        'D-5: il gruppo multi-sezionale compare sotto ENTRAMBI i filtri'
      )
END;

-- 11. registri_n non e' una seconda verita': e' cardinality(registri_ids).
--     ⚠️ E array_agg TIENE i NULL, a differenza di count(DISTINCT): e' cosi'
--     che «uno risolto + uno ignoto» conta 2 invece di mostrare un sezionale.
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_dash_competenza_gruppi
    WHERE registri_n IS DISTINCT FROM cardinality(registri_ids)),
  0,
  'registri_n coincide sempre con cardinality(registri_ids)'
);

-- 12. ⛔ security_invoker e' una reloption invisibile nel corpo della vista: un
--     CREATE OR REPLACE che non la ripete la AZZERA, senza errore. Qui ci sta
--     lo scope emittente, quindi il presidio e' esplicito.
-- ⛔ QUI `security_invoker` NON SI PRESIDIA PIU' (rev 2026-09-07), e non e' una
--   rinuncia: lo fa gia' db/pgtap/rls/test-rls-viste-security-invoker.sql, su
--   TUTTE le viste che toccano dati in RLS — anche attraverso altre viste — e
--   leggendo la PROPRIETA' invece della parola. Nessun elenco di nomi.
--   ⚠️ Il doppione locale non aggiungeva copertura, e ne ha tolta: era scritto
--   come confronto di GRAFIA (`security_invoker=on`) ed e' diventato ROSSO su
--   una vista perfettamente sana, riscritta con `= true` — che significa la
--   stessa identica cosa. Due falsi allarmi il 2026-09-07, e una bisezione fra
--   due cantieri per scoprire che non era rotto niente.
--   ⭐ Una seconda sede diverge sempre; questa e' divergiata verso il FALSO
--   ALLARME, che e' il verso che fa spegnere i presidi.


SELECT finish();

ROLLBACK;
