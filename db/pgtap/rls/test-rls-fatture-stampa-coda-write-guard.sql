-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce DUE aziende con una fattura
--   ciascuna, e una fattura pretende un billing account. Come `zeroerp_app`
--   l'INSERT del BA muore al RETURNING quando l'emittente di chi agisce non e'
--   quello di default (la policy di lettura risolve il BA non ancora mappato
--   sul default; il legame lo scrive un trigger AFTER). Da owner la RLS si
--   accende con `FORCE ROW LEVEL SECURITY` locale alla transazione: il test 1
--   continua a pretendere che la sessione la SUBISCA, e con il FORCE la
--   subisce — e il guard, che esce per chi la bypasserebbe, resta in servizio.
-- pgTAP test per Zero ERP
--
-- Test: il guard di scrittura sulla coda di stampa (DB-6 / R-10)
-- Brief: brief-db-processi-automatici-residui-be.md, risposta DB (R-D)
--
-- Elenco test (plan 6):
--  1) ⭐ IL PRESUPPOSTO: questa sessione SUBISCE la row level security
--  2) il guard c'e', ed e' montato sul modo `fattura` su `sorgente_id`
--  3) ⚠️ la FK che rende lecito quel modo esiste ancora
--  4) ✅ accodare la stampa di una PROPRIA fattura passa
--  5) ⛔ accodare la stampa di una fattura ALTRUI si ferma, e SPIEGA
--  6) ⭐ il presidio livello 2 non ha ALLARMI
--
-- Scopo:
--  - provare il caso che la policy da sola non copre bene: sull'INSERT il
--    `WITH CHECK` si valuta DOPO i trigger `BEFORE ROW`, quindi senza guard
--    l'operatore riceverebbe «new row violates row-level security policy» —
--    vero e inservibile. Il test 5 chiede il messaggio, non solo il rifiuto;
--  - ⚠️ fissare col test 3 l'ASSUNTO su cui il modo `fattura` regge. La tabella
--    porta `sorgente_tipo_id` e `sorgente_id`, cioe' la forma delle sorgenti
--    polimorfe: quello che la rende non-polimorfa e' una FK dura. Se cadesse,
--    il guard punterebbe alla tabella sbagliata e la policy pure — e nessuno
--    dei due lo direbbe da solo.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file cercava una fattura ESISTENTE nel proprio perimetro, un secondo
--   emittente e un super admin, e senza di loro SALTAVA i test 4 e 5 — su un
--   database ricostruito dai changelog moriva nella fixture. Ora: due aziende
--   con `dbops.fn_pgtap_crea_emittente_operatore()`, un cliente ciascuna con
--   `dbops.fn_pgtap_crea_cliente_ba(..., azienda)`, il registro
--   (`script.fn_pgtap_registro_fattura`) e una fattura ciascuna — tutto PRIMA
--   di aprire il contesto, come nei gemelli `*-satelliti.sql`. Niente `skip`.
--   ⚠️ Fino a quel giorno il file girava come `zeroerp_app`: il costo del
--   cambio e' scritto nel marcatore.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- Fixture: il mondo, POI il contesto
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⛔ Il BA va LEGATO al proprio emittente (terzo parametro): senza, la fattura
--   ricadrebbe sull'emittente di DEFAULT dell'installazione.
CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.soggetto_ruolo_id AS emittente_sr_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'RLS guard stampa ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⭐ Il registro lo da' l'helper, che ne CREA uno coerente se quell'emittente
--   non ne ha: senza, il guard registro-emittente rifiuterebbe la fattura per
--   un motivo che non c'entra col test.
CREATE TEMP TABLE _fatture AS
WITH f AS (
    INSERT INTO vendite.fatture
        (registro_id, emittente_soggetto_ruolo_id, billing_account_id, meta)
    SELECT script.fn_pgtap_registro_fattura(c.emittente_sr_id),
           c.emittente_sr_id, c.billing_account_id,
           jsonb_build_object('test_scope', 'pgtap_guard_stampa_coda')
      FROM _clienti c
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT c.lato, f.id AS fattura_id
  FROM f JOIN _clienti c ON c.emittente_sr_id = f.emittente_soggetto_ruolo_id;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'MIA'));
    PERFORM set_config('pgtap.fattura_mia',
        (SELECT fattura_id FROM _fatture WHERE lato = 'MIA')::text, true);
    PERFORM set_config('pgtap.fattura_altrui',
        (SELECT fattura_id FROM _fatture WHERE lato = 'ALTRUI')::text, true);
END $ctx$;

-- Da owner la policy non morde: si accende per la durata della transazione.
ALTER TABLE vendite.fatture_stampa_coda FORCE ROW LEVEL SECURITY;

SELECT plan(6);

-- ============================================================
-- 1..3. Il presupposto e la postura
-- ============================================================
SELECT ok(
    row_security_active('vendite.fatture_stampa_coda'::regclass),
    '1. questa sessione SUBISCE la RLS: i test 4 e 5 hanno senso'
);

-- ⚠️ Non basta «c''e'' un guard»: un guard montato col modo sbagliato
--   risolverebbe sempre NULL, cioe' sarebbe spento pur sembrando acceso.
SELECT is(
    (SELECT encode(t.tgargs, 'escape')
       FROM pg_trigger t JOIN pg_proc f ON f.oid = t.tgfoid
      WHERE t.tgrelid = 'vendite.fatture_stampa_coda'::regclass
        AND NOT t.tgisinternal
        AND f.proname = 'trgfn_guard_emittente_scope'),
    'fattura\000sorgente_id\000',
    '2. il guard e'' montato sul modo fattura, su sorgente_id'
);

