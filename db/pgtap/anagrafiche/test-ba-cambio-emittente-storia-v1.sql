-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un billing account con storia non cambia emittente fiscale
-- Oggetti:
--   anagrafiche.fn_get_storia_emittente_ba()            (20260831-17)
--   anagrafiche.fn_ba_ha_storia_emittente()             (20260831-17)
--   anagrafiche.fn_guard_ba_cambio_emittente()          (20260826-47)
--   anagrafiche.trgfn_efba_guard_storia_emittente()     (20260826-49)
--   script.fn_check_ba_cambio_emittente()               (20260827-01)
--   anagrafiche.fn_guard_ba_cambio_emittente() rev N2   (20260827-02)
--   script.fn_check_ba_cambio_emittente() rev C2-17     (20260831-19)
--
-- Elenco test (plan 14):
--  1) Precondizioni: mondo costruito + secondo emittente distinto
--  2) BA appena nato: nessuna storia -> nessuna riga
--  3) BA appena nato: il cambio di emittente PASSA        [la finestra di correzione]
--  4) Dopo una commessa: la storia conta 1 documento SOTTO LA FAMIGLIA COMMESSA
--  5) Con storia: il cambio di emittente -> P0001         [il cancello]
--  6) ... e la frase nomina la SPECIE del documento che blocca
--  7) Emittente che non cambia davvero: PASSA             [manutenzione ordinaria]
--  8) Il trigger e' montato sui tre movimenti (INSERT/UPDATE/DELETE)
--  9) check: senza storia -> [] (la stessa risposta del guard, dalla riga)
-- 10) check: emittente che NON cambia davvero -> [], anche CON storia
-- 11) check: cambia + storia -> un motivo, col codice giusto
-- 12) il messaggio nomina l'emittente per CODICE, non per soggetto_ruolo_id
-- 13) ⭐ STRUTTURALE: la madre CHIAMA la check e non contiene piu' il predicato
-- 14) ⛔ la RIGA DEL GESTORE GLOBALE non e' togliibile, e non «dipende»
--
-- Scopo:
--  - il caso si FABBRICA (billing account nuovo, poi una commessa sopra):
--    un test che cerca fra i dati esistenti passa a vuoto in CI, dove il
--    database e' ricostruito da zero;
--  - ⭐ il 3) e il 5) sono la stessa chiamata sullo stesso cliente, prima e
--    dopo che gli sia passato del lavoro: e' la forma «b» decisa in D-1 —
--    libero finche' non c'e' storia, vietato dopo — e provarli in coppia e'
--    l'unico modo di dimostrare che la finestra di correzione esiste davvero
--    e non e' solo dichiarata;
--  - ⚠️ il guard si chiama DIRETTAMENTE, con `prima`/`dopo` espliciti: e' la
--    forma deterministica. Il percorso via trigger su due emittenti diversi
--    richiederebbe un secondo emittente fiscale nello scope dell'operatore,
--    che questa fixture non fabbrica; il montaggio del trigger e' presidiato
--    strutturalmente dall'8).
--
-- Piano: brief-db-billing-account-cambio-emittente, M5 (§6.5)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- =========================================================
-- 0) Il mondo si COSTRUISCE: un cliente nuovo, quindi un BA senza storia
-- =========================================================
-- ⛔ 2026-09-23: il file PESCAVA soggetto, ruolo e utility da «un billing
--   account esistente». Su un database ricostruito dai changelog i billing
--   account sono zero, e la fixture moriva sul NOT NULL di
--   `istanze_utilities.soggetto_id` — copertura zero, non parziale.
-- ⭐ Il cliente del mondo e' gia' il caso del test: un BA appena nato, legato
--   dal trigger z90 all'emittente di chi agisce. Il contesto e' aperto dalla
--   riga sopra, quindi il BB riusa l'azienda dell'operatore (ramo B).
CREATE TEMP TABLE tmp_mondo_ba_storia AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('BA storia');

