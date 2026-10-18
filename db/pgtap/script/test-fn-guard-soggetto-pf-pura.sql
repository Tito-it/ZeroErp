-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_guard_soggetto_pf_pura
-- Riferimento: §4.2 WIP multi-face-auth, funzione riusabile estratta
-- dal trigger trgfn_risorse_umane_auth_user_guard_persona_fisica.
--
-- Indice test (1..8):
--    1. Precondizione: comune nascita disponibile per fn_crea_soggetto_pf
--    2. Setup: creato soggetto PF pura (CF valorizzato, P.IVA NULL)
--    3. Guard NULL: p_soggetto_id NULL -> throws E_PARAMETRO_INVALIDO
--    4. Guard soggetto inesistente: UUID random -> throws E_SOGGETTO_NOT_FOUND
--    5. Guard PF pura: soggetto valido -> ritorna soggetto_id (no exception)
--    6. Setup: aggiungi P.IVA al soggetto
--    7. Guard con P.IVA: throws E_AUTH_USER_SOGGETTO_CON_PIVA
--    8. La fixture e' COMMITTABILE: chiusi i tre guard differiti di soggetti
--
-- Nota: il caso "senza CF" NON e' testabile su un soggetto PR reale
-- perche' il trigger trgfn_soggetti_guard_cf_piva_obbligatori garantisce
-- CF NOT NULL per tipo PR (invariante di modello). La funzione ha il
-- ramo difensivo ma non e' raggiungibile con dati validi.
--
-- BEGIN; + rollback a fine file.
-- ------------------------------------------------------------

BEGIN;

-- ⭐ DOVE STA `SET CONSTRAINTS ALL IMMEDIATE`, E PERCHE' NON IN CIMA.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e la deferralita' li' e' VOLUTA: si
--   crea il soggetto, poi il suo indirizzo, e la completezza si verifica al
--   COMMIT. Metterlo in cima, come fanno i file che scrivono in una tabella
--   sola, pretenderebbe l'indirizzo nell'istante dell'INSERT del soggetto,
--   cioe' vieterebbe il pattern che il dominio ha scelto. Sta percio' alla
--   FINE, nel punto in cui l'unita' di lavoro e' completa — ed e' il test 8,
--   che e' esattamente cio' che il COMMIT farebbe.
--
-- ⛔ FINO AL 2026-09-22 QUESTO FILE ERA DICHIARATO `pgtap-differiti: escluso`,
--   e la fixture lasciava un soggetto SENZA INDIRIZZO: uno stato che
--   l'applicazione non potrebbe mai committare. I tre guard non li esercitava
--   nessuno, e il verde era per sottrazione — reggeva solo finche' la finestra
--   differita non si chiudeva mai.
--   ⚠️ FATTO DATATO. Il 2026-09-22 il file e' uscito ERRORE_FIXTURE sullo
--   scratch `zeroerp_ci` con «Indirizzo obbligatorio mancante per soggetto …»:
--   su un database senza operatori la riga di contesto COSTRUISCE il mondo, e
--   quel builder esce `SET CONSTRAINTS ALL IMMEDIATE` (contratto dichiarato da
--   `20260921-18`). Da li' i differiti non erano piu' differiti e il guard ha
--   rifiutato il soggetto all'INSERT. Poi una corsa successiva ha COMMITTATO
--   l'operatore `PGTR0001` sullo scratch: da allora il ramo di costruzione non
--   si percorre piu' e il file e' tornato verde — cioe' il difetto e' stato
--   MASCHERATO da un residuo, non riparato. E' la terza occorrenza della
--   famiglia censita in `20260921-18` (le altre due: `anagrafiche/create-cliente`,
--   corretto, e `anagrafiche/test-soggetti-split-payment-cliente-pa`).
--   ⇒ La fixture ora e' completa e la riga e' al suo posto.
--   ⛔ CORREZIONE del 2026-09-23: la frase che seguiva («il file non dipende
--   piu' da CHI chiude la finestra differita») era falsa. Completare la
--   fixture sposta il giudizio in fondo, ma i vincoli li aveva gia' chiusi la
--   riga di contesto: sullo scratch ricostruito, senza residui, il file e'
--   morto di nuovo all'INSERT del soggetto. Da qui la riapertura dichiarata
--   subito dopo la riga di contesto.
--   Brief: brief-db-pgtap-runner-rls-baseline §20, §22.4.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   Il soggetto nasce, POI riceve indirizzo e contatti, e il test 8 chiude la
--   finestra «dove l'unita' di lavoro e' completa» (testata del file).
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   ERRORE_FIXTURE: «Indirizzo obbligatorio mancante per soggetto …»
--   all'INSERT del soggetto — il test 8 non arrivava mai.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(8);

-- =========================================================
-- 1) Precondizione: un comune di nascita disponibile
-- =========================================================
CREATE TEMP TABLE _t_comune AS
SELECT id AS comune_id
  FROM config.comuni
 ORDER BY id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_comune) = 1,
    '1. Precondizione: comune disponibile per fn_crea_soggetto_pf'
);

