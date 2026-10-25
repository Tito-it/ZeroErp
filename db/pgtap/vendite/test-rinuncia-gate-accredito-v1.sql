-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), l'attivita' da dbops.fn_pgtap_crea_commessa_attivita (sorgente DDT_VENDITA, E-3), la fattura agganciata da dbops.fn_pgtap_fattura_attivita: ritirati pg_temp.rin_fattura e pg_temp.ann_reset_lotto (definito e mai chiamato, E-4).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso per ri-consegna dal builder dbops.fn_pgtap_crea_reso (che concede da se' conferma_reso); restano scritte a mano la rinuncia (chiusura e riapertura della ri-consegna) e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso (giro 2), la rinuncia e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: script.fn_check_rinuncia_reversibile — il gate NC si e' svegliato
--       (P-3 / passo 4, changeset 20260819-02)
-- ------------------------------------------------------------
-- ⛔ Prima di 20260819-02 questo file NON arriva in fondo, ed e' il difetto che
--    misura. Corsa del 2026-08-19, senza il changeset:
--      1, 2   verdi  (la fixture regge: rinuncia creata, riga in coda)
--      3      have NULL, want E_RESO_RINUNCIA_ACCREDITO_ESEGUITO|...
--      4      «no exception thrown»  <- ⭐ il difetto in tre parole: la madre
--             non si oppone, e la rinuncia SI RIAPRE davvero
--      5..8   non eseguiti: avendo riaperto per davvero al test 4, il test 6
--             trova E_RESO_NESSUNA_RICONSEGNA_PENDENTE e la transazione muore
--             («Bad plan. You planned 8 tests but ran 5»)
--    ⚠️ La cascata NON e' un difetto del test: e' la conseguenza diretta del
--    fatto che al test 4 il divieto non morde. Con il changeset applicato il
--    test 4 solleva, non riapre niente, e 5-8 girano.
--
-- Indice test (1..8):
--   1) fixture: la riga e' in coda accrediti e la ri-consegna e' stata chiusa
--   2) PRIMA dell'accredito il gate e' vuoto: la rinuncia si puo' riaprire
--   3) ⭐ dopo l'accredito il gate produce ACCREDITO_ESEGUITO, col codice giusto
--   4) ⭐ e la MADRE lo solleva da se': fn_riapri_riconsegna_reso rifiuta —
--      e' il pezzo che dimostra che il gate non e' decorativo
--   5) ⭐⭐ dopo l'ANNULLO il gate torna vuoto: l'auto-riparazione di C-3
--   6) ⭐ e la madre RIESCE davvero: la rinuncia si riapre
--   7) il ramo storico non e' stato rotto: riga inesistente -> RIGA_INESISTENTE
--   8) guard sul parametro: id nullo -> errore di dominio (P0001)
--
-- ⭐ PERCHE' SI PASSA DALLA MADRE (test 4 e 6) E NON SOLO DAL GATE.
--    Il gate e' una funzione PURA: da sola produce un elenco che nessuno e'
--    obbligato a leggere. Che il divieto MORDA lo dice solo
--    vendite.fn_riapri_riconsegna_reso, che solleva il primo motivo prodotto.
--    Un test sul solo gate direbbe «l'elenco contiene la voce giusta», non
--    «la rinuncia non si riapre».
--
-- ⚠️ NOTA DI CONTRATTO, verificata: la madre solleva
--    `v_motivi -> 0 ->> 'codice'` passando UN SOLO valore (resi_riga_id). Ogni
--    codice prodotto da questo gate deve quindi avere arita' <= 1, o
--    l'errore di dominio sparirebbe in un 22023.
--
-- ⚠️ Il tipo di reso e' RESO_PER_RICONSEGNA (riapre_residuo = true): senza,
--    trgfn_resi_rinunce_guard rifiuta la rinuncia e la fixture non arriva
--    nemmeno al soggetto del test.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_acc AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP rinuncia gate');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_acc)); END $ctx$;