-- ⭐ L'«altro» emittente e' un emittente VERO, costruito: prima era «un
--   soggetto_ruolo qualunque diverso da quello dell'operatore», cioe' un
--   numero che il guard riceveva come emittente senza esserlo.
CREATE TEMP TABLE tmp_refs_ba_storia AS
SELECT m.utility_id,
       m.emittente_soggetto_ruolo_id                 AS emittente_sr_ok,
       (SELECT e.soggetto_ruolo_id
          FROM dbops.fn_pgtap_crea_emittente() e)    AS emittente_sr_altro
  FROM tmp_mondo_ba_storia m;

SELECT ok(
    (SELECT utility_id IS NOT NULL
        AND emittente_sr_ok IS NOT NULL
        AND emittente_sr_altro IS NOT NULL
        AND emittente_sr_altro <> emittente_sr_ok
     FROM tmp_refs_ba_storia),
    'Precondizioni: il mondo costruito e un secondo emittente distinto'
);

CREATE TEMP TABLE tmp_ids_ba_storia AS
SELECT m.billing_account_id FROM tmp_mondo_ba_storia m;

-- =========================================================
-- 2) BA appena nato: nessuna storia
-- =========================================================
-- ⭐ 2026-08-31: la funzione non torna piu' due colonne fisse ma UNA RIGA PER
--   FAMIGLIA con almeno un documento numerato. «Nessuna storia» e' quindi
--   «nessuna riga», e non «(0,0)»: gli zeri non escono, cosi' chi compone la
--   frase del rifiuto non deve filtrarli.
SELECT is(
    (SELECT count(*)
       FROM tmp_ids_ba_storia t,
            LATERAL anagrafiche.fn_get_storia_emittente_ba(t.billing_account_id) s),
    0::bigint,
    'Un billing account appena nato non ha nessuna storia: nessuna famiglia risponde'
);

-- =========================================================
-- 3) ⭐ La FINESTRA DI CORREZIONE: senza storia il cambio passa
-- =========================================================
SELECT lives_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_altro FROM tmp_refs_ba_storia)
    ),
    'Forma b: senza storia il billing account puo'' ancora cambiare emittente'
);

-- =========================================================
-- 9) La CHECK dice la stessa cosa, e lo dice alla RIGA
-- =========================================================
-- ⭐ Non e' un doppione del 3): il 3) prova che la madre non solleva, questo
--   prova che il pulsante resta ACCESO. Sono le due estremita' dello stesso
--   predicato, ed e' il punto del §12.5.2.
SELECT is(
    (SELECT script.fn_check_ba_cambio_emittente(
                t.billing_account_id, r.emittente_sr_ok, r.emittente_sr_altro)
       FROM tmp_ids_ba_storia t, tmp_refs_ba_storia r),
    '[]'::jsonb,
    'check: senza storia nessun motivo — il cestino di riga resta acceso'
);

-- =========================================================
-- 4) Gli si attacca del lavoro: ora la storia c'e'
-- =========================================================
INSERT INTO vendite.commesse (codice, billing_account_id, utility_id)
SELECT 'TST-BA-STORIA-CMM-01', t.billing_account_id, r.utility_id
  FROM tmp_ids_ba_storia t, tmp_refs_ba_storia r;

-- ⚠️ La riga si cerca per FAMIGLIA e non per posizione: l'ordine e' quello del
--   catalogo, e un test che pescasse «la prima riga» misurerebbe l'ordinamento
--   invece del conteggio.
SELECT is(
    (SELECT s.n_documenti
       FROM tmp_ids_ba_storia t,
            LATERAL anagrafiche.fn_get_storia_emittente_ba(t.billing_account_id) s
      WHERE s.famiglia_documento = 'COMMESSA'),
    1::bigint,
    'La commessa appena creata entra nella storia, sotto la sua famiglia'
);

-- =========================================================
-- 5/6) ⛔ IL CANCELLO: con storia il cambio si blocca, e lo dice
-- =========================================================
SELECT throws_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_altro FROM tmp_refs_ba_storia)
    ),
    'P0001',
    NULL,
    'Con una commessa a carico, il cambio di emittente e'' respinto'
);

