-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_emittibili_lane (changeset 20260619-01, 20260619-11)
--   Discovery corsie (emittente, tipo_doc_fiscale, utility, competenza_mese) per il driver batch.
--
-- NB: l'emittente di test deriva da un billing_account ESISTENTE, che puo' avere gia'
-- commesse/attivita' candidate. Quindi i conteggi sono verificati per DELTA (baseline
-- pre-fixture vs dopo), non in assoluto. competenza_mese e l'esclusione NULL sono invece
-- robusti per costruzione (il filtro <= cappa al mese richiesto).
--
-- Prerequisiti ambiente: un billing_account con emittente fiscale, un articolo e una UoM
-- attivi, e >= 2 tipi_doc_fiscale attivi (X, Y distinti).
--
-- NB grana per-utility (changeset 20260619-11): la fn raggruppa anche per c.utility_id.
-- Le commesse A/B condividono lo stesso billing_account -> stessa utility U1, quindi i
-- DELTA su (E,X) restano per-terna (E,X,U1). Gli helper sono utility-aware (filtrano U1)
-- per non incappare nello scalar-subquery >1 row in DB con piu' utility per emittente.
--
-- Indice test (1..13):
--   1) terna (E,X,U1) presente con competenza_mese = max cappato (2026-07-01)
--   2) DELTA (E,X,U1) = 3 -> include l'ARRETRATO di giugno (filtro <= cumulativo)
--   3) DELTA (E,Y,U1) = 1 -> riga BOZZA (non approvata) ESCLUSA
--   4) nessuna terna con tipo_doc_fiscale_id NULL (riga BOZZA+NULL esclusa; APPROVATA+NULL vietata dal guard)
--   5) DELTA corsia immediata=true  (E,X,U1) = 2 (solo commessa immediata)
--   6) DELTA corsia immediata=false (E,X,U1) = 1 (solo commessa differita)
--   7) fn_list_commesse_emittibili NON toccata (continua a restituire la commessa A)
--   8) multi-utility: stesso (E,X) su U2 -> terna (E,X,U2) distinta (skip se manca 2o BA)
--   9) utility_id in output mai NULL (commesse.utility_id NOT NULL a monte)
--  10-11) gruppi_coperti: elenco per terna, e il non servito per differenza
--  12) tetto p_limit sul giro di MASSA: tronca in silenzio (storico)
--  13) tetto p_limit sul giro MIRATO: SOLLEVA (perimetro nominale)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- SETUP: riferimenti minimi + due tipi_doc distinti (X, Y)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  ba.id                          AS billing_account_id,
  ba.utility_id                  AS utility_id,
  ba.istanza_utility_id          AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
     ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)            AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
     ORDER BY u.id LIMIT 1)                                     AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
     ORDER BY t.id LIMIT 1)                                     AS doc_x,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
     ORDER BY t.id OFFSET 1 LIMIT 1)                            AS doc_y
FROM anagrafiche.billing_account ba
WHERE ba.utility_id IS NOT NULL
  AND ba.istanza_utility_id IS NOT NULL
  AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
ORDER BY ba.id
LIMIT 1;

-- Secondo BA con LO STESSO emittente fiscale ma utility DIVERSA (per il test multi-utility).
-- Puo' non esistere: in quel caso il test 8 viene skippato (skip condizionale).
CREATE TEMP TABLE tmp_refs2 AS
SELECT
  ba.id                  AS billing_account_id,
  ba.utility_id          AS utility_id,
  ba.istanza_utility_id  AS istanza_utility_id
FROM anagrafiche.billing_account ba
WHERE ba.utility_id IS NOT NULL
  AND ba.istanza_utility_id IS NOT NULL
  AND ba.utility_id <> (SELECT utility_id FROM tmp_refs)
  AND anagrafiche.fn_get_emittente_fiscale_id(ba.id)
      = (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_refs)
ORDER BY ba.id
LIMIT 1;

