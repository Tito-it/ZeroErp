-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_is_super_admin
-- Riferimento: §4.6.B.1 WIP multi-face-auth (ADMIN come profilo).
--
-- Semantica attesa:
--   - NULL auth_user -> false
--   - Identita inesistente -> false
--   - Identita attiva + binding SUPER_ADMIN attivo -> true
--   - Identita attiva + binding inattivo -> false
--   - Identita inattiva + binding attivo -> false (rev 2026-09-25: lo stato
--     ESISTE — porta e profili sganciati — e il caso 6 lo collauda)
--   - Profilo SUPER_ADMIN inattivo -> false
--   - Identita fuori finestra temporale -> false
--
-- Pattern: tre OPERATORI costruiti con dbops.fn_pgtap_crea_operatore_umano,
-- dal percorso di produzione (persona fisica, risorsa umana, identita').
--
-- Indice test (1..8):
--    1. Setup: 3 operatori costruiti (identita OPERATORE attive)
--    2. fn_is_super_admin(NULL) -> false
--    3. fn_is_super_admin su auth_user senza identita -> false
--    4. Identita attiva + binding attivo -> true
--    5. Identita attiva + nessun binding -> false
--    6. Identita inattiva + binding SA attivo -> false
--    7. Binding disattivato -> false
--    8. Identita con valido_al scaduto -> false
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   La fixture PESCAVA: tre soggetti_ruolo da billing_account (clienti) per
--   due identita' CLIENTE_PORTALE, un'identita' OPERATORE esistente senza SA,
--   e il profilo SUPER_ADMIN per id cablato (9100). Quattro difetti:
--   1. su un database ricostruito (la CI) non ci sono ne' clienti ne'
--      operatori da pescare: il setup moriva al test 1;
--   2. un binding SA su un'identita' CLIENTE_PORTALE lo rifiuta il guard di
--      coerenza («binding non coerente col tipo del profilo»): il caso 6
--      non poteva nascere;
--   3. i casi 5 e 6 erano verdi per la ragione SBAGLIATA — la stessa che la
--      rev 2026-08-18 aveva gia' trovato per il caso 7: fn_is_super_admin e'
--      fail-closed sui contesti portale, e un'identita' CLIENTE_PORTALE
--      risponde false comunque, binding o no;
--   4. l'id 9100 e' vero solo perche' il seed porta l'id esplicito (lo stesso
--      difetto corretto nella madre da 20260923-10): il profilo si risolve dal
--      TIPO.
--   Ora le tre identita' sono OPERATORI costruiti, e ogni caso misura il suo
--   oggetto: il binding (4, 5, 7), la finestra (8).
--   ⭐ Il caso 6 cambia oggetto, e non per comodita': «identita' inattiva +
--   binding attivo» il modello NON lo ammette, in nessuno dei due versi —
--   l'identita' non si disattiva con un binding attivo (block_deact su
--   config.profili_accesso_bindings), e un binding non si attiva su
--   un'identita' inattiva (trgfn_child_requires_active_parent, «Padre non
--   attivo: figlio attivo non consentito»). Provati tutti e due il
--   2026-09-23. Il ramo fail-closed di fn_is_super_admin su identita'
--   inattiva resta difesa in profondita', ma uno stato irraggiungibile non
--   si collauda: si collauda la regola che lo rende irraggiungibile.
--   ⚠️ SUPERATO il 2026-09-25 (brief-db-blocco-login-per-credenziale §12.3):
--   porta e profili si sono sganciati, lo stato «inattiva + binding attivo»
--   ora esiste e il caso 6 collauda il ramo di fn_is_super_admin che lo nega.
--   ⭐ E il debito §22.4 si chiude: i builder chiudono da soli la saga del
--   soggetto (indirizzi compresi), quindi il file torna IMMEDIATE come gli
--   altri — la riga «pgtap-differiti: escluso» e' tolta.
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA: e
--   fn_is_super_admin e' STABLE, non sta mai nella stessa istruzione del
--   builder.
-- ============================================================================

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- =========================================================
-- 1) Setup: tre operatori costruiti
--    1 = super admin (casi 4, 7, 8)
--    2 = operatore semplice, nessun binding SA (caso 5)
--    3 = super admin di cui si prova a disattivare l'identita' (caso 6)
-- =========================================================
CREATE TEMP TABLE _t_op1 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('is SA 1', p_super_admin := true);

CREATE TEMP TABLE _t_op2 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('is SA 2');

