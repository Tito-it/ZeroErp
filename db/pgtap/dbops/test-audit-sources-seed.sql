-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed dbops.audit_sources (Fase 5 P1 2026-04-29 +
-- aggiornato 2026-05-04 dismissione modello profili_reparto_*).
--
-- Verifica:
--   - 8 righe seedate (4 user_override/emittenti + identita +
--     3 profili_accesso_*).
--   - Coerenza area_funzionale con il vocabolario controllato:
--     PERMESSI | AUTH | ANAGRAFICHE | EMITTENTI | FATTURAZIONE.
--   - Le storico_table / storico_pk_col puntano a oggetti esistenti
--     (catch tipo nel CSV).
--   - Nessun residuo del modello legacy profili_reparto_*.
--   - La vista pubblica script.vw_audit_sources espone esattamente quattro colonne
--     (code, label_key, area_funzionale, storico_table).
--
-- Indice test (1..8):
--    1. dbops.audit_sources contiene almeno 8 righe attive
--    2. Codici attesi presenti (set match) — incluso il nuovo
--       modello profili_accesso_aree/_azioni/_bindings
--    3. Tutte le righe attive usano un valore di area_funzionale
--       del vocabolario controllato
--    4. Tutte le storico_table referenziate esistono (regclass cast)
--    5. Tutte le storico_pk_col referenziate esistono come colonne
--       della rispettiva storico
--    6. Nessun codice legacy profili_reparto_* presente
--    7. Vista vw_audit_sources espone esattamente 4 colonne
--       (code, label_key, area_funzionale, storico_table)
--    8. La riga di risorse_umane_auth_user NON esiste piu' (ritirata
--       il 12-09-2026 con la tabella ponte legacy, 80_data/20260912-09)
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

SELECT plan(8);

-- =========================================================
-- 1) Almeno 8 righe attive
-- =========================================================
-- ⚠️ Era `>= 9` fino al 2026-09-02: `risorse_umane_auth_user` (riga 5) e'
--   stata dismessa quel giorno, quindi le attive sono 8. Vedi il test 2, che
--   dice QUALE e perche'.
SELECT cmp_ok(
    (SELECT count(*)::int FROM dbops.audit_sources WHERE attivo = true),
    '>=',
    8,
    '1) dbops.audit_sources ha almeno 8 righe attive (post dismissione profili_reparto_* e risorse_umane_auth_user)'
);

-- =========================================================
-- 2) Set di codici attesi presenti (intersezione match)
-- =========================================================
SELECT bag_eq(
    $$
    SELECT code FROM dbops.audit_sources WHERE attivo = true
     AND code IN ('user_override_aree','user_override_azioni','user_override_oggetti',
                  'user_emittenti_fiscali','risorse_umane_auth_user','identita_digitali',
                  'profili_accesso_aree','profili_accesso_azioni','profili_accesso_bindings')
    $$,
    $$ VALUES ('user_override_aree'),('user_override_azioni'),('user_override_oggetti'),
              ('user_emittenti_fiscali'),('identita_digitali'),
              ('profili_accesso_aree'),('profili_accesso_azioni'),('profili_accesso_bindings') $$,
    '2) Gli 8 codici target sono attivi, e risorse_umane_auth_user NON lo e'' piu'''
);

-- ⭐ NOTA SULLA FORMA, perche' la scelta non e' cosmetica: `risorse_umane_auth_user`
--   resta nell'`IN (...)` qui sopra — cioe' nel PERIMETRO interrogato — ed e'
--   uscito solo dalle ATTESE. Cosi' il test non si limita a ignorarlo: se
--   qualcuno lo riattivasse, il `bag_eq` troverebbe 9 codici contro 8 attesi e
--   diventerebbe ROSSO. Toglierlo da entrambi i lati avrebbe reso la
--   riattivazione invisibile, ed e' proprio la decisione che va presidiata.
--
-- ⛔ PERCHE' E' STATO DISMESSO (2026-09-02). La sua `storico_table` era
--   `storico.risorse_umane_auth_user`, che su un database RICOSTRUITO non
--   nasce piu': `anagrafiche.risorse_umane_auth_user` e' diventata una VISTA
--   (la tabella e' `_legacy_...`, changeSet 20260429-19a) e l'automazione dello
--   storico lavora sulle TABELLE. In dev la vecchia sopravvive dalla storia del
--   database, in CI no — di li' 9 errori Django tutti uguali.
--   ⚠️ E la strada «puntala alla _legacy» e' stata SCARTATA su una misura:
--   `storico._legacy_risorse_umane_auth_user` ha ZERO righe, mentre i 12
--   snapshot pre-cutover stanno nella vecchia. Ripuntarla avrebbe mostrato un
--   audit VUOTO invece di un errore — la stessa perdita, ma muta.
--   L'audit AUTH del presente e' coperto da `identita_digitali` (riga 8).
--
-- ✅ CHIUSO il 2026-09-12: la riga 5 e' stata CANCELLATA (80_data/20260912-09,
--   e tolta dal CSV) insieme alla tabella ponte legacy e alle sue due shadow
--   (20260912-03, -08, -10; brief-db-rls-storico-scope-congelato §10). Il
--   `risorse_umane_auth_user` nell'`IN (...)` del test 2 RESTA: ora presidia
--   che nessuno la REINSERISCA attiva. Il test 8 presidia che non esista
--   affatto, attiva o no.

