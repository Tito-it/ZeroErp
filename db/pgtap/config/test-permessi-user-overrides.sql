-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tabelle override utente e scope emittente
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11): la seconda azione
--   (azione_id_2, quella del CHECK valido_dal <= valido_al) era approva_fattura, che il
--   giro ritira (attivo = false): un override su un'azione spenta lo rifiuterebbe il
--   guard ATTIVO prima del CHECK che il test cerca. Ora e' numera_fatture_lotti, attiva.
--   Attese invariate.
--       config.user_override_aree, config.user_override_oggetti,
--       config.user_override_azioni, config.user_emittenti_fiscali
--
-- Elenco test:
--  1) Riferimento django.auth_user presente
--  2) Riferimento aree_funzionali presente
--  3) Riferimento azioni_processo presente
--  4) user_override_aree: INSERT valido accettato
--  5) user_override_aree: default valido_dal = script.fn_data_operativa()
--  6) user_override_aree: UQ (user, area) duplicato bloccato
--  7) user_override_aree: CHECK valido_dal <= valido_al
--  8) user_override_oggetti: INSERT valido accettato
--  9) user_override_oggetti: UQ (user, app_label, model_name) bloccato
-- 10) user_override_oggetti: CHECK valido_dal <= valido_al
-- 11) user_override_azioni: INSERT valido accettato
-- 12) user_override_azioni: abilitata = true come inserito
-- 13) user_override_azioni: UQ (user, azione) duplicato bloccato
-- 14) user_override_azioni: CHECK valido_dal <= valido_al
-- 15) Riferimento anagrafiche.emittenti_fiscali presente
-- 16) user_emittenti_fiscali: INSERT valido accettato
-- 17) user_emittenti_fiscali: UQ (user, emittente) duplicato bloccato
-- 18) user_emittenti_fiscali: FK emittente_fiscale_id invalida bloccata
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

SELECT plan(18);

-- ============================================================
-- 0. Raccolta riferimenti
-- ============================================================

-- ⛔ L'UTENTE SI COSTRUISCE (2026-09-23). Prendere «il primo utente attivo»
--   funzionava finche' quel posto era occupato da un utente qualunque: su un
--   database ricostruito il primo attivo e' l'operatore TECNICO del contesto,
--   che una riga in `config.user_emittenti_fiscali` ce l'ha gia' — e il caso
--   16, che vuole inserirne una, moriva su `uq_user_emittenti_fiscali_auth_user`
--   invece di misurare l'INSERT. Il soggetto di questo file sono le tabelle di
--   override: l'utente giusto e' uno NUOVO, senza override e senza emittente.
CREATE TEMP TABLE tmp_uo_user AS
WITH ins AS (
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined)
    VALUES ('_pgtap_uo_' || substr(md5(clock_timestamp()::text), 1, 8),
            '!', TRUE, FALSE, FALSE, '', '', '', now())
    RETURNING id
)
SELECT id AS user_id FROM ins;

CREATE TEMP TABLE tmp_refs_uo AS
SELECT
    (SELECT user_id FROM tmp_uo_user)                   AS user_id,
    (SELECT id FROM config.aree_funzionali
     WHERE codice = 'vendite')                          AS area_vendite_id,
    (SELECT id FROM config.aree_funzionali
     WHERE codice = 'acquisti')                         AS area_acquisti_id,
    (SELECT id FROM config.azioni_processo
     WHERE permission_codename = 'genera_fatture_lotti') AS azione_id,
    (SELECT id FROM config.azioni_processo
     WHERE permission_codename = 'numera_fatture_lotti') AS azione_id_2,
    (SELECT id FROM anagrafiche.emittenti_fiscali
     WHERE attivo = true ORDER BY id LIMIT 1)            AS emittente_id;

