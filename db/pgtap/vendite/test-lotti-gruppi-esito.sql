-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'esito di un gruppo dentro un lotto — dal posto dove si scrive
--       (vendite.fatturazione_lotti_gruppi) a quello dove si vede
--       (vendite.vw_dash_competenza_gruppi)
-- ChangeSet: 20260906-10 (colonne), -11 (chi le scrive), -12 (chi le mostra)
--
-- Elenco test (plan 8):
--  1) le quattro colonne dell'esito ci sono
--  2) ⭐ il vocabolario e' lo STESSO del gemello, e si legge dai vincoli
--  3) ⛔ un errore senza causa ne' frase non si scrive
--  4) ✅ marcare per chiave di gruppo: una riga, e i campi parlano
--  5) ✅ COMPLETED non lascia residui dell'errore precedente
--  6) ⛔ una commessa che non alimenta nessun gruppo del lotto non marca niente
--  7) la competenza espone le cinque colonne dell'ultimo tentativo
--  8) ⛔ e NON ha smesso di dire se il documento e' ancora da emettere
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL CASO DA CUI NASCE. Il lotto LTF-0009578 ha preso in carico tre ordini
--   e ne ha fatturati due. Il terzo e' caduto al primo passo, e non essendo mai
--   diventato fattura non aveva nessuna riga dove comparire: fuori dal lotto, e
--   dentro i documenti da emettere senza un segno. Sembrava fatturabile.
--
-- ⚠️ TUTTI I CASI SONO COSTRUITI. Il lotto e i gruppi li fabbrica la fixture:
--   nessuna asserzione si appoggia a un lotto vero, che domani puo' essere
--   archiviato o corretto. L'unica cosa presa dai dati sono i due riferimenti
--   obbligatori del lotto (tipo documento ed emittente), letti da un lotto
--   esistente perche' devono stare nel perimetro dell'operatore.
--
-- ⛔ QUELLO CHE QUESTO FILE NON PROVA, E VA DETTO: il ritrovamento del gruppo
--   PARTENDO DALLA COMMESSA quando la commessa alimenta davvero quel gruppo.
--   Costruirlo richiederebbe una commessa con le sue attivita' — una fixture
--   piu' grande della cosa da provare. Il test 6 copre il verso che si puo'
--   costruire (una commessa che non c'entra non marca niente); il verso
--   positivo si collauda sul giro vero, ed e' un debito dichiarato.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Fixture: un lotto e due gruppi, fabbricati qui
-- ============================================================
CREATE TEMP TABLE tmp_esito AS
SELECT l.tipo_doc_fiscale_id, l.emittente_soggetto_ruolo_id
  FROM vendite.fatturazione_lotti l
 ORDER BY l.id DESC
 LIMIT 1;

DO $fixture$
DECLARE
    v_lotto_id vendite.fatturazione_lotti.id%TYPE;
BEGIN
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-ESITO-GRUPPI', date_trunc('month', CURRENT_DATE)::date,
           t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id
      FROM tmp_esito t
    RETURNING id INTO v_lotto_id;

    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
    VALUES (v_lotto_id, 'PGTAP:gruppo-che-fallisce'),
           (v_lotto_id, 'PGTAP:gruppo-che-riesce');

    PERFORM set_config('pgtap.lotto', v_lotto_id::text, true);
END
$fixture$;

-- ============================================================
-- 1. Le colonne ci sono
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'fatturazione_lotti_gruppi'
        AND column_name IN ('stato_esecuzione', 'errore_codice',
                            'errore_messaggio', 'errore_quando')),
    4,
    '1. il gruppo di un lotto ha le quattro colonne dell''esito'
);

-- ============================================================
-- 2. ⭐ Stesso vocabolario del gemello — letto, non riscritto
-- ============================================================
-- ⛔ Non si scrive a mano l'elenco dei quattro valori: sarebbe una fotografia,
--   e il giorno in cui il gemello ne ammette un quinto questo test resterebbe
--   verde mentre le due colonne hanno smesso di parlare la stessa lingua.
--   Si leggono dai due vincoli e si confrontano fra loro.
SELECT is(
    (SELECT array_agg(v ORDER BY v)
       FROM (SELECT unnest(regexp_matches(pg_get_constraintdef(oid), '''([A-Z_]+)''', 'g')) AS v
               FROM pg_constraint
              WHERE conname = 'chk_lotti_gruppi_stato_esecuzione') s),
    (SELECT array_agg(v ORDER BY v)
       FROM (SELECT unnest(regexp_matches(pg_get_constraintdef(oid), '''([A-Z_]+)''', 'g')) AS v
               FROM pg_constraint
              WHERE conname = 'chk_fatturazione_lf_stato_esecuzione') s),
    '2. il gruppo e la fattura del lotto ammettono gli STESSI stati'
);