-- ⚠️ La frase E' la posta in gioco: deve dire QUALE specie di documento blocca
--   e quanti sono, altrimenti manda a cercare a mano cosa c'e' sotto.
-- ⛔ Dal 2026-08-31 le famiglie sono cinque: una frase che ne nominasse due —
--   «3 fatture e 1 commesse» — sarebbe PEGGIO di una che non ne nomina
--   nessuna, perche' manderebbe a cercare fatture a un cliente bloccato da un
--   DDT. Le parole vengono da vendite.famiglie_documento.descrizione.
SELECT throws_like(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_altro FROM tmp_refs_ba_storia)
    ),
    '%(Commessa: 1)%',
    'La frase nomina la specie del documento che blocca, con le parole del catalogo'
);

-- =========================================================
-- 7) Manutenzione ordinaria: se l'emittente non cambia, non si blocca
-- =========================================================
-- E' la riga che tiene aperta la cancellazione di un mapping specifico quando
-- il gestore globale punta allo STESSO emittente: li' non si sposta nessun
-- documento, e bloccare sarebbe un falso positivo.
SELECT lives_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia)
    ),
    'Un emittente che non cambia davvero non blocca niente, anche con storia'
);

-- =========================================================
-- 8) Il trigger e' montato, e sui TRE movimenti
-- =========================================================
-- ⚠️ Presidio strutturale: la CANCELLAZIONE e' il movimento che si dimentica,
--   ed e' proprio quello con cui il backend «sposta» un billing account
--   (DELETE + INSERT: non esiste nessun UPDATE sul mapping).
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'anagrafiche'
        AND c.relname = 'emittenti_fiscali_billing_account'
        AND t.tgname  = 'trg_emittenti_fiscali_ba_a10_guard_storia_emittente_ins_upd_dlt'
        -- 2 = BEFORE, 4 = INSERT, 8 = DELETE, 16 = UPDATE  (pg_trigger.tgtype)
        AND (t.tgtype & 2)  = 2
        AND (t.tgtype & 4)  = 4
        AND (t.tgtype & 8)  = 8
        AND (t.tgtype & 16) = 16),
    1,
    'Il guard e'' montato BEFORE su INSERT, UPDATE e DELETE'
);

-- =========================================================
-- 10) ⛔ LA META' DEL PREDICATO CHE SI DIMENTICA
-- =========================================================
-- Se l'emittente non cambia DAVVERO non c'e' niente da presidiare, e questo
-- vale ANCHE su un billing account che ha storia: togliere un mapping quando
-- il gestore globale punta allo stesso emittente non sposta nessun documento.
-- ⚠️ Senza questa riga il cestino si spegnerebbe su quasi tutte le righe di
--   un'installazione a un solo emittente, tutte a torto.
SELECT is(
    (SELECT script.fn_check_ba_cambio_emittente(
                t.billing_account_id, r.emittente_sr_ok, r.emittente_sr_ok)
       FROM tmp_ids_ba_storia t, tmp_refs_ba_storia r),
    '[]'::jsonb,
    'check: emittente che non cambia davvero -> nessun motivo, anche con storia'
);

-- =========================================================
-- 11) Cambia + storia: un motivo, e il codice e' quello a catalogo
-- =========================================================
SELECT is(
    (SELECT script.fn_check_ba_cambio_emittente(
                t.billing_account_id, r.emittente_sr_ok, r.emittente_sr_altro) -> 0 ->> 'codice'
       FROM tmp_ids_ba_storia t, tmp_refs_ba_storia r),
    'E_BA_EMITTENTE_CON_STORIA',
    'check: con storia il primo motivo nomina il codice gia'' a catalogo'
);