-- Helper: crea una riga commesse_attivita variando commessa/tipo_doc/competenza/stato.
CREATE FUNCTION pg_temp.mk_att(
  p_commessa bigint, p_tipo_doc bigint, p_comp date, p_appr varchar, p_tag text
) RETURNS bigint LANGUAGE sql AS $$
  SELECT r.attivita_id
  FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => p_commessa,
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => (p_commessa)::text,
    p_segment_key                   => ('SEG-LANE-' || p_tag || '-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
    p_articolo_id                   => (SELECT articolo_id FROM tmp_refs),
    p_istanza_utility_id            => (SELECT istanza_utility_id FROM tmp_refs),
    p_data_attivita                 => p_comp,
    p_uom_id                        => (SELECT uom_id FROM tmp_refs),
    p_quantita                      => 1.000000,
    p_competenza_mese               => p_comp,
    p_competenza_dal                => date_trunc('month', p_comp)::date,
    p_competenza_al                 => (date_trunc('month', p_comp) + INTERVAL '1 month - 1 day')::date,
    p_prezzo_snapshot               => 10.0000000000,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_tipo_doc_fiscale_id           => p_tipo_doc,
    p_stato_approvazione            => p_appr,
    p_stato_emissione               => 'NON_EMESSA',
    p_tipo_movimento                => 'NORMALE',
    p_meta                          => jsonb_build_object('lane_tag', p_tag)
  ) r;
$$;

-- Gemello di mk_att per la commessa su tmp_refs2 (istanza_utility della seconda utility).
CREATE FUNCTION pg_temp.mk_att2(
  p_commessa bigint, p_tipo_doc bigint, p_comp date, p_appr varchar, p_tag text
) RETURNS bigint LANGUAGE sql AS $$
  SELECT r.attivita_id
  FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => p_commessa,
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => (p_commessa)::text,
    p_segment_key                   => ('SEG-LANE-' || p_tag || '-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
    p_articolo_id                   => (SELECT articolo_id FROM tmp_refs),
    p_istanza_utility_id            => (SELECT istanza_utility_id FROM tmp_refs2),
    p_data_attivita                 => p_comp,
    p_uom_id                        => (SELECT uom_id FROM tmp_refs),
    p_quantita                      => 1.000000,
    p_competenza_mese               => p_comp,
    p_competenza_dal                => date_trunc('month', p_comp)::date,
    p_competenza_al                 => (date_trunc('month', p_comp) + INTERVAL '1 month - 1 day')::date,
    p_prezzo_snapshot               => 10.0000000000,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_tipo_doc_fiscale_id           => p_tipo_doc,
    p_stato_approvazione            => p_appr,
    p_stato_emissione               => 'NON_EMESSA',
    p_tipo_movimento                => 'NORMALE',
    p_meta                          => jsonb_build_object('lane_tag', p_tag)
  ) r;
$$;

-- ============================================================
-- SETUP: commessa A (immediata) giugno-luglio; commessa B (differita) luglio.
-- (create PRIMA delle righe e della transizione -> non ancora emittibili)
-- ============================================================
CREATE TEMP TABLE tmp_a AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => true,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_lane_A'),
  p_force_new => true
) AS commessa_id;

CREATE TEMP TABLE tmp_b AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_lane_B'),
  p_force_new => true
) AS commessa_id;

-- Commessa C (immediata) sul SECONDO billing account -> stessa E, utility U2.
-- Vuota (0 righe) se tmp_refs2 non ha trovato un secondo BA fratello.
CREATE TEMP TABLE tmp_c AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => r2.billing_account_id,
  p_utility_id => r2.utility_id,
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => true,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_lane_C'),
  p_force_new => true
) AS commessa_id
FROM tmp_refs2 r2;

-- emittente E (condiviso: stesso billing account)
CREATE TEMP TABLE tmp_e AS
SELECT emittente_soggetto_ruolo_id AS e
FROM vendite.commesse WHERE id = (SELECT commessa_id FROM tmp_a);

-- Helper: total_candidate per la terna (E, tipo_doc, U1) sotto corsia p_imm (luglio).
-- Utility-aware: filtra l'utility primaria U1 (tmp_refs) -> con la grana a 3 assi la
-- scalar subquery resta a 1 riga anche se l'emittente ha piu' utility per lo stesso tipo_doc.
CREATE FUNCTION pg_temp.lane_total(p_tipo_doc bigint, p_imm boolean)
RETURNS bigint LANGUAGE sql AS $$
  SELECT COALESCE((
    SELECT l.total_candidate
    FROM vendite.fn_list_emittibili_lane(
           p_competenza_mese => DATE '2026-07-01',
           p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e),
           p_fatturazione_immediata => p_imm) l
    WHERE l.tipo_doc_fiscale_id = p_tipo_doc
      AND l.utility_id = (SELECT utility_id FROM tmp_refs)
  ), 0::bigint);
