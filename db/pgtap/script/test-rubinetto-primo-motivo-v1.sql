-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: P-2 — IL RUBINETTO della coda «solleva il primo motivo»
--       Piano: brief-db-coda-primo-motivo-in-un-posto-solo, sezione 7
-- ------------------------------------------------------------
-- Elenco test (plan 7) — numerati come li stampa il TAP:
--  1) l'helper esiste, con la firma dichiarata
--  2) ⭐⭐ IL RUBINETTO: zero punti IN PERIMETRO sollevano il primo motivo a mano
--  3) ⭐ zero punti NON CLASSIFICATI — un presidio che non sa leggere un sito
--        deve diventare ROSSO, non saltarlo
--  4) il debito FUORI perimetro non cresce (soglia 13, puo' solo calare)
--  5) le dieci funzioni bonificate chiamano davvero l'helper
--  6) ⚠️ il marcatore non e' troppo LARGO: un codice LETTERALE resta fuori
--  7) ⭐⭐ la canarina: il marcatore non e' troppo STRETTO
--
-- Scopo:
--   ⭐⭐ QUESTO E' IL PRESIDIO CHE CONTA, piu' della bonifica. Senza, i dieci
--   punti sanati tornano: chi scrive una fn_check_* copia la coda dalla guard
--   accanto, ed e' cosi' che si e' arrivati a ventitre' senza che nessuno
--   avesse deciso niente. «Rincorrere gli esistenti senza chiudere il rubinetto
--   e' la forma in cui questi registri non calano mai.»
--
--   ⭐ IL PERIMETRO SI DERIVA, NON SI ELENCA. Un punto e' in perimetro quando
--   fa DUE cose insieme:
--     1) il CODICE che solleva non e' un letterale: lo legge da un motivo
--     2) la fn_check_* da cui viene l'array emette `valori`
--   Solo li' l'helper puo' stare. Dove la check NON emette `valori` la frase la
--   compone il chiamante dai propri dati, e delegare la spezzerebbe:
--   uscirebbero i `%s` grezzi a video (§2.2 del brief). ⇒ Li' il `-> 0` e'
--   LEGITTIMO, e pretendere zero anche li' sarebbe un cancello che boccia il
--   caso giusto — dopo due blocchi sbagliati qualcuno lo spegne.
--   ⭐ Derivandolo, una check che domani aggiunge `valori` fa entrare il suo
--   sito nel perimetro DA SOLA, senza che nessuno aggiorni un elenco.
--
--   🔴 IL MARCATORE E' `->> 'codice'` E NON `-> 0 ->> 'codice'`, e questa riga
--   e' costata una prova per mutazione. Col secondo, il presidio era VERDE PER
--   COSTRUZIONE: prendeva solo la forma scritta INLINE, mentre i dieci siti
--   bonificati usano una variabile d'appoggio —
--       v_primo := v_motivi -> 0;      <- riga a se'
--       ... v_primo ->> 'codice' ...   <- dentro la chiamata
--   cioe' proprio la forma che questo cantiere ha appena tolto non era
--   presidiabile. Rimessa a mano una coda vecchia, il conteggio non si muoveva.
--   ⇒ L'invariante VERO non e' come e' scritto l'indice: e' che **il codice non
--   e' un letterale**. Ed e' lo stesso fatto che rende questi siti invisibili
--   al rubinetto degli accumulatori, che i letterali `'E_...'` li cerca (§7.3).
--
--   ⚠️ QUESTO FILE LEGGE `pg_proc.prosrc`, cioe' il TESTO delle funzioni. E'
--   un'euristica, e va detto: riconosce la forma scritta, non il significato.
--   Per questo esistono il test 3 (un sito che non si riesce a legare alla sua
--   check e' ROSSO, non saltato) e il test 7 (la canarina che si accorge se il
--   marcatore viene ristretto).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture — la classificazione, in una vista temporanea sola: i test la
--   interrogano invece di ripetere la derivazione cinque volte (e di poter
--   divergere fra loro, che e' il difetto classico dei presidi copiati).
-- ============================================================

CREATE TEMP VIEW punti_primo_motivo AS
WITH punti AS (
    SELECT n.nspname AS sch, p.proname AS fn, p.prosrc
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
       -- ⭐ Il codice non e' un letterale: viene da un motivo. Prende sia la
       --   forma con la variabile d'appoggio sia quella inline.
       AND p.prosrc ~ 'fn_log_and_raise_error\s*\([^;]*->> ''codice'''
       -- ⛔ L'helper e' la SEDE della coda, non un suo residuo: e' l'unico
       --   posto del database dove quella forma e' giusta.
       AND NOT (n.nspname = 'script' AND p.proname = 'fn_raise_primo_motivo_se_presente')
), legami AS (
    -- ⚠️ Si cercano TUTTE le fn_check_* nominate nel corpo, non solo quella
    --   assegnata a `v_motivi`: vendite.trgfn_commesse_guard_transizione ne
    --   sceglie una fra TRE con un CASE, e un riconoscimento ancorato a `:=`
    --   la perdeva — cioe' il presidio aveva un ramo cieco proprio dove il
    --   codice e' piu' articolato.
    SELECT pt.sch, pt.fn, m[1] AS csch, m[2] AS cfn
      FROM punti pt
     CROSS JOIN LATERAL regexp_matches(pt.prosrc, '(\w+)\.(fn_check_\w+)\s*\(', 'g') m
)
SELECT pt.sch,
       pt.fn,
       count(c.oid)                                      AS check_trovate,
       -- ⭐ PESSIMISTA: basta UNA delle check nominate che emetta `valori`
       --   perche' il sito sia in perimetro. Un presidio che sceglie il ramo
       --   ottimista assolve il caso che dovrebbe segnalare.
       coalesce(bool_or(c.prosrc ~ '''valori'''), false) AS in_perimetro
  FROM punti pt
  LEFT JOIN legami l  ON l.sch = pt.sch AND l.fn = pt.fn
  LEFT JOIN pg_proc c ON c.proname = l.cfn
  LEFT JOIN pg_namespace cn ON cn.oid = c.pronamespace AND cn.nspname = l.csch
 GROUP BY pt.sch, pt.fn;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) L'helper c'e', e con la firma che il brief dichiara. ⚠️ Il confronto