-- ============================================================
-- 3. ⛔ Un errore muto non si scrive
-- ============================================================
-- Se passasse, la riga direbbe «è andata male» e nient'altro: chi la legge non
-- saprebbe né che cosa sistemare né dove andare.
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id   => current_setting('pgtap.lotto')::bigint,
        p_stato      => 'ERRORE',
        p_gruppo_key => 'PGTAP:gruppo-che-fallisce'),
    0,
    '3. un ERRORE senza causa ne'' frase non viene scritto'
);

-- ============================================================
-- 4. ✅ Marcare per chiave di gruppo
-- ============================================================
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:gruppo-che-fallisce',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'ROOT source mancante'),
    1,
    '4. l''esito viene appeso al gruppo indicato, e a quello solo'
);

-- ============================================================
-- 5. ✅ COMPLETED non lascia residui
-- ============================================================
-- ⭐ Un gruppo che ci riprova e stavolta riesce non deve restare con addosso
--   il messaggio del tentativo di prima: sarebbe un rosso che non scade mai.
DO $riuscito$
BEGIN
    PERFORM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id   => current_setting('pgtap.lotto')::bigint,
        p_stato      => 'COMPLETED',
        p_gruppo_key => 'PGTAP:gruppo-che-fallisce');
END
$riuscito$;

SELECT ok(
    (SELECT stato_esecuzione = 'COMPLETED'
        AND errore_codice IS NULL
        AND errore_messaggio IS NULL
        AND errore_quando IS NULL
       FROM vendite.fatturazione_lotti_gruppi
      WHERE lotto_id = current_setting('pgtap.lotto')::bigint
        AND gruppo_key = 'PGTAP:gruppo-che-fallisce'),
    '5. un gruppo riuscito non conserva l''errore del tentativo precedente'
);

-- ============================================================
-- 6. ⛔ Il perimetro del lotto tiene
-- ============================================================
-- Una commessa che in questo lotto non alimenta niente non deve marcare niente:
-- ⚠️ marcare «il primo gruppo che capita» sarebbe peggio del non marcare, perché
--   attribuirebbe un errore a un documento che non c'entra.
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_commessa_id      => -1,
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'commessa che non c''entra'),
    0,
    '6. una commessa che non alimenta nessun gruppo del lotto non marca niente'
);

-- ============================================================
-- 7. La competenza porta l'esito dell'ultimo tentativo
-- ============================================================
-- ⭐ E' il pezzo che rende visibile tutto il resto: senza queste colonne
--   l'esito starebbe scritto e non lo leggerebbe nessuno.
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'vw_dash_competenza_gruppi'
        AND column_name IN ('ultimo_esito', 'ultimo_errore_codice',
                            'ultimo_errore_messaggio', 'ultimo_errore_quando',
                            'ultimo_lotto_codice')),
    5,
    '7. i documenti da emettere portano l''esito dell''ultimo tentativo'
);

-- ============================================================
-- 8. ⛔ Il segno non ha spento l'emittibilita'
-- ============================================================
-- ⛔ E' il presidio della decisione di Tid del 2026-09-06, e sta qui perche' e'
--   la cosa che qualcuno, fra sei mesi, sara' tentato di «sistemare»: togliere
--   dall'elenco i documenti che hanno un errore. Sarebbe tornare al problema di
--   partenza dall'altra parte — il documento sparirebbe di nuovo.
-- ⚠️ Il test guarda che le due colonne ci siano ancora: un CREATE OR REPLACE
--   della vista che le togliesse fallirebbe qui invece che in produzione.
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'vw_dash_competenza_gruppi'
        AND column_name IN ('stadio', 'commessa_emittibile')),
    2,
    '8. un documento con un errore resta comunque uno che dice se e'' da emettere'
);

SELECT * FROM finish();
ROLLBACK;