$$;

-- BASELINE pre-fixture (A/B senza righe e non emittibili -> conteggio dati pre-esistenti)
CREATE TEMP TABLE tmp_base AS
SELECT
  pg_temp.lane_total((SELECT doc_x FROM tmp_refs), NULL::boolean)  AS x_null,
  pg_temp.lane_total((SELECT doc_y FROM tmp_refs), NULL::boolean)  AS y_null,
  pg_temp.lane_total((SELECT doc_x FROM tmp_refs), true)           AS x_imm,
  pg_temp.lane_total((SELECT doc_x FROM tmp_refs), false)          AS x_dif;

-- Righe commessa A: X-lug, X-giu(arretrato), Y-lug, Y-lug BOZZA(escl), NULL-lug BOZZA(escl)
-- NB: la riga tipo_doc NULL DEVE essere BOZZA: il guard
-- trg_commesse_attivita_a10_guard_tipo_doc_emittibile (brief-db-guard-tipo-doc-attivita)
-- vieta APPROVATA + tipo_doc NULL. In BOZZA il NULL e' lecito ed e' comunque escluso
-- dalla lane (sia per approvazione sia per tipo_doc NOT NULL).
SELECT pg_temp.mk_att((SELECT commessa_id FROM tmp_a), (SELECT doc_x FROM tmp_refs), DATE '2026-07-01', 'APPROVATA', 'aXjul');
SELECT pg_temp.mk_att((SELECT commessa_id FROM tmp_a), (SELECT doc_x FROM tmp_refs), DATE '2026-06-01', 'APPROVATA', 'aXjun');
SELECT pg_temp.mk_att((SELECT commessa_id FROM tmp_a), (SELECT doc_y FROM tmp_refs), DATE '2026-07-01', 'APPROVATA', 'aYjul');
SELECT pg_temp.mk_att((SELECT commessa_id FROM tmp_a), (SELECT doc_y FROM tmp_refs), DATE '2026-07-01', 'BOZZA',     'aYbozza');
SELECT pg_temp.mk_att((SELECT commessa_id FROM tmp_a), NULL,                          DATE '2026-07-01', 'BOZZA',     'aNull');

-- Riga commessa B: X-lug
SELECT pg_temp.mk_att((SELECT commessa_id FROM tmp_b), (SELECT doc_x FROM tmp_refs), DATE '2026-07-01', 'APPROVATA', 'bXjul');

-- Riga commessa C (utility U2): X-lug. Solo se C esiste (secondo BA fratello trovato).
SELECT pg_temp.mk_att2(c.commessa_id, (SELECT doc_x FROM tmp_refs), DATE '2026-07-01', 'APPROVATA', 'cXjul')
FROM tmp_c c;

-- Porta in stato emittibile A, B e (se esiste) C
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_a), 'PRONTA_FATTURAZIONE');
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_b), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_cambia_stato_commessa(c.commessa_id, 'PRONTA_FATTURAZIONE') FROM tmp_c c;

-- ============================================================
-- TEST 1: coppia (E,X) presente con competenza_mese = 2026-07-01 (max cappato dal filtro <=)
-- ============================================================
SELECT is(
  (SELECT l.competenza_mese
   FROM vendite.fn_list_emittibili_lane(
          p_competenza_mese => DATE '2026-07-01',
          p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e)) l
   WHERE l.tipo_doc_fiscale_id = (SELECT doc_x FROM tmp_refs)
     AND l.utility_id = (SELECT utility_id FROM tmp_refs)),
  DATE '2026-07-01',
  '(E,X,U1) presente con competenza_mese = 2026-07-01 (max cappato)'
);

-- TEST 2: DELTA (E,X) = 3 -> arretrato giugno incluso (filtro <= cumulativo)
SELECT is(
  pg_temp.lane_total((SELECT doc_x FROM tmp_refs), NULL::boolean) - (SELECT x_null FROM tmp_base),
  3::bigint,
  'DELTA (E,X) = 3 (X-lug A + X-giu arretrato A + X-lug B)'
);

-- TEST 3: DELTA (E,Y) = 1 -> riga BOZZA esclusa
SELECT is(
  pg_temp.lane_total((SELECT doc_y FROM tmp_refs), NULL::boolean) - (SELECT y_null FROM tmp_base),
  1::bigint,
  'DELTA (E,Y) = 1 (riga BOZZA esclusa)'
);