SELECT plan(10);

CREATE TEMP TABLE tmp_refs_rin AS
SELECT
  m.billing_account_id                         AS billing_account_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-RIN-GATE', false)                  AS articolo_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_acc m;

-- ============================================================
-- FIXTURE: consegnati 10 a 25, fatturati 10, resi 3 per RI-CONSEGNA,
--   poi la ri-consegna viene CHIUSA -> nasce la rinuncia.
-- ============================================================
-- La partita (bolla CONSEGNATA da ordine) e' del builder
-- dbops.fn_pgtap_crea_ddt_da_ordine; la merce viene FATTURATA per intero
-- (attivita' sul segmento della bolla, emessa, agganciata a una fattura vera):
-- e' la catena che la madre risale per copiare il prezzo.
CREATE TEMP TABLE tmp_com_rin AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('rinuncia gate', NULL,
           (SELECT billing_account_id FROM tmp_refs_rin), p_con_sorgente_root => true) c;

CREATE TEMP TABLE tmp_pr AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('rinuncia gate',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_rin),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_rin),
           p_fatturazione_trigger => 'CONSEGNATO') b;
-- E-3: l'attivita' sul segmento della bolla dichiara la sorgente DDT_VENDITA.
CREATE TEMP TABLE tmp_pr_att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_rin), 25,
           p_articolo_id      => (SELECT articolo_id FROM tmp_refs_rin),
           p_sorgente_codice  => 'DDT_VENDITA',
           p_sorgente_uid     => (SELECT ddt_uid FROM tmp_pr)::text,
           p_sorgente_riga_id => (SELECT ddt_riga_id FROM tmp_pr),
           p_quantita         => 10);
CREATE TEMP TABLE tmp_pr_fattura AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('rinuncia gate',
           ARRAY[(SELECT attivita_id FROM tmp_pr_att)]);
-- Il reso per ri-consegna di 3, confermato.
CREATE TEMP TABLE tmp_pr_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('rinuncia gate', (SELECT ddt_id FROM tmp_pr), 3,
                                       'RESO_PER_RICONSEGNA',
                                       p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pr));

-- La ri-consegna si chiude: la quota diventa definitivamente non ri-spedibile
-- e nasce la riga in vendite.resi_righe_rinunce, che e' il soggetto del gate.
SELECT vendite.fn_chiudi_riconsegna_reso((SELECT reso_id FROM tmp_pr_reso));

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_rinunce x
     WHERE x.resi_riga_id = (SELECT resi_riga_id FROM tmp_pr_reso))::text
  || '|' ||
  (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare q
     WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pr_reso))::text,
  '1|1',
  '1) fixture: la ri-consegna e'' chiusa (una rinuncia) e la riga e'' in coda accrediti'
);

SELECT is(
  script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)),
  '[]'::jsonb,
  '2) PRIMA dell''accredito il gate e'' vuoto: la rinuncia si puo'' riaprire'
);

-- ============================================================
-- IL VERBO
-- ============================================================
CREATE TEMP TABLE tmp_acc_rin AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pr_reso));

SELECT is(
  (SELECT script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)) -> 0 ->> 'codice'
   || '|' ||
   (script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)) -> 0 ->> 'reason')),
  'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO|ACCREDITO_ESEGUITO',
  '3) dopo l''accredito il gate produce il motivo, col codice e la reason giusti'
);

