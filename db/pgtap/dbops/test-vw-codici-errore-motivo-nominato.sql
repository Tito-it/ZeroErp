-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: V-1 — dbops.vw_codici_errore_forme_condizione riconosce la forma
--       «CODICE NOMINATO IN UN MOTIVO», cioe' il pattern linee-guida-sql §12.5
--       in cui il letterale E_* sta dentro la fn_check_* e non accanto alla
--       chiamata che solleva.
--
-- Elenco test (plan 8) — numerati come li stampa il TAP:
--  1) un codice nominato SOLO come motivo compare nella vista
--  2) ⭐ e prende la famiglia della guardia che sta DENTRO la check
--  3) ⛔ il verso che tiene onesto il 2: una guardia illeggibile resta IGNOTO
--  4) ⚠️ il marcatore non e' troppo LARGO: una menzione senza la chiave
--        'codice' e senza chiamata vicina NON diventa un punto
--  5) ⚠️ il marcatore e' per FORMA e non per NOME di funzione
--  6) ⭐ sul codice vivo: i codici-motivo che restano invisibili sono un debito
--        DICHIARATO, e puo' solo calare
--  7) ⚠️ una guardia su un PARAMETRO nullo resta PARAMETRO
--  8) ⛔ ma un CAMPO di un parametro record non lo e': e' dominio, non un
--        chiamante rotto
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' IL TEST 2 E' IL CUORE, e non il test 1.
--   Il test 1 passerebbe anche su una vista che risale dal punto che SOLLEVA
--   alla check e le attribuisce i suoi codici: i codici comparirebbero.
--   Comparirebbero pero' tutti sotto IGNOTO, perche' sopra il punto che solleva
--   la guardia e' sempre «IF jsonb_array_length(v_motivi) > 0», identica ovunque
--   e muta sul perche'. E IGNOTO lo snapshot del rubinetto B-7 lo SCARTA
--   (`WHERE NOT solo_ignoto`): zero candidati nuovi, e una copertura che sembra
--   cresciuta di 35. ⇒ Il test 2 e' l'unico che distingue le due
--   implementazioni, ed e' la ragione per cui questo file esiste.
--
-- ⛔ I CASI SI COSTRUISCONO, non si cercano nel codice esistente. Un test che
--   frugasse fra le fn_check_* di oggi proverebbe soltanto i casi che questa
--   popolazione per caso contiene, e su un database ricostruito da zero
--   girerebbe identico solo per coincidenza. Qui le funzioni-testimone le
--   scrive il test. L'eccezione e' il 6, che e' un debito e va misurato dove
--   vive.
--
-- ⚠️ I TESTIMONI NON CHIAMANO fn_log_and_raise_error, ed e' il punto: una
--   fn_check_* e' PURA, nomina i codici e non solleva. Se un giorno questi
--   corpi acquistassero una chiamata, i test 1-3 passerebbero per la vecchia
--   strada (`chiamata_vicina`) senza provare piu' niente della forma nuova.
--
-- Brief: brief-db-i-motivi-si-fermano-dentro-la-check.md (V-1)
-- ChangeSet: 20260908-35-update-vw-codici-errore-forme-condizione-motivo-nominato
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Le funzioni-testimone
-- ============================================================
-- ⭐ La forma canonica del §12.5: una guardia che il classificatore sa leggere,
--   e sotto il motivo che NOMINA il codice. Nessuna chiamata: la check e' pura.
CREATE FUNCTION pg_temp.pgtap_motivo_valore_atteso() RETURNS jsonb
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_stato  text  := 'APERTO';
BEGIN
    IF v_stato = 'CHIUSO' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PGTAP_MOTIVO_VALORE_ATTESO',
            'reason',     'GIA_CHIUSO',
            'reason_key', 'pgtap.motivo.gia_chiuso',
            'dettaglio',  v_stato);
    END IF;
    RETURN v_motivi;
END
$f$;

-- ⛔ Stessa forma, guardia che nessuna regola sa leggere: un confronto fra due
--   variabili. Deve restare IGNOTO — «non so», che e' una risposta onesta.
CREATE FUNCTION pg_temp.pgtap_motivo_illeggibile() RETURNS jsonb
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_a integer := 1;
    v_b integer := 2;