-- =========================================================
-- 3) Vocabolario controllato area_funzionale
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources
      WHERE attivo = true
        AND area_funzionale NOT IN
            ('PERMESSI','AUTH','ANAGRAFICHE','EMITTENTI','FATTURAZIONE')),
    0,
    '3) Tutte le righe usano un area_funzionale del vocabolario controllato'
);

-- =========================================================
-- 4) Le storico_table esistono come oggetti DB (regclass cast
--    fallirebbe se la tabella non esiste -> raise gestito da DO)
-- =========================================================
DO $check$
DECLARE
    v_row record;
BEGIN
    FOR v_row IN SELECT code, storico_table FROM dbops.audit_sources WHERE attivo = true
    LOOP
        PERFORM v_row.storico_table::regclass;
    END LOOP;
END
$check$;

SELECT pass('4) Tutte le storico_table referenziate esistono (regclass cast OK)');

-- =========================================================
-- 5) Tutte le storico_pk_col esistono come colonne nelle storico
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources s
      WHERE s.attivo = true
        AND NOT EXISTS (
            SELECT 1
              FROM information_schema.columns c
             WHERE c.table_schema = split_part(s.storico_table, '.', 1)
               AND c.table_name   = split_part(s.storico_table, '.', 2)
               AND c.column_name  = s.storico_pk_col
        )),
    0,
    '5) Tutte le storico_pk_col referenziate esistono come colonne'
);

-- =========================================================
-- 6) Nessun residuo del modello legacy profili_reparto_*
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources
      WHERE code IN ('profili_reparto_aree','profili_reparto_azioni')),
    0,
    '6) Nessun codice legacy profili_reparto_* in dbops.audit_sources'
);

-- =========================================================
-- 7) La vista pubblica espone esattamente quattro colonne
-- =========================================================
SELECT bag_eq(
    $$
    SELECT column_name
      FROM information_schema.columns
     WHERE table_schema = 'script'
       AND table_name   = 'vw_audit_sources'
    $$,
    $$ VALUES ('code'), ('label_key'), ('area_funzionale'), ('storico_table') $$,
    '7) script.vw_audit_sources espone esattamente (code, label_key, area_funzionale, storico_table)'
);

-- ⭐ `storico_table` e' entrata il 2026-09-02 (changeSet 20260902-11) e questo
--   test e' cambiato NELLO STESSO GIRO. Prima la vista esponeva solo i tre
--   campi del contratto API, e il backend il nome fisico se lo costruiva
--   concatenando `code` — che e' l'identita' LOGICA, e alla prima storico
--   rinominata si separa dal nome fisico senza dare nessun avviso.
-- ⚠️ Un presidio sulla FORMA va cambiato insieme alla forma, o smette di
--   essere un presidio e diventa un ostacolo: e' `bag_eq`, quindi una colonna
--   in piu' lo fa rosso anche quando l'aggiunta e' voluta.

-- =========================================================
-- 8) La riga di risorse_umane_auth_user non esiste piu'
-- =========================================================
-- Fino al 2026-09-12 era `attivo = f` (la dichiarazione della dismissione);
-- quel giorno la tabella ponte legacy e' stata eliminata con le sue shadow, e
-- una riga che punta a `storico.risorse_umane_auth_user` — che non esiste piu'
-- dal 20260912-03 — non dichiara piu' niente. Forma del test 6.
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources
      WHERE code = 'risorse_umane_auth_user'
         OR storico_table IN ('storico.risorse_umane_auth_user',
                              'storico._legacy_risorse_umane_auth_user')),
    0,
    '8) Nessuna riga risorse_umane_auth_user in dbops.audit_sources (ritirata il 2026-09-12)'
);

SELECT * FROM finish();
ROLLBACK;