SELECT ok(
    (SELECT user_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento django.auth_user presente'
);

SELECT ok(
    (SELECT area_vendite_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento aree_funzionali presente'
);

SELECT ok(
    (SELECT azione_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento azioni_processo presente'
);

-- ============================================================
-- 1. config.user_override_aree
-- ============================================================

-- 🔴 PULIZIA D'INGRESSO, aggiunta il 2026-08-18.
--   La fixture prende «il primo auth_user attivo» e «l'area vendite», e ci
--   inserisce un override. Ma quella coppia in sviluppo ESISTE GIA' come dato
--   vero: l'INSERT violava `uq_user_override_aree_user_area` e il file moriva
--   qui — 3 asserzioni eseguite su 18, le altre 15 mai viste.
--
--   ⚠️ La fixture non sceglieva una riga libera: sceglieva la PRIMA, e sperava.
--   Finche' nessuno aveva un override su vendite ha funzionato per caso.
--
--   ⭐ Si toglie di mezzo la riga vera invece di cercare un utente «libero»:
--   cercare il libero rende il test dipendente da quanti utenti configurati ci
--   sono, che e' la stessa fragilita' spostata di un passo. Il file e'
--   TRANSAZIONALE (BEGIN in testa, ROLLBACK in coda): l'override vero torna.
DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_uo)
   AND area_id      = (SELECT area_vendite_id FROM tmp_refs_uo);

CREATE TEMP TABLE tmp_uoa_ins AS
WITH ins AS (
    INSERT INTO config.user_override_aree
        (auth_user_id, area_id, livello, meta)
    SELECT r.user_id, r.area_vendite_id,
           'TUTTO'::config.livello_accesso,
           jsonb_build_object('test_scope', 'pgtap_permessi_overrides')
    FROM tmp_refs_uo r
    RETURNING id, valido_dal
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_uoa_ins) IS NOT NULL,
    'user_override_aree: INSERT valido accettato'
);

SELECT is(
    (SELECT valido_dal FROM tmp_uoa_ins),
    script.fn_data_operativa(),
    'user_override_aree: default valido_dal = script.fn_data_operativa()'
);

-- UQ (auth_user_id, area_id)
-- 🔴 SQLSTATE AGGIORNATO il 2026-08-18: 23514 -> 22000.
--   Queste tre asserzioni aspettavano una CHECK violation. Dalla migrazione a
--   `daterange` nativo (2026-04-12, 18 tabelle) la validita' non e' piu' due
--   colonne con un CHECK sopra: e' un RANGE, e un intervallo rovesciato lo
--   rifiuta il COSTRUTTORE DEL TIPO — `22000`, prima che qualunque CHECK possa
--   guardarlo.
--   ⭐ La garanzia non si e' indebolita, si e' spostata piu' in basso: dal
--   vincolo di tabella al tipo della colonna. L'etichetta ora dice questo,
--   perche' «CHECK» mandava a cercare un vincolo che non c'e' piu'.
--   ⭐ 2026-09-23 (brief-db-guard-date-validita): a rifiutare e' ora il
--   GUARD COMUNE delle date (script.trgfn_guard_date_validita, montato
--   dall'automazione DATE_VALIDITA). E' un BEFORE ROW, e i BEFORE girano
--   prima del calcolo della colonna generata: l'operatore legge
--   E_DATA_AL_MINORE_DAL invece della frase tecnica del daterange. Il
--   daterange resta sotto, come il CHECK: sono l'ultima difesa.
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_aree
              (auth_user_id, area_id, livello)
          VALUES (%s, %s, 'LETTURA'::config.livello_accesso)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT area_vendite_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_override_aree: UQ (user, area) duplicato bloccato'
);

-- CHECK valido_dal <= valido_al (usa area_acquisti_id per evitare UQ)
SELECT throws_like(
    format(
        $$INSERT INTO config.user_override_aree
              (auth_user_id, area_id, livello, valido_dal, valido_al)
          VALUES (%s, %s, 'LETTURA'::config.livello_accesso,
                  '2026-03-01'::date, '2026-02-01'::date)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT area_acquisti_id FROM tmp_refs_uo)
    ),
    '%è inferiore alla data dal%',
    'user_override_aree: validita rovesciata, parla il guard comune delle date (E_DATA_AL_MINORE_DAL)'
);

-- ============================================================
-- 2. config.user_override_oggetti
-- ============================================================

CREATE TEMP TABLE tmp_uoo_ins AS
WITH ins AS (
    INSERT INTO config.user_override_oggetti
        (auth_user_id, app_label, model_name, livello, meta)
    SELECT r.user_id, 'vendite', 'fattura',
           'LETTURA'::config.livello_accesso,
           jsonb_build_object('test_scope', 'pgtap_permessi_overrides')
    FROM tmp_refs_uo r
    RETURNING id
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_uoo_ins) IS NOT NULL,
    'user_override_oggetti: INSERT valido accettato'
);

-- UQ (auth_user_id, app_label, model_name)
-- 🔴 SQLSTATE AGGIORNATO il 2026-08-18: 23514 -> 22000.
--   Queste tre asserzioni aspettavano una CHECK violation. Dalla migrazione a
--   `daterange` nativo (2026-04-12, 18 tabelle) la validita' non e' piu' due
--   colonne con un CHECK sopra: e' un RANGE, e un intervallo rovesciato lo
--   rifiuta il COSTRUTTORE DEL TIPO — `22000`, prima che qualunque CHECK possa
--   guardarlo.
--   ⭐ La garanzia non si e' indebolita, si e' spostata piu' in basso: dal
--   vincolo di tabella al tipo della colonna. L'etichetta ora dice questo,
--   perche' «CHECK» mandava a cercare un vincolo che non c'e' piu'.
--   ⭐ 2026-09-23: ora a parlare e' il guard comune delle date (vedi la nota
--   sulla prima delle tre asserzioni).
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_oggetti
              (auth_user_id, app_label, model_name, livello)
          VALUES (%s, 'vendite', 'fattura', 'BLOCCATO'::config.livello_accesso)$$,
        (SELECT user_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_override_oggetti: UQ (user, app_label, model_name) duplicato bloccato'
);