BEGIN
    IF v_a > v_b THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PGTAP_MOTIVO_ILLEGGIBILE',
            'reason',     'ILLEGGIBILE',
            'reason_key', 'pgtap.motivo.illeggibile',
            'dettaglio',  v_a);
    END IF;
    RETURN v_motivi;
END
$f$;

-- ⚠️ Il nome NON dice fn_check_*, e il motivo e' dichiarato lo stesso: il
--   marcatore guarda la FORMA. Un filtro su `proname LIKE 'fn_check_%'` avrebbe
--   dato per perimetro quell'elenco, e nel database vivo perderebbe le due
--   righe di script.fn_available_actions_ordine / _preventivo.
CREATE FUNCTION pg_temp.pgtap_motivo_fuori_dal_nome() RETURNS jsonb
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_tipo   text  := 'ALTRO';
BEGIN
    IF v_tipo = 'RESO' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PGTAP_MOTIVO_FUORI_DAL_NOME',
            'reason',     'FUORI_DAL_NOME',
            'reason_key', 'pgtap.motivo.fuori_dal_nome',
            'dettaglio',  v_tipo);
    END IF;
    RETURN v_motivi;
END
$f$;

-- ⚠️ Una MENZIONE, non un motivo: il letterale c'e', ma non sotto la chiave
--   'codice' e senza nessuna chiamata vicina. Non e' un punto di sollevamento e
--   non deve entrare — altrimenti il marcatore ha cominciato a prendere
--   qualunque stringa E_* del database.
CREATE FUNCTION pg_temp.pgtap_motivo_solo_menzione() RETURNS jsonb
LANGUAGE plpgsql AS $f$
DECLARE
    v_esito text := 'OK';
BEGIN
    IF v_esito = 'OK' THEN
        RETURN jsonb_build_object('precedente', 'E_PGTAP_MOTIVO_SOLO_MENZIONE');
    END IF;
    RETURN '{}'::jsonb;
END
$f$;

-- ⚠️ Una guardia su un PARAMETRO nullo: e' PARAMETRO, e deve restarlo. E' il
--   verso che impedisce di svuotare la regola mentre la si stringe (test 8).
CREATE FUNCTION pg_temp.pgtap_motivo_param_vero(p_documento_id bigint) RETURNS jsonb
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
BEGIN
    IF p_documento_id IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PGTAP_MOTIVO_PARAM_VERO',
            'reason',     'PARAM_VERO',
            'reason_key', 'pgtap.motivo.param_vero',
            'dettaglio',  'x');
    END IF;
    RETURN v_motivi;
END
$f$;

-- ⛔ Un CAMPO di un parametro RECORD, invece, non e' un parametro: `p_doc` e' il
--   documento, `causa` un suo campo, e la condizione e' «manca un dato», cioe'
--   qualcosa che una persona corregge. PARAMETRO significa l'opposto — «chi mi
--   ha chiamato e' rotto», l'asse TECNICO/500 su cui non c'e' nessun campo da
--   accendere. Il classificatore le confondeva proprio sull'asse per cui esiste.
--   ⇒ Deve cadere in IGNOTO: «non so leggerla» e' la risposta onesta.
CREATE FUNCTION pg_temp.pgtap_motivo_param_campo(p_doc config.messaggi_errore) RETURNS jsonb
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
BEGIN
    IF p_doc.causa IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PGTAP_MOTIVO_PARAM_CAMPO',
            'reason',     'PARAM_CAMPO',
            'reason_key', 'pgtap.motivo.param_campo',
            'dettaglio',  'x');
    END IF;
    RETURN v_motivi;
END
$f$;

-- ============================================================
-- 1) Il codice nominato solo come motivo COMPARE
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.vw_codici_errore_forme_condizione
             WHERE codice = 'E_PGTAP_MOTIVO_VALORE_ATTESO'),
    '1. un codice nominato SOLO dentro un motivo compare nella vista'
);

-- ============================================================
-- 2) ⭐ E prende la famiglia della guardia che sta DENTRO la check
-- ============================================================
-- ⛔ E' l'asserzione che distingue questa implementazione da quella scartata.
--   Con la risalita «dal punto che solleva» qui uscirebbe {IGNOTO}, il codice
--   verrebbe scartato dallo snapshot del rubinetto e la copertura sembrerebbe
--   cresciuta senza che nessun accumulatore diventasse visibile.
SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_MOTIVO_VALORE_ATTESO'),
    ARRAY['VALORE_ATTESO'],
    '2. la famiglia viene dalla guardia DENTRO la check, non da «c''e'' un motivo?»'
);