-- =========================================================
-- 12) La frase nomina l'emittente per CODICE
-- =========================================================
-- ⭐ Il canale VARIADIC compone quello che legge una PERSONA. Il messaggio
--   diceva «…con l'emittente 72» — un soggetto_ruolo_id in mezzo a una frase
--   italiana, nella stessa frase in cui il cliente era gia' nominato bene.
-- ⚠️ 2026-08-31: i valori sono passati da QUATTRO a TRE (cliente, emittente,
--   elenco), perche' i due conteggi fissi sono diventati un elenco derivato dal
--   catalogo. L'emittente e' quindi in posizione 1, non 3.
SELECT is(
    (SELECT (script.fn_check_ba_cambio_emittente(
                t.billing_account_id, r.emittente_sr_ok, r.emittente_sr_altro)
             -> 0 -> 'valori' ->> 1)
       FROM tmp_ids_ba_storia t, tmp_refs_ba_storia r),
    -- ⚠️ `::text` obbligatorio, e non e' cosmesi: `is()` e'
    --   `is(anyelement, anyelement, text)`, quindi i due lati devono
    --   RISOLVERE ALLO STESSO TIPO. A sinistra `->> 3` da' `text`, qui
    --   `emittenti_fiscali.codice` e' `character varying`: senza il cast
    --   PostgreSQL non trova nessuna funzione e il file muore a meta' corsa.
    --   ℹ️ Le altre `is()` di questo file reggono perche' confrontano con un
    --   LETTERALE, che e' `unknown` e viene coercito all'anyelement: il difetto
    --   compare solo quando il secondo lato e' una COLONNA gia' tipata.
    (SELECT ef.codice::text FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.soggetto_ruolo_id = (SELECT emittente_sr_ok FROM tmp_refs_ba_storia)),
    'il messaggio nomina l''emittente per CODICE, non per soggetto_ruolo_id'
);

-- =========================================================
-- 13) ⭐ IL PRESIDIO CHE CONTA, ed e' STRUTTURALE
-- =========================================================
-- Il §12.5.2 lo dice in una riga: il presidio da scrivere NON e' «gli esiti
-- coincidono» — quello proverebbe che oggi vanno d'accordo — ma «la madre non
-- contiene piu' il predicato». Cosi' si prova che non POSSONO divergere.
-- ⇒ Se un giorno qualcuno ricopiasse il conteggio dentro la madre «per non
--   fare una chiamata in piu'», questa riga diventa rossa. E' l'unico posto in
--   cui quel passo indietro si vedrebbe.
SELECT ok(
    pg_get_functiondef('anagrafiche.fn_guard_ba_cambio_emittente(bigint,bigint,bigint)'::regprocedure)
        LIKE '%fn_check_ba_cambio_emittente%'
    AND pg_get_functiondef('anagrafiche.fn_guard_ba_cambio_emittente(bigint,bigint,bigint)'::regprocedure)
        NOT LIKE '%fn_get_storia_emittente_ba%',
    'la madre CHIAMA la check e non contiene piu'' il predicato (§12.5.2)'
);

-- =========================================================
-- 14) ⛔ LA RIGA DEL GESTORE GLOBALE, e la risposta e' INCONDIZIONATA
-- =========================================================
-- Prima la check cadeva su «senza billing account non e' il mio caso» e
-- rispondeva [] — cioe' lasciava il cestino ACCESO sulla riga che il
-- repository tiene IN TESTA (ORDER BY is_default DESC).
-- ⛔ Quella riga non si toglie MAI: il singleton pretende esattamente un
--   default. La risposta NON dipende dalla storia, ed e' il motivo per cui non
--   si e' scritta la gemella del guard raggio N — avrebbe dato un motivo
--   condizionale dove la risposta e' secca.
-- ⚠️ Si passa un `dopo` NULL, che e' esattamente cio' che resterebbe.
SELECT is(
    (SELECT script.fn_check_ba_cambio_emittente(
                NULL::bigint, r.emittente_sr_ok, NULL::bigint) -> 0 ->> 'reason'
       FROM tmp_refs_ba_storia r),
    'DEFAULT_SINGLETON',
    'la riga del gestore globale non e'' togliibile, e il motivo non e'' la storia'
);

SELECT * FROM finish();
ROLLBACK;
