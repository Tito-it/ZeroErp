-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL nello schema magazzino (funzioni, una vista, una tabella con FK, trigger, policy e default testimoni, portati via dal ROLLBACK): l'applicazione non crea oggetti, e il soggetto del test e' il catalogo, non un percorso applicativo.
-- pgTAP test per Zero ERP
--
-- Test: CANCELLO — il registro di magazzino non nomina i suoi consumatori
--   dbops.vw_magazzino_dipendenze_inverse
--
-- Brief: brief-db-magazzino-registro-anello-interno, sezioni 2 (D-1, D-2, D-3) e 4
-- ChangeSet: 20_code/dbops/20261001-23 · 90_end/20261001-26 · catalogo dbops.presidi
--            (e cio' che il cancello chiude: 20_code/vendite/20261001-18 … -21,
--             00_schema/magazzino/20261001-22, 90_end/20261001-24)
--
-- ⭐ LA MATRICE DELLE DIPENDENZE ERA SCRITTA, E NESSUN TEST LA LEGGEVA: il verso
--   inverso (magazzino -> vendite) e' entrato coi Lotti 3 e 3-bis senza un rosso.
--   Il registro di magazzino e' un servizio dell'anello 2 (D-1): nessun suo
--   oggetto nomina uno schema di processo. Questo file pretende la vista vuota,
--   in CI, a ogni build.
--
-- ⭐ E SI PROVA CHE LA LENTE VEDA: una vista vuota potrebbe essere vuota perche'
--   non guarda (Regola zero: il caso si COSTRUISCE). Sei testimoni, uno per
--   strada — una funzione plpgsql che legge vendite (lente CORPO); una vista su
--   acquisti, una FK verso pagamenti, un trigger che esegue una funzione di
--   vendite, una policy e un default che nominano vendite (lente CATALOGO) —
--   piu' il gemello negativo: una funzione che nomina vendite SOLO in un
--   commento non conta. Poi il ROLLBACK li porta via.
--   ⚠️ Vista, trigger, policy e default sono i quattro oggetti che
--   pg_identify_object restituisce SENZA schema: la vista li attribuisce alla
--   tabella che li porta. Il testimone della vista l'ha trovato alla prima
--   prova (2026-10-01): la lente era cieca sulle viste.
--
-- Elenco test (plan 14):
--    1  : ⛔ la vista e' VUOTA: nessun oggetto di magazzino nomina vendite, acquisti, pagamenti
--    2  : gemello «esiste»: il verso giusto (FK da vendite verso magazzino) c'e', e pg_depend lo registra
--    3  : il perimetro dichiarato nella vista e' {vendite, acquisti, pagamenti}
--    4  : ⭐ una funzione di magazzino che legge vendite.ddt -> la vista la vede (CORPO)
--    5  : … e una che nomina vendite.ddt SOLO in un commento di riga non la vede
--    6  : ⭐ una vista di magazzino su acquisti.ordini -> la vista la vede (CATALOGO)
--    7  : ⭐ una FK da magazzino verso pagamenti.enti_incasso -> la vista la vede (CATALOGO)
--    8  : ⭐ un trigger su una tabella di magazzino che esegue una funzione di vendite -> la vede
--    9  : ⭐ una policy su una tabella di magazzino che legge vendite.ddt -> la vede
--   10  : ⭐ un default di una colonna di magazzino che nomina il tipo vendite.ddt -> la vede
--   11  : i posting non stanno piu' nel registro: magazzino.fn_posta_ddt / fn_posta_reso non esistono
--   12  : … e stanno in vendite, SECURITY DEFINER
--   13  : magazzino.assets non porta piu' contratto_id (D-3)
--   14  : la vista e' a catalogo in dbops.presidi come CANCELLO, presidiata da questo file
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

SELECT is((SELECT count(*) FROM dbops.vw_magazzino_dipendenze_inverse),
          0::bigint,
          '1. nessun oggetto dello schema magazzino nomina uno schema di processo: il registro non conosce i suoi consumatori');

-- Gemello «esiste», calcolato SENZA passare dalla vista: le FK del verso giusto
-- (un documento di vendite che punta al registro) sono in pg_depend. Se fossero
-- zero, la lente CATALOGO vuota non direbbe niente.
SELECT cmp_ok((SELECT count(*) FROM pg_constraint k
                 JOIN pg_class c  ON c.oid = k.conrelid
                 JOIN pg_namespace n  ON n.oid = c.relnamespace
                 JOIN pg_class cf ON cf.oid = k.confrelid
                 JOIN pg_namespace nf ON nf.oid = cf.relnamespace
                WHERE k.contype = 'f' AND n.nspname = 'vendite' AND nf.nspname = 'magazzino'),
              '>', 0::bigint,
              '2. gemello «esiste»: vendite punta al registro (il verso giusto), e il catalogo lo registra');

-- Il perimetro e' il contratto e vive nella definizione della vista.
SELECT ok(pg_get_viewdef('dbops.vw_magazzino_dipendenze_inverse'::regclass) LIKE '%''vendite''%'
          AND pg_get_viewdef('dbops.vw_magazzino_dipendenze_inverse'::regclass) LIKE '%''acquisti''%'
          AND pg_get_viewdef('dbops.vw_magazzino_dipendenze_inverse'::regclass) LIKE '%''pagamenti''%',
          '3. il perimetro dichiarato e'' {vendite, acquisti, pagamenti}: uno schema di processo nuovo e'' un changeSet firmato');