CREATE TEMP TABLE _t_op3 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('is SA 3', p_super_admin := true);

CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
CREATE TEMP TABLE _t_id (idx int, identita_id bigint);

INSERT INTO _t_au SELECT 1, auth_user_id FROM _t_op1
UNION ALL          SELECT 2, auth_user_id FROM _t_op2
UNION ALL          SELECT 3, auth_user_id FROM _t_op3;

INSERT INTO _t_id SELECT 1, identita_id FROM _t_op1
UNION ALL          SELECT 2, identita_id FROM _t_op2
UNION ALL          SELECT 3, identita_id FROM _t_op3;

SELECT ok(
    (SELECT count(*) FROM anagrafiche.identita_digitali idg
       JOIN _t_id t ON t.identita_id = idg.id
      WHERE idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
        AND idg.attivo) = 3,
    '1. Setup: 3 identita OPERATORE attive costruite'
);

-- =========================================================
-- 2) fn_is_super_admin(NULL) -> false
-- =========================================================
SELECT ok(
    script.fn_is_super_admin(NULL) = false,
    '2. fn_is_super_admin(NULL) -> false (fail-closed)'
);

-- =========================================================
-- 3) auth_user senza identita -> false
-- =========================================================
SELECT ok(
    script.fn_is_super_admin(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM django.auth_user)
    ) = false,
    '3. auth_user inesistente (no identita) -> false'
);

-- =========================================================
-- 4) Identita attiva + binding SUPER_ADMIN attivo -> true
--    Il binding l'ha scritto la madre (fn_crea_operatore_v2).
-- =========================================================

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ) = true,
    '4. Identita attiva + binding SUPER_ADMIN attivo -> true'
);

-- =========================================================
-- 5) Identita attiva senza binding -> false
-- =========================================================
SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 2)
    ) = false,
    '5. Identita attiva senza binding SUPER_ADMIN -> false'
);

-- =========================================================
-- 6) Identita inattiva + binding attivo -> false.
--    ⭐ Rev 2026-09-25 (brief-db-blocco-login-per-credenziale §12.3): fino a
--    quel giorno il modello NON ammetteva questo stato (la coppia ATTIVO
--    block/require fra binding e identita') e il caso asseriva il rifiuto.
--    Con la veste OPERATORE che nasce spenta, porta e profili si sono
--    sganciati (dbops.automazione_attivo_eccezioni, decisione Tid): lo stato
--    esiste — e' l'operatore in attesa d'invito, o disattivato — e la regola
--    da collaudare e' quella che lo nega: la porta chiusa vince sul binding.
--    Il binding SA di 1 resta attivo: spegnere 3 non e' spegnere l'ultimo.
-- =========================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT identita_id FROM _t_id WHERE idx = 3);

SELECT is(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 3)
    ),
    false,
    '6. Identita inattiva + binding SUPER_ADMIN attivo -> false (la porta chiusa vince)'
);

-- Riaccesa: il caso 7 spegne il binding di 1, e 3 deve restare un SA attivo
-- perche' quello non sia l'ultimo.
UPDATE anagrafiche.identita_digitali
   SET attivo = true
 WHERE id = (SELECT identita_id FROM _t_id WHERE idx = 3);

-- =========================================================
-- 7) Binding disattivato -> false
-- =========================================================
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM config.profili_accesso pa
 WHERE pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
   AND pab.identita_digitale_id = (SELECT identita_id FROM _t_id WHERE idx = 1);

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ) = false,
    '7. Binding disattivato (attivo=false) -> false'
);

-- Riattivo per caso 8
UPDATE config.profili_accesso_bindings pab
   SET attivo = true
  FROM config.profili_accesso pa
 WHERE pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
   AND pab.identita_digitale_id = (SELECT identita_id FROM _t_id WHERE idx = 1);

-- =========================================================
-- 8) Identita fuori finestra (valido_al scaduto) -> false
-- =========================================================
-- NOTA: chk_identita_digitali_date impone valido_al >= valido_dal.
-- Per simulare finestra scaduta aggiorno ENTRAMBE le date:
-- valido_dal 30 giorni fa, valido_al ieri (coerente col CHECK).
UPDATE anagrafiche.identita_digitali
   SET valido_dal = script.fn_data_operativa() - 30,
       valido_al  = script.fn_data_operativa() - 1
 WHERE id = (SELECT identita_id FROM _t_id WHERE idx = 1);

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ) = false,
    '8. Identita con valido_al scaduto -> false'
);

SELECT * FROM finish();
ROLLBACK;