-- TEST 4: nessuna terna con tipo_doc_fiscale_id NULL (riga BOZZA+NULL esclusa)
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_emittibili_lane(
           p_competenza_mese => DATE '2026-07-01',
           p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e)) l
    WHERE l.tipo_doc_fiscale_id IS NULL
  ),
  'nessuna terna con tipo_doc NULL (riga BOZZA+NULL esclusa)'
);

-- TEST 5: DELTA corsia immediata=true -> (E,X) = 2 (solo commessa A)
SELECT is(
  pg_temp.lane_total((SELECT doc_x FROM tmp_refs), true) - (SELECT x_imm FROM tmp_base),
  2::bigint,
  'DELTA corsia immediata=true (E,X) = 2 (commessa A: X-lug + X-giu)'
);

-- TEST 6: DELTA corsia immediata=false -> (E,X) = 1 (solo commessa B)
SELECT is(
  pg_temp.lane_total((SELECT doc_x FROM tmp_refs), false) - (SELECT x_dif FROM tmp_base),
  1::bigint,
  'DELTA corsia immediata=false (E,X) = 1 (commessa B)'
);

-- TEST 7: fn_list_commesse_emittibili NON toccata (restituisce ancora la commessa A)
SELECT ok(
  EXISTS (
    SELECT 1 FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_a)
  ),
  'fn_list_commesse_emittibili invariata (restituisce la commessa A)'
);

-- TEST 8: multi-utility -> la stessa (E,X) su U2 produce una TERNA distinta (E,X,U2).
-- Skippato se in ambiente non esiste un secondo BA con stesso emittente e utility diversa.
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM tmp_c)
  THEN ok(
    EXISTS (
      SELECT 1
      FROM vendite.fn_list_emittibili_lane(
             p_competenza_mese => DATE '2026-07-01',
             p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e)) l
      WHERE l.tipo_doc_fiscale_id = (SELECT doc_x FROM tmp_refs)
        AND l.utility_id = (SELECT utility_id FROM tmp_refs2)
        AND l.total_candidate >= 1
    ),
    'multi-utility: terna (E,X,U2) distinta presente (grana per-utility)'
  )
  ELSE skip('nessun secondo billing_account con stesso emittente e utility diversa', 1)
END;

-- TEST 9: utility_id in output mai NULL (commesse.utility_id NOT NULL a monte)
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_emittibili_lane(
           p_competenza_mese => DATE '2026-07-01',
           p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e)) l
    WHERE l.utility_id IS NULL
  ),
  'utility_id in output mai NULL'
);

-- ============================================================
-- TEST 10 e 11: `gruppi_coperti` — l'emissione PARZIALE sa dire chi e'
--   rimasto fuori (rev 2026-08-15, brief emittibilita §5, `20260815-02`).
--
--   Il difetto che chiudono: la lane aggrega per terna, e in quel GROUP BY
--   i gruppi richiesti sparivano. Chiesti 3, fatturati 2, e nessuno a valle
--   poteva dire quale fosse il terzo — il caso peggiore, perche' «2 su 3»
--   sembra un successo mentre il lavoro non fatturato resta fermo.
--
--   La fixture usa i gruppi VERI delle due commesse costruite sopra: la
--   chiave si chiede alla sola fonte di verita'
--   (fn_build_gruppo_fatturabile_key), non si scrive a mano — scriverla
--   qui sarebbe una seconda copia della regola, cioe' il difetto stesso.
-- ============================================================
CREATE TEMP TABLE tmp_gruppi AS
SELECT DISTINCT
       vendite.fn_build_gruppo_fatturabile_key(
           ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS k,
       ca.commessa_id
  FROM vendite.commesse_attivita ca
 WHERE ca.commessa_id IN ((SELECT commessa_id FROM tmp_a),
                          (SELECT commessa_id FROM tmp_b))
   AND ca.stato_approvazione = 'APPROVATA'
   AND ca.stato_emissione    = 'NON_EMESSA'
   AND ca.tipo_doc_fiscale_id IS NOT NULL;

-- TEST 10: chiedendo UN gruppo solo, la terna dichiara quel gruppo e
--   nient'altro. E' l'invariante minima: cio' che esce e' cio' che si e'
--   chiesto, non «tutto quello che c'era nella terna».
SELECT CASE WHEN (SELECT count(*) FROM tmp_gruppi) = 0
  THEN skip('nessun gruppo fatturabile nelle commesse della fixture', 1)
  ELSE is(
    (SELECT array_agg(DISTINCT g ORDER BY g)
       FROM vendite.fn_list_emittibili_lane(
              p_competenza_mese => DATE '2026-07-01',
              p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e),
              p_gruppi => ARRAY[(SELECT k FROM tmp_gruppi ORDER BY k LIMIT 1)]) l,
            unnest(l.gruppi_coperti) AS g),
    ARRAY[(SELECT k FROM tmp_gruppi ORDER BY k LIMIT 1)],
    'gruppi_coperti: chiesto un gruppo, la terna dichiara esattamente quello'
  )