-- CHECK valido_dal <= valido_al (usa model_name diverso per evitare UQ)
-- ⚠️ Un oggetto A CATALOGO ('preventivo'; fino al 2026-09-28 'lotto', che non c'e'):
--   con 'lotto' il test passava solo perche' il guard BEFORE ROW delle date scatta
--   prima della FK composita del catalogo (D-4) — verde per l'ordine dei controlli.
SELECT throws_like(
    format(
        $$INSERT INTO config.user_override_oggetti
              (auth_user_id, app_label, model_name, livello, valido_dal, valido_al)
          VALUES (%s, 'vendite', 'preventivo',
                  'LETTURA'::config.livello_accesso,
                  '2026-03-01'::date, '2026-02-01'::date)$$,
        (SELECT user_id FROM tmp_refs_uo)
    ),
    '%è inferiore alla data dal%',
    'user_override_oggetti: validita rovesciata, parla il guard comune delle date (E_DATA_AL_MINORE_DAL)'
);

-- ============================================================
-- 3. config.user_override_azioni
-- ============================================================

CREATE TEMP TABLE tmp_uoaz_ins AS
WITH ins AS (
    INSERT INTO config.user_override_azioni
        (auth_user_id, azione_id, abilitata, meta)
    SELECT r.user_id, r.azione_id, true,
           jsonb_build_object('test_scope', 'pgtap_permessi_overrides')
    FROM tmp_refs_uo r
    RETURNING id, abilitata
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_uoaz_ins) IS NOT NULL,
    'user_override_azioni: INSERT valido accettato'
);

SELECT is(
    (SELECT abilitata FROM tmp_uoaz_ins),
    true,
    'user_override_azioni: abilitata = true come inserito'
);

-- UQ (auth_user_id, azione_id)
-- 🔴 SQLSTATE AGGIORNATO il 2026-08-18: 23514 -> 22000.
--   Queste tre asserzioni aspettavano una CHECK violation. Dalla migrazione a
--   `daterange` nativo (2026-04-12, 18 tabelle) la validita' non e' piu' due
--   colonne con un CHECK sopra: e' un RANGE, e un intervallo rovesciato lo
--   rifiuta il COSTRUTTORE DEL TIPO — `22000`, prima che qualunque CHECK possa
--   guardarlo.
--   ⭐ La garanzia non si e' indebolita, si e' spostata piu' in basso: dal
--   vincolo di tabella al tipo della colonna. L'etichetta ora dice questo,
--   perche' «CHECK» mandava a cercare un vincolo che non c'e' piu'.
--   ⭐ 2026-09-23: ora a parlare e' il guard comune delle date (vedi la nota
--   sulla prima delle tre asserzioni).
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_azioni
              (auth_user_id, azione_id, abilitata)
          VALUES (%s, %s, false)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT azione_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_override_azioni: UQ (user, azione) duplicato bloccato'
);

-- CHECK valido_dal <= valido_al (usa azione_id_2 per evitare UQ)
SELECT throws_like(
    format(
        $$INSERT INTO config.user_override_azioni
              (auth_user_id, azione_id, abilitata, valido_dal, valido_al)
          VALUES (%s, %s, true,
                  '2026-03-01'::date, '2026-02-01'::date)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT azione_id_2 FROM tmp_refs_uo)
    ),
    '%è inferiore alla data dal%',
    'user_override_azioni: validita rovesciata, parla il guard comune delle date (E_DATA_AL_MINORE_DAL)'
);

-- ============================================================
-- 4. config.user_emittenti_fiscali
-- ============================================================

SELECT ok(
    (SELECT emittente_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento anagrafiche.emittenti_fiscali presente'
);

SELECT lives_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id, meta)
          VALUES (%s, %s,
                  '{"test_scope": "pgtap_permessi_overrides"}'::jsonb)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT emittente_id FROM tmp_refs_uo)
    ),
    'user_emittenti_fiscali: INSERT valido accettato'
);

-- UQ (auth_user_id, emittente_fiscale_id)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id)
          VALUES (%s, %s)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT emittente_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_emittenti_fiscali: UQ (user, emittente) duplicato bloccato'
);

-- FK emittente_fiscale_id invalida
-- 🔴 SBLOCCATO il 2026-08-18. Questa asserzione non poteva riuscire: il test 16
--   ha appena inserito la riga di QUESTO utente, e `uq_user_emittenti_fiscali_auth_user`
--   e' unica sul solo `auth_user_id` — quindi scattava 23505 (duplicato) PRIMA
--   che la FK potesse dire la sua, e il test aspettava 23503.
--   ⚠️ Non e' un difetto del vincolo: e' l'ordine in cui i vincoli parlano. Per
--   interrogare la FK bisogna prima liberare la chiave.
--   Il DELETE passa dall'override GUC perche' la tabella ha un guard sul delete
--   (trgfn_user_emittenti_fiscali_guard_delete) — la stessa porta che usa
--   script.fn_change_user_emittenti_scope.
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_uo);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

SELECT throws_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id)
          VALUES (%s, 999999)$$,
        (SELECT user_id FROM tmp_refs_uo)
    ),
    '23503',
    NULL,
    'user_emittenti_fiscali: FK emittente_fiscale_id invalida bloccata'
);

SELECT * FROM finish();

ROLLBACK;