--    include i NOMI dei parametri, perche' pg_get_function_identity_arguments()
--    li restituisce: scritta coi soli tipi, questa asserzione e' rossa a vuoto.
SELECT is(
    (SELECT pg_get_function_identity_arguments(p.oid)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_raise_primo_motivo_se_presente'),
    'p_area text, p_funzione text, p_motivi jsonb, p_campo text, p_tx_id uuid, p_context_extra jsonb',
    'script.fn_raise_primo_motivo_se_presente esiste con la firma dichiarata');

-- 2) ⭐⭐ IL RUBINETTO. Zero, e non «pochi»: qui l'helper puo' stare, quindi
--    ogni punto rimasto e' una coda copiata.
SELECT is(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE in_perimetro),
    0,
    'nessun punto IN PERIMETRO solleva ancora il primo motivo a mano');

-- 3) ⭐ Il ramo cieco e' rosso. Un punto marcato di cui non si trovi nessuna
--    fn_check_* non e' «a posto»: e' un sito che il presidio non sa leggere, e
--    un presidio che salta cio' che non capisce diventa verde per sottrazione.
SELECT is(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE check_trovate = 0),
    0,
    'ogni punto marcato si riesce a legare alla sua check: nessun ramo cieco');

-- 4) Il debito fuori perimetro. ⚠️ E' un REGISTRO, non una lista di eccezioni:
--    la soglia puo' solo calare. Cala quando una di quelle check impara a
--    emettere `valori` e il suo sito passa all'helper — il cantiere lasciato
--    aperto nel §6 del brief.
--    ⛔ Non si alza per far passare la CI: un numero piu' alto significa che
--    qualcuno ha scritto una coda nuova, ed e' esattamente la cosa da vedere.
SELECT cmp_ok(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE NOT in_perimetro),
    '<=', 13,
    'il debito dei siti FUORI perimetro non cresce (soglia 13, puo'' solo calare)');

-- 5) La bonifica e' arrivata dove diceva: dieci funzioni chiamano l'helper.
--    ⭐ E' il test che ha morso nella prova per mutazione, quando il 2 non
--    mordeva: rimessa una coda vecchia, qui il conteggio scende a nove.
SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE p.prosrc ~ 'fn_raise_primo_motivo_se_presente'
        AND p.proname <> 'fn_raise_primo_motivo_se_presente'),
    10,
    'le dieci funzioni della forma A chiamano l''helper');

-- 6) ⚠️ Il marcatore non e' troppo LARGO. vendite.fn_cleanup_fatture_by_ids
--    solleva un codice LETTERALE e dal primo motivo legge solo un valore per la
--    frase (`-> 0 ->> 'dettaglio'`): con un marcatore su `-> 0` entrerebbe nel
--    perimetro e sarebbe un falso positivo. Se questo test diventa rosso,
--    qualcuno ha allargato il marcatore e il cancello ha cominciato a bocciare
--    il caso giusto.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM punti_primo_motivo
                 WHERE sch = 'vendite' AND fn = 'fn_cleanup_fatture_by_ids'),
    'un sito che solleva un codice LETTERALE resta fuori dal perimetro');

-- 7) ⭐⭐ LA CANARINA: il marcatore non e' troppo STRETTO. L'helper e' l'unico
--    posto dove la coda vive ancora, e la scrive nella forma con la variabile
--    d'appoggio — la stessa dei dieci siti bonificati. Se il marcatore smette
--    di riconoscerla, questo test si accorge PRIMA che il rubinetto diventi
--    verde per costruzione.
--    ⚠️ E' successo davvero: la prima stesura cercava `-> 0 ->> 'codice'` e non
--    vedeva nessuno dei dieci. Solo una prova per mutazione l'ha mostrato.
SELECT ok(
    (SELECT p.prosrc ~ 'fn_log_and_raise_error\s*\([^;]*->> ''codice'''
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_raise_primo_motivo_se_presente'),
    'il marcatore riconosce la forma con la variabile d''appoggio (canarina)');

SELECT * FROM finish();
ROLLBACK;