END;

-- TEST 11: il caso del brief. Si chiedono TUTTI i gruppi della fixture piu'
--   uno INESISTENTE: i gruppi coperti sono quelli veri, e il fantasma si
--   ricava per differenza — che e' esattamente la risposta che prima non
--   c'era. ⚠️ Il gruppo assente si costruisce inesistente di proposito:
--   usarne uno vero di un'altra commessa legherebbe il test a dati che
--   possono cambiare.
SELECT CASE WHEN (SELECT count(*) FROM tmp_gruppi) = 0
  THEN skip('nessun gruppo fatturabile nelle commesse della fixture', 1)
  ELSE is(
    (SELECT array_agg(k ORDER BY k) FROM (
       SELECT k FROM tmp_gruppi
       UNION ALL SELECT 'PREVENTIVO:00000000-0000-0000-0000-000000000000'
     ) q
     WHERE NOT EXISTS (
       SELECT 1
         FROM vendite.fn_list_emittibili_lane(
                p_competenza_mese => DATE '2026-07-01',
                p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e),
                p_gruppi => (SELECT array_agg(k) FROM (
                               SELECT k FROM tmp_gruppi
                               UNION ALL SELECT 'PREVENTIVO:00000000-0000-0000-0000-000000000000') z)) l
        WHERE q.k = ANY (l.gruppi_coperti))),
    ARRAY['PREVENTIVO:00000000-0000-0000-0000-000000000000'],
    'gruppi_coperti: il gruppo non servito si ricava per differenza (emissione parziale)'
  )
END;

-- ============================================================
-- TEST 12-13: il TETTO (p_limit) e le due risposte opposte.
--   Il tetto limita le CORSIE. Se ne taglia una, i gruppi che stavano
--   dentro spariscono dal risultato, e a valle il conto per differenza li
--   marchia «non fatturabili»: una diagnosi FALSA su un gruppo che era solo
--   oltre il taglio. Il rimedio non e' simmetrico, ed e' il punto:
--     · giro di MASSA -> il tetto e' una valvola, tronca in silenzio
--     · giro MIRATO   -> il perimetro e' nominale, e troncare significa non
--                        aver risposto: solleva.
--   brief-db-emittibilita-visibile-e-sbloccabile §9 F7, changeSet 20260815-32.
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.fn_list_emittibili_lane(
     p_competenza_mese => DATE '2026-07-01',
     p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e),
     p_limit => 1)),
  1,
  '12. Giro di MASSA col tetto a 1: tronca in silenzio, comportamento storico invariato'
);

-- ⚠️ Il caso vale solo se le corsie della fixture sono piu' d'una: con una
--   sola non c'e' niente da troncare e il test misurerebbe il nulla.
SELECT CASE WHEN (
    SELECT count(*) FROM vendite.fn_list_emittibili_lane(
      p_competenza_mese => DATE '2026-07-01',
      p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e),
      p_gruppi => (SELECT array_agg(k) FROM tmp_gruppi))) < 2
  THEN skip('la fixture produce meno di 2 corsie: niente da troncare', 1)
  ELSE throws_ok(
    format($$ SELECT * FROM vendite.fn_list_emittibili_lane(
                p_competenza_mese => DATE '2026-07-01',
                p_emittente_soggetto_ruolo_id => %s,
                p_gruppi => %L::text[],
                p_limit  => 1) $$,
           (SELECT e FROM tmp_e),
           (SELECT array_agg(k) FROM tmp_gruppi)),
    'P0001', NULL,
    '13. Giro MIRATO troncato dal tetto: SOLLEVA, non restituisce una risposta parziale che a valle diventa una diagnosi falsa'
  )
END;