-- =========================================================
-- 2) Setup: soggetto PF pura via fn_crea_soggetto_pf
-- =========================================================
-- Uso md5 clock_timestamp per CF univoco (evita collisioni tra run).
-- CF fisso valido. pgTAP rollbacca a fine file, nessun conflitto
-- tra run. Email random per evitare collisioni nella tabella contatti.
CREATE TEMP TABLE _t_sogg AS
SELECT anagrafiche.fn_crea_soggetto_pf(
    p_cognome           := 'LccTestPfPura',
    p_nome              := 'Rld',
    p_codice_fiscale    := 'LCCRLD80A01L736X',
    p_email             := 'pgtap_pf_pura_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@test.local',
    p_data_nascita      := DATE '1980-01-01',
    p_sesso             := 'M',
    p_stato_iso2        := 'IT',
    p_comune_nascita_id := (SELECT comune_id FROM _t_comune),
    p_tipo_contatto_id  := NULL,
    p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
) AS soggetto_id;

SELECT ok(
    (SELECT soggetto_id FROM _t_sogg) IS NOT NULL,
    '2. Setup: creato soggetto PF pura (CF valorizzato, P.IVA NULL)'
);

-- --------------------------------------------------------------
-- 2-bis) Setup: gli INDIRIZZI che il dominio pretende dal soggetto
-- --------------------------------------------------------------
-- ⭐ Non e' contorno della fixture: senza queste righe il soggetto non e'
--   committabile, e il test 8 lo dimostrerebbe. Il tipo dettaglio `PR`
--   pretende RES e DOMFISC; il terzo obbligatorio (FATT) e' soddisfatto dal
--   proprio fallback su DOMFISC, quindi due indirizzi bastano — letto dalla
--   matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`, non dedotto.
-- ⚠️ Il dettaglio si FABBRICA: `anagrafiche.indirizzi_dettaglio` e' dato di
--   macchina e su un database ricostruito da zero ha zero righe, quindi
--   cercarne uno esistente renderebbe il file verde solo su dev.
-- ⚠️ I CONTATTI non stanno qui: li scrive gia' `fn_crea_soggetto_pf` dalla
--   `p_email` passata sopra, e basta un canale valorizzato al guard.
CREATE TEMP TABLE _t_dett AS
SELECT dbops.fn_pgtap_crea_indirizzo_dettaglio('pgtap-guard-soggetto-pf-pura') AS dettaglio_id;

-- ⚠️ `PERFORM` e non `SELECT`: la funzione ritorna l'id dell'indirizzo creato,
--   e un `SELECT` lo stamperebbe in mezzo al flusso TAP.
DO $ind$
BEGIN
    -- rev 2026-10-18: la madre prende l'indirizzo in jsonb (20261018-96)
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
        (SELECT soggetto_id FROM _t_sogg),
        jsonb_build_object('tipo_indirizzo_codice',  'RES',
                           'indirizzo_dettaglio_id', (SELECT dettaglio_id FROM _t_dett)));
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
        (SELECT soggetto_id FROM _t_sogg),
        jsonb_build_object('tipo_indirizzo_codice',  'DOMFISC',
                           'indirizzo_dettaglio_id', (SELECT dettaglio_id FROM _t_dett)));
END $ind$;

-- =========================================================
-- 3) Guard NULL -> throws
-- =========================================================
SELECT throws_ok(
    $$SELECT script.fn_guard_soggetto_pf_pura(NULL::uuid)$$,
    NULL,
    NULL,
    '3. p_soggetto_id NULL -> solleva eccezione (E_PARAMETRO_INVALIDO)'
);

-- =========================================================
-- 4) Guard soggetto inesistente -> throws
-- =========================================================
-- UUID random che non corrisponde a nessun soggetto reale.
SELECT throws_ok(
    format($$SELECT script.fn_guard_soggetto_pf_pura(%L::uuid)$$,
           gen_random_uuid()),
    NULL,
    NULL,
    '4. Soggetto inesistente -> solleva eccezione (E_SOGGETTO_NOT_FOUND)'
);

-- =========================================================
-- 5) Guard PF pura -> ritorna soggetto_id
-- =========================================================
-- La funzione ritorna l'id passato se il guard passa.
SELECT ok(
    script.fn_guard_soggetto_pf_pura((SELECT soggetto_id FROM _t_sogg))
        = (SELECT soggetto_id FROM _t_sogg),
    '5. PF pura valida -> ritorna soggetto_id passato (pass-through)'
);

-- =========================================================
-- 6) Setup: aggiungi P.IVA al soggetto (lo rende NON PF pura)
-- =========================================================
UPDATE anagrafiche.soggetti
   SET partita_iva = 'PGTAP' || upper(substring(md5(clock_timestamp()::text) from 1 for 6))
 WHERE id = (SELECT soggetto_id FROM _t_sogg);

SELECT ok(
    (SELECT partita_iva FROM anagrafiche.soggetti
      WHERE id = (SELECT soggetto_id FROM _t_sogg)) IS NOT NULL,
    '6. Setup: aggiunta P.IVA al soggetto'
);

-- =========================================================
-- 7) Guard con P.IVA -> throws
-- =========================================================
SELECT throws_ok(
    format($$SELECT script.fn_guard_soggetto_pf_pura(%L::uuid)$$,
           (SELECT soggetto_id FROM _t_sogg)),
    NULL,
    NULL,
    '7. Soggetto con P.IVA -> solleva E_AUTH_USER_SOGGETTO_CON_PIVA'
);

-- =========================================================
-- 8) La fixture e' COMMITTABILE: i tre guard differiti si chiudono
-- =========================================================
-- ⭐ E' il punto in cui l'unita' di lavoro e' completa, quindi qui va la riga
--   che gli altri file mettono in cima. `SET CONSTRAINTS ALL IMMEDIATE` e'
--   esattamente cio' che il COMMIT farebbe: i tre guard DEFERRABLE di
--   `soggetti` valutano ORA lo stato finale del soggetto — P.IVA compresa,
--   che il test 6 ha aggiunto.
-- ⛔ E' un'ASSERZIONE, non una riga di servizio, ed e' una scelta: se la
--   fixture tornasse incompleta il file morirebbe in fixture, cioe' con
--   copertura ZERO e l'etichetta ERRORE_FIXTURE, che e' il modo in cui un
--   buco si nasconde. Cosi' invece il file dice «non ok 8» e nomina la cosa.
SELECT lives_ok(
    $$SET CONSTRAINTS ALL IMMEDIATE$$,
    '8. La fixture e'' committabile: indirizzi, contatti e dati societari del soggetto soddisfano i tre guard differiti'
);

-- Nota: il caso "senza CF" non e' rappresentabile su soggetti PR reali
-- (trigger garantisce CF NOT NULL). Ramo difensivo della funzione coperto
-- dalla sola lettura del codice; non verificabile via pgTAP senza bypass
-- del trigger di guard (anti-pattern). Omesso volontariamente.

SELECT * FROM finish();

ROLLBACK;