-- I testimoni. Non vengono eseguiti: basta che esistano, il cancello guarda il catalogo.
CREATE FUNCTION magazzino.fn_pgtap_legge_vendite()
RETURNS bigint LANGUAGE plpgsql AS $f$
BEGIN
    RETURN (SELECT count(*) FROM vendite.ddt);
END
$f$;

CREATE FUNCTION magazzino.fn_pgtap_nomina_vendite_in_prosa()
RETURNS bigint LANGUAGE plpgsql AS $f$
BEGIN
    -- Una volta questa funzione leggeva vendite.ddt: ora non piu'.
    RETURN 0;
END
$f$;

CREATE VIEW magazzino.vw_pgtap_legge_acquisti AS
SELECT o.id FROM acquisti.ordini o;

CREATE TABLE magazzino.pgtap_punta_pagamenti (
    id      bigint PRIMARY KEY,
    ente_id bigint CONSTRAINT fk_pgtap_punta_pagamenti REFERENCES pagamenti.enti_incasso (id),
    -- il default nomina il tipo riga di vendite.ddt: il catalogo lo registra
    ddt_id  bigint DEFAULT (NULL::vendite.ddt).id
);

CREATE TRIGGER trg_pgtap_esegue_vendite
    BEFORE UPDATE ON magazzino.pgtap_punta_pagamenti
    FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_ordini_ful_guard_consistenza();

CREATE POLICY pgtap_legge_vendite ON magazzino.pgtap_punta_pagamenti
    USING (EXISTS (SELECT 1 FROM vendite.ddt));

SELECT is((SELECT come || '|' || schema_nominato || '|' || nominati
             FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE oggetto LIKE 'magazzino.fn_pgtap_legge_vendite(%'),
          'CORPO|vendite|vendite.ddt',
          '4. una funzione di magazzino che legge vendite.ddt: la vista la vede, dal corpo');

SELECT is((SELECT count(*) FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE oggetto LIKE 'magazzino.fn_pgtap_nomina_vendite_in_prosa(%'),
          0::bigint,
          '5. una funzione che nomina vendite.ddt solo in un commento di riga: la vista non la vede');

SELECT is((SELECT come || '|' || schema_nominato
             FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE oggetto LIKE '%magazzino.vw_pgtap_legge_acquisti%'),
          'CATALOGO|acquisti',
          '6. una vista di magazzino su acquisti.ordini: la vista la vede, dal catalogo');

SELECT is((SELECT come || '|' || schema_nominato
             FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE oggetto LIKE 'fk_pgtap_punta_pagamenti on magazzino.pgtap_punta_pagamenti%'),
          'CATALOGO|pagamenti',
          '7. una FK da magazzino verso pagamenti: la vista la vede, dal catalogo');

SELECT is((SELECT come || '|' || schema_nominato
             FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE oggetto LIKE 'trg_pgtap_esegue_vendite on magazzino.pgtap_punta_pagamenti%'),
          'CATALOGO|vendite',
          '8. un trigger su una tabella di magazzino che esegue una funzione di vendite: la vista lo vede');

SELECT is((SELECT come || '|' || schema_nominato
             FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE oggetto LIKE 'pgtap_legge_vendite on magazzino.pgtap_punta_pagamenti%'),
          'CATALOGO|vendite',
          '9. una policy su una tabella di magazzino che legge vendite.ddt: la vista la vede');

SELECT is((SELECT come || '|' || schema_nominato
             FROM dbops.vw_magazzino_dipendenze_inverse
            WHERE tipo_oggetto = 'default value'
              AND oggetto LIKE '%magazzino.pgtap_punta_pagamenti.ddt_id%'),
          'CATALOGO|vendite',
          '10. un default di una colonna di magazzino che nomina vendite.ddt: la vista lo vede');

-- Cio' che il cancello chiude: i due posting e la FK dell'asset.
SELECT ok(to_regproc('magazzino.fn_posta_ddt') IS NULL AND to_regproc('magazzino.fn_posta_reso') IS NULL,
          '11. i posting non stanno piu'' nel registro: magazzino.fn_posta_ddt e fn_posta_reso non esistono');

SELECT is((SELECT string_agg(n.nspname || '.' || p.proname || '=' || p.prosecdef::text, ',' ORDER BY p.proname)
             FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'vendite' AND p.proname IN ('fn_posta_ddt', 'fn_posta_reso')),
          'vendite.fn_posta_ddt=true,vendite.fn_posta_reso=true',
          '12. i posting stanno in vendite, nel dominio che muove la merce, SECURITY DEFINER');

SELECT hasnt_column('magazzino', 'assets', 'contratto_id',
          '13. magazzino.assets non porta il contratto: se servira'', il legame nasce nel contratto (D-3)');

SELECT ok((SELECT natura = 'CANCELLO'
                  AND presidiato_da = 'db/pgtap/magazzino/test-registro-non-nomina-i-consumatori-v1.sql'
                  AND cadenza = 'MAI' AND attivo AND obsoleto_dal IS NULL
             FROM dbops.presidi WHERE vista = 'dbops.vw_magazzino_dipendenze_inverse'),
          '14. la vista e'' a catalogo come CANCELLO, attiva, presidiata da questo file');

SELECT * FROM finish();
ROLLBACK;