-- ============================================================
-- 14-15) ⭐ IL DOCUMENTO TRATTENUTO DA UN LOTTO VIVO NON SI RI-OFFRE
-- ============================================================
-- ⛔ IL DIFETTO: la lane filtrava solo su `stato_emissione = 'NON_EMESSA'` e
--   `stato_approvazione = 'APPROVATA'`, senza guardare gli esiti dei lotti. Un
--   documento gia' preso da un giro VIVO che non ha ancora finito — tipicamente
--   perche' il suo pull e' FALLITO, quindi niente fattura, quindi NON_EMESSA —
--   veniva riofferto, e un secondo lotto se lo prendeva.
--   ⚠️ La casella spenta a video non lo impedisce: chi costruisce il lotto lo
--   prende da QUI. E' il lato macchina della regola.
--
-- ⭐ I DUE TEST SONO UN VERSO E IL SUO CONTRARIO, e servono entrambi: col solo
--   14 passerebbe anche un filtro che esclude QUALUNQUE documento con un esito,
--   e allora un lotto annullato bloccherebbe per sempre il suo contenuto. Il 15
--   e' quello che se ne accorge — ed e' anche il test che morde se qualcuno
--   leggesse `congela_fiscale` al posto di `is_abortito`.
--
-- ⚠️ Il predicato NON si riscrive qui: si interroga la sede unica
--   (vendite.vw_documenti_trattenuti_da_lotto). Scriverlo nel test sarebbe una
--   seconda copia della regola, cioe' il difetto stesso — la stessa ragione per
--   cui la fixture qui sopra chiede la chiave a fn_build_gruppo_fatturabile_key
--   invece di comporla a mano.
-- Brief: brief-db-documento-trattenuto-da-un-lotto-vivo.md (T-4)

-- Un gruppo vero della fixture. ⚠️ ORDER BY prima del LIMIT: senza, quale
--   gruppo esca dipende dal planner e il test proverebbe una riga diversa a
--   ogni corsa.
CREATE TEMP TABLE tmp_trat_g AS
SELECT k FROM tmp_gruppi ORDER BY k LIMIT 1;

CREATE TEMP TABLE tmp_trat_lotto AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
    stato_doc_fiscale_id)
  SELECT 'PGTAP-LANE-TRAT-' || substr(md5(clock_timestamp()::text), 1, 8),
         DATE '2026-07-01',
         (SELECT l.tipo_doc_fiscale_id FROM vendite.fatturazione_lotti l
           ORDER BY l.id DESC LIMIT 1),
         (SELECT e FROM tmp_e),
         -- ⛔ `codice_interno`, mai un id.
         (SELECT sdf.id FROM config.stati_doc_fiscale sdf
           WHERE sdf.codice_interno = 'DRAFT')
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT (SELECT id FROM tmp_trat_lotto), (SELECT k FROM tmp_trat_g);

-- ⭐ Esito COMPLETED di proposito: il caso in cui l'esito direbbe «libero».
INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
SELECT (SELECT id FROM tmp_trat_lotto), (SELECT k FROM tmp_trat_g), 'COMPLETED';

SELECT ok(
  NOT EXISTS (
    SELECT 1
      FROM vendite.fn_list_emittibili_lane(
             p_competenza_mese => DATE '2026-07-01',
             p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e)) l
     WHERE (SELECT k FROM tmp_trat_g) = ANY (l.gruppi_coperti)),
  '14. un documento trattenuto da un lotto VIVO non viene riofferto a un secondo giro'
);

-- ⭐ IL VERSO OPPOSTO: annullato il lotto, il documento torna disponibile — e
--   l'esito e' rimasto COMPLETED, cioe' non e' lui a decidere.
UPDATE vendite.fatturazione_lotti
   SET stato_doc_fiscale_id = (SELECT sdf.id FROM config.stati_doc_fiscale sdf
                                WHERE sdf.codice_interno = 'ANNULLATA')
 WHERE id = (SELECT id FROM tmp_trat_lotto);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM vendite.fn_list_emittibili_lane(
             p_competenza_mese => DATE '2026-07-01',
             p_emittente_soggetto_ruolo_id => (SELECT e FROM tmp_e)) l
     WHERE (SELECT k FROM tmp_trat_g) = ANY (l.gruppi_coperti)),
  '15. annullato il lotto il documento torna offerto: decide lo STATO, non l''esito'
);

SELECT * FROM finish();

ROLLBACK;