-- ⭐ P-1 — LA FRASE RESA. E' l'unica verifica che vede l'ORDINE dei valori:
--   il ramo C di test-catalogo-messaggi-errore-completo.sql prova che sono
--   TANTI QUANTI i segnaposto, non che siano quelli giusti al posto giusto.
--   Il precedente e' del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA — due
--   valori, due segnaposto, «Registro X1» a video con la serie al posto della
--   famiglia — e nel 2026-09-09 lo stesso difetto e' stato trovato VIVO su due
--   siti di questo cantiere.
-- ⚠️ Si confronta con la frase composta dai valori letti dalla TABELLA: se la
--   check li emettesse invertiti, le due stringhe divergerebbero. Un `matches`
--   su un pezzo di frase non lo vedrebbe.
-- ⚠️ Il CASE con `coalesce` non e' pignoleria: senza, una check che smettesse
--   di emettere `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file.
--   E scritto con un `<>` nudo non guarderebbe niente: `jsonb_typeof(NULL) <>
--   'array'` vale NULL, non vero.
SELECT is(
  (WITH v AS (SELECT script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT format((SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO' AND m.lingua = 'it'),
                 (SELECT resi_riga_id FROM tmp_pr_reso)::text)),
  '3-bis) la frase resa nomina la RIGA DI RESO');

-- ⭐ IL CASO A ZERO SEGNAPOSTO, e vale la riga a se': «Reso non trovato.» non
--   ha `%s`, quindi il suo `valori` e' un array VUOTO — che e' un valore, non
--   una dimenticanza. Con zero valori fn_log_and_raise_error salta il ramo
--   format() e il testo arriva intero.
--   ⛔ Il difetto da vedere qui e' l'opposto degli altri: un `%s` che resta a
--   video LETTERALE perche' nessuno lo riempie (test 4 del catalogo messaggi).
--   ⚠️ Le due arita' diverse sulla stessa check (0 e 1) sono il caso che il
--   chiamante a valori FISSI non poteva servire: e' la ragione per cui questa
--   check e' entrata nel cantiere.
SELECT is(
  (WITH v AS (SELECT script.fn_check_rinuncia_reversibile(999999999) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_NOT_FOUND' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_NOT_FOUND' AND m.lingua = 'it'),
  '3-ter) il motivo a ZERO segnaposto rende il testo intero, senza %s a video');

-- ⭐ Che il divieto MORDA lo dice solo la madre: il gate da solo produce un
--    elenco che nessuno e' obbligato a leggere.
SELECT throws_like(
  format($$ SELECT vendite.fn_riapri_riconsegna_reso(%s) $$,
         (SELECT reso_id FROM tmp_pr_reso)),
  '%accredito e'' gia'' stato eseguito%',
  '4) e la MADRE lo solleva da se'': la rinuncia NON si riapre'
);

-- ============================================================
-- 5-6) ⭐⭐ L'AUTO-RIPARAZIONE DI C-3, nei due versi.
--   Il gate non sa nulla dell'annullo: torna vuoto solo perche' l'annullo
--   CANCELLA le righe di ponte. Se un giorno diventasse un soft-delete,
--   questi due test diventerebbero rossi — ed e' esattamente il loro scopo.
-- ============================================================
SELECT vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_pr_reso), 'ci ho ripensato, pgTAP');

SELECT is(
  script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)),
  '[]'::jsonb,
  '5) dopo l''ANNULLO il gate torna vuoto: si auto-ripara senza sapere nulla dell''annullo'
);

SELECT is(
  (SELECT vendite.fn_riapri_riconsegna_reso((SELECT reso_id FROM tmp_pr_reso)))::int,
  1,
  '6) e la madre RIESCE davvero: la rinuncia si riapre, il round-trip si chiude'
);

-- ============================================================
-- I rami che c'erano prima, non rotti
-- ============================================================
SELECT is(
  script.fn_check_rinuncia_reversibile(999999999) -> 0 ->> 'reason',
  'RIGA_INESISTENTE',
  '7) il ramo storico regge: una riga inesistente resta RIGA_INESISTENTE'
);

SELECT throws_ok(
  $$ SELECT script.fn_check_rinuncia_reversibile(NULL) $$,
  'P0001', NULL,
  '8) guard sul parametro: id nullo -> errore di dominio, mai normalizzazione silenziosa'
);

SELECT * FROM finish();
ROLLBACK;
