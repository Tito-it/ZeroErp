-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_email_ambito_perimetro — la regola dell'ambito delle
--   email, con chi guarda gia' calcolato dalla policy.
--   Brief: brief-db-perimetro-una-volta-famiglie-residue §9 (giro 5),
--   changeSet 20261021-41.
--
-- ⭐ La funzione e' PURA: non legge tabelle, quindi la regola si prova con i
--   valori, ramo per ramo e nei due versi, senza fixture. Gli argomenti:
--   (super_admin, uo di chi guarda, processo, perimetro emittenti, utente,
--    ambito, emittente della mail, reparto della mail, autore della mail).
--   Il perimetro segue la convenzione dell'operatore: NULL = tutti.
--
-- Indice test (plan 14):
--    1. SISTEMA: super admin -> vede
--    2. SISTEMA: il processo -> vede
--    3. ⛔ SISTEMA: ne' l'uno ne' l'altro -> no, anche se autore e reparto coincidono
--    4. REPARTO: stesso reparto ed emittente nel perimetro -> vede
--    5. ⛔ REPARTO: stesso reparto ma emittente FUORI perimetro -> no
--    6. ⛔ REPARTO: altro reparto -> no
--    7. ⛔ REPARTO: chi guarda senza reparto (NULL) -> no (fail-closed)
--    8. REPARTO: super admin, perimetro tutti -> vede
--    9. OPERATORE: l'autore, emittente nel perimetro -> vede
--   10. ⛔ OPERATORE: l'autore, emittente fuori perimetro -> no (l'emittente resta in AND)
--   11. ⛔ OPERATORE: non l'autore -> no
--   12. OPERATORE: il processo, emittente nel perimetro -> vede
--   13. ⛔ un ambito sconosciuto -> no
--   14. ⛔ ambito NULL -> false, non NULL
-- BEGIN; + rollback a fine file.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- Chi guarda: utente 7, reparto 3, perimetro emittenti {10, 11}.
-- La mail: emittente 10 (dentro) o 99 (fuori), reparto 3 o 4, autore 7 o 8.

-- SISTEMA
SELECT is(script.fn_scope_email_ambito_perimetro(true,  3, false, ARRAY[10, 11]::bigint[], 7, 'SISTEMA', 10, 3, 7), true,
          '1. SISTEMA: il super admin vede');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, true,  ARRAY[10, 11]::bigint[], 7, 'SISTEMA', 10, 3, 7), true,
          '2. SISTEMA: il processo vede');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'SISTEMA', 10, 3, 7), false,
          '3. SISTEMA: ne'' super admin ne'' processo: no, anche da autore e dello stesso reparto');

-- REPARTO
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'REPARTO', 10, 3, 8), true,
          '4. REPARTO: stesso reparto ed emittente nel perimetro: vede');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'REPARTO', 99, 3, 8), false,
          '5. REPARTO: stesso reparto ma emittente fuori perimetro: no');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'REPARTO', 10, 4, 7), false,
          '6. REPARTO: altro reparto: no, anche da autore');
SELECT is(script.fn_scope_email_ambito_perimetro(false, NULL, false, ARRAY[10, 11]::bigint[], 7, 'REPARTO', 10, 3, 8), false,
          '7. REPARTO: chi guarda senza reparto: no (fail-closed)');
SELECT is(script.fn_scope_email_ambito_perimetro(true,  NULL, false, NULL::bigint[], 7, 'REPARTO', 99, 4, 8), true,
          '8. REPARTO: super admin col perimetro tutti: vede');

-- OPERATORE
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'OPERATORE', 10, 4, 7), true,
          '9. OPERATORE: l''autore, emittente nel perimetro: vede');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'OPERATORE', 99, 4, 7), false,
          '10. OPERATORE: l''autore ma emittente fuori perimetro: no');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, false, ARRAY[10, 11]::bigint[], 7, 'OPERATORE', 10, 3, 8), false,
          '11. OPERATORE: non l''autore, anche dello stesso reparto: no');
SELECT is(script.fn_scope_email_ambito_perimetro(false, 3, true,  ARRAY[10, 11]::bigint[], 7, 'OPERATORE', 10, 4, 8), true,
          '12. OPERATORE: il processo, emittente nel perimetro: vede');

-- Bordi
SELECT is(script.fn_scope_email_ambito_perimetro(true,  3, true,  NULL::bigint[], 7, 'ALTRO', 10, 3, 7), false,
          '13. un ambito sconosciuto: no, anche per il super admin');
SELECT is(script.fn_scope_email_ambito_perimetro(true,  3, true,  NULL::bigint[], 7, NULL, 10, 3, 7), false,
          '14. ambito NULL: false, non NULL');

SELECT * FROM finish();
ROLLBACK;