-- ============================================================
-- 3) ⛔ Il verso che tiene onesto il 2
-- ============================================================
-- Senza, il test 2 passerebbe anche su un classificatore che risponde SEMPRE
-- VALORE_ATTESO, cioe' su un asse che ha smesso di distinguere.
SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_MOTIVO_ILLEGGIBILE'),
    ARRAY['IGNOTO'],
    '3. una guardia che nessuna regola sa leggere resta IGNOTO anche su un motivo'
);

-- ============================================================
-- 4) ⚠️ Il marcatore non e' troppo LARGO
-- ============================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_codici_errore_forme_condizione
                 WHERE codice = 'E_PGTAP_MOTIVO_SOLO_MENZIONE'),
    '4. un E_* menzionato fuori dalla chiave ''codice'' non diventa un punto'
);

-- ============================================================
-- 5) ⚠️ Per FORMA, non per NOME di funzione
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.vw_codici_errore_forme_condizione
             WHERE codice = 'E_PGTAP_MOTIVO_FUORI_DAL_NOME'),
    '5. un motivo dichiarato fuori da una fn_check_* entra lo stesso'
);

-- ============================================================
-- 6) ⭐ Il debito che resta, dichiarato invece che scoperto dopo
-- ============================================================
-- ⚠️ Non tutti i codici-motivo del database vivo arrivano al classificatore:
--   quattro cadono sulla regola PREESISTENTE «al massimo venticinque righe fra
--   la guardia e il punto» (distanze misurate il 2026-09-08: 51, 32, 53, 37).
--   Non e' un difetto di questa consegna — vale identica sui punti a codice
--   letterale — ma va DICHIARATO: un test che pretendesse zero sarebbe rosso a
--   vuoto, e uno che non guardasse affatto lascerebbe crescere il buco.
-- ⛔ La soglia puo' solo CALARE. Se sale, qualcuno ha scritto una fn_check_*
--   con la guardia lontana dal motivo, ed e' la cosa da vedere.
-- ⚠️ Si escludono i testimoni di questo file, altrimenti il test si
--   risponderebbe da solo.
SELECT cmp_ok(
    (SELECT count(DISTINCT m.cod)::int
       FROM (SELECT (regexp_match(l.riga, '''(E_[A-Z0-9_]+)'''))[1] AS cod
               FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
               CROSS JOIN LATERAL regexp_split_to_table(p.prosrc, E'\n') l(riga)
              WHERE p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
                AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND l.riga !~ '^\s*--'
                AND l.riga ~ '''codice''\s*,\s*''E_[A-Z0-9_]+''') m
      WHERE m.cod NOT LIKE 'E_PGTAP_%'
        AND NOT EXISTS (SELECT 1 FROM dbops.vw_codici_errore_forme_condizione v
                         WHERE v.codice = m.cod)),
    '<=', 4,
    '6. i codici-motivo che restano invisibili sono un debito dichiarato (soglia 4, puo'' solo calare)'
);

-- ============================================================
-- 7-8) ⭐ PARAMETRO: il parametro si', il suo CAMPO no
-- ============================================================
-- ⚠️ Vanno letti INSIEME. Il solo 8 passerebbe anche su una regola PARAMETRO
--   svuotata — cioe' su un asse che ha smesso di riconoscere i guard di
--   parametro, che sono la maggioranza; il 7 e' il verso che lo impedisce.
--   ⛔ Chi un giorno «ripulisse» la regola togliendo il `(?!\s*\.)` vedrebbe
--   rosso l'8 e non il 7, ed e' l'informazione giusta.
SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_MOTIVO_PARAM_VERO'),
    ARRAY['PARAMETRO'],
    '7. una guardia su un PARAMETRO nullo resta PARAMETRO'
);

SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_MOTIVO_PARAM_CAMPO'),
    ARRAY['IGNOTO'],
    '8. un CAMPO di un parametro record non e'' PARAMETRO: e'' dominio, e cade in IGNOTO'
);

SELECT * FROM finish();
ROLLBACK;