-- ⭐ QUESTO TEST FISSA UN ASSUNTO, ed e' il motivo per cui esiste.
--   `sorgente_tipo_id` + `sorgente_id` sono la forma delle sorgenti polimorfe,
--   dove il portante puo' essere l'uid e puntare `sorgente_id` a UNA tabella
--   sarebbe sbagliato. Qui e' lecito solo perche' una FK dura lo fissa alle
--   fatture. ⛔ Se cadesse, guard e policy assumerebbero entrambi una cosa
--   falsa, e nessuno dei due se ne accorgerebbe.
SELECT isnt_empty(
    $$SELECT 1 FROM pg_constraint
       WHERE conname = 'fk_fatture_stampa_coda_fattura'
         AND conrelid = 'vendite.fatture_stampa_coda'::regclass$$,
    '3. la FK che fissa sorgente_id alle fatture esiste ancora'
);


-- ============================================================
-- 4. ✅ Cio' che deve passare
-- ============================================================
-- Prima del rifiuto va provato il consenso: un guard che nega tutto passerebbe
-- il test 5 senza essere corretto.
SELECT lives_ok(
    format($$INSERT INTO vendite.fatture_stampa_coda
                 (sorgente_tipo_id, sorgente_id, stato)
             SELECT (SELECT id FROM config.sorgenti
                      WHERE codice_interno = 'FATTURA'),
                    %s, 'PENDING'$$,
           current_setting('pgtap.fattura_mia')),
    '4. accodare la stampa di una PROPRIA fattura passa'
);

-- ============================================================
-- 5. ⛔ Cio' che deve fermarsi, e come lo dice
-- ============================================================
-- ⭐ E' il caso per cui il guard esiste: sull'INSERT la policy arriverebbe
--   dopo, con un messaggio che non dice niente. Il guard scatta BEFORE e nomina
--   utente, emittente e tabella.
-- ⚠️ Non si usa `throws_ok` col solo SQLSTATE: tutti gli errori applicativi
--   passano da `fn_log_and_raise_error` e sono `P0001`, quindi sarebbe verde
--   anche se a fermare la riga fosse un guard qualunque — o la policy. Si
--   chiede lo stato E che il messaggio sia quello dello scope.
DO $prova$
DECLARE
    v_esito text := 'non-sollevato';
BEGIN
    BEGIN
        INSERT INTO vendite.fatture_stampa_coda
            (sorgente_tipo_id, sorgente_id, stato)
        SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA'),
               current_setting('pgtap.fattura_altrui')::bigint,
               'PENDING';
    EXCEPTION WHEN OTHERS THEN
        v_esito := SQLSTATE || '|' ||
                   CASE WHEN SQLERRM ILIKE '%scope emittente fiscale%'
                        THEN 'scope' ELSE 'altro:' || left(SQLERRM, 60) END;
    END;

    PERFORM set_config('pgtap.esito5', v_esito, true);
END
$prova$;

SELECT is(
    current_setting('pgtap.esito5', true),
    'P0001|scope',
    '5. accodare la stampa di una fattura ALTRUI si ferma, e SPIEGA'
);

-- ============================================================
-- 6. ⭐ Il presidio livello 2 non ha ALLARMI
-- ============================================================
-- ⚠️ QUESTA ASSERZIONE E' CAMBIATA, ed e' il caso di dire perche'.
--   Nata il 2026-09-05 come «la vista e' VUOTA», ed era vera: col guard sulla
--   coda di stampa il livello 2 era arrivato a zero. Poche ore dopo il changeSet
--   20260905-18 ha dato a `config.email_outbox` la colonna emittente ma NON la
--   policy che la applica — prima va deciso chi puo' leggere le email di ambito
--   SISTEMA (reset password), che non appartengono a nessun emittente.
--   ⇒ La vista ha di nuovo una riga, e la riga e' GIUSTA: un debito con un
--     nome, dichiarato in `dbops.processi_bersagli.debito_dichiarato`.
--
-- ⛔ «Vuota» non e' piu' l'invariante, e insistere l'avrebbe resa una bugia: il
--   rosso non avrebbe segnalato un difetto ma una decisione presa apposta.
--   ⭐ Cio' che resta vero — e che questo cantiere ha davvero ottenuto — e' che
--   non c'e' nessuna riga NON dichiarata: nessun ALLARME.
--
-- ⚠️ E si dichiara il rischio: dichiarare un debito ZITTISCE questo test. E' il
--   motivo per cui il censimento dei debiti non sta qui ma in
--   db/pgtap/dbops/test-presidi-debito-dichiarato.sql, dove il test 6 prova che
--   un bersaglio NUOVO e rotto esce NON_DICHIARATO — cioe' che il flag e' un
--   gesto e non l'impostazione di fabbrica.
SELECT is_empty(
    $$SELECT processo_codice, nome_tabella
        FROM dbops.vw_processi_dominio_senza_difesa
       WHERE stato = 'NON_DICHIARATO'$$,
    '6. nessun bersaglio di dominio scoperto che non sia DICHIARATO'
);

ALTER TABLE vendite.fatture_stampa_coda NO FORCE ROW LEVEL SECURITY;

SELECT * FROM finish();

ROLLBACK;
