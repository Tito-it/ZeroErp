-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_change_user_emittenti_scope(p_auth_user_id, p_emittente_ids)
--   Orchestrazione atomica del cambio scope per il drawer Operatore
--   (Fase 2 P1 2026-04-29).
--
-- Strategia:
--   Setup OPERATORE vergine non-SA (cambio scope senza interazione
--   con guard ultimo-SA). Setup separato SA singleton per testare
--   il guard E_PROFILO_ULTIMO_SUPER_ADMIN. Stato accumulato tra i
--   casi (no SAVEPOINT) e rolled-back a fine file.
--   ⭐ Dal 2026-11-25 (giro 10, brief-db-porte-aperte-dalla-sola-guc §10) il
--   verbo chiede il SUPER_ADMIN: lo chiama il SA costruito, nel contesto. I
--   casi del permesso e della porta sono in config/test-porta-scope-emittenti-v1.
--
-- Indice test (1..8):
--   1. MULTI (>1) -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO
--   2. senza riga -> SINGLE  (INSERT)        -> changed=true, riga creata
--   3. SINGLE -> SINGLE stesso EF (no-op)    -> changed=false, riga invariata
--   4. operatore SINGLE -> GLOBAL            -> raise E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN,
--                                               e la riga resta (5)
--   6. operatore senza riga -> GLOBAL        -> raise anche li': non e' un no-op
--   7. SUPER_ADMIN SINGLE -> GLOBAL          -> changed=true, riga rimossa (7.bis)
--   8. Ultimo SA cambia scope -> raise E_PROFILO_ULTIMO_SUPER_ADMIN
--   ⭐ Rev 2026-11-26 (giro 10-ter, brief-db-porte-aperte-dalla-sola-guc §10-ter):
--   l'operatore non e' mai «globale». Fino a oggi il 4 portava l'operatore a GLOBAL
--   e il 5 contava la riga tolta: ora il 4 e' il rifiuto e il 5 la riga che resta.
--   GLOBAL si prova su un secondo SUPER_ADMIN (7), costruito.
--
-- Niente SAVEPOINT (azzera il counter pgTAP).
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

-- ⛔ LE TRE IDENTITA' SI COSTRUISCONO, non si cercano (2026-09-12). La fixture
--   del 2026-08-18 aveva imparato a COSTRUIRE lo stato GLOBAL, ma l'operatore a
--   cui costruirlo lo cercava ancora fra gli esistenti — e su un database
--   ricostruito dai changelog non ce n'e' nessuno: «p_auth_user_id non valido:
--   NULL», sette asserzioni perse. Due aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`, PRIMA di aprire il contesto:
--   quella del contesto e quella su cui si porta l'operatore sotto test.
--   L'operatore sotto test e il super admin sono persone costruite con
--   `dbops.fn_pgtap_crea_operatore_umano`, che nascono SENZA azienda (rev
--   2026-11-25): lo stato GLOBAL e' costruito, senza toccare la porta.
CREATE TEMP TABLE _mondi AS
SELECT 'CTX' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'OP'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _t_user AS
SELECT o.auth_user_id AS au_id FROM dbops.fn_pgtap_crea_operatore_umano('scope-sotto-test', false) o;

CREATE TEMP TABLE _t_sa AS
SELECT o.auth_user_id AS au_id, o.identita_id AS id_id
  FROM dbops.fn_pgtap_crea_operatore_umano('scope-super-admin', true) o;

-- Il secondo operatore senza azienda (6) e il secondo SUPER_ADMIN (7): nascono
-- senza azienda come gli altri.
CREATE TEMP TABLE _t_user_senza AS
SELECT o.auth_user_id AS au_id FROM dbops.fn_pgtap_crea_operatore_umano('scope-senza-azienda', false) o;

CREATE TEMP TABLE _t_sa2 AS
SELECT o.auth_user_id AS au_id
  FROM dbops.fn_pgtap_crea_operatore_umano('scope-super-admin-2', true) o;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'CTX'));
END $ctx$;

-- Chi chiama il verbo e' il super admin costruito: il verbo chiede il SUPER_ADMIN.
DO $sa$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT au_id FROM _t_sa));
END $sa$;

-- 🔴 plan 6 -> 7 il 2026-08-18: le asserzioni erano SEMPRE state sette (il
--   punto 2 ne ha due: `changed=true` e la riga effettivamente scritta), ma il
--   file moriva alla prima e il piano sbagliato non si e' mai visto.
--   ⚠️ Un piano piu' basso del numero di asserzioni non e' un dettaglio
--   formale: pgTAP lo segnala come «Bad plan» e rende ROSSO un file in cui
--   tutte le asserzioni passano — cioe' nasconde il verde, dopo aver nascosto
--   il rosso.
SELECT plan(10);

CREATE OR REPLACE FUNCTION pg_temp.disable_other_sa(p_keep_bind_id bigint)
RETURNS int LANGUAGE plpgsql AS $$
DECLARE v_b record; v_count int := 0;
BEGIN
    FOR v_b IN
        SELECT pab.id FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
         WHERE pa.codice = 'SUPER_ADMIN' AND pab.attivo = true
           AND pab.id <> p_keep_bind_id
    LOOP
        UPDATE config.profili_accesso_bindings SET attivo = false WHERE id = v_b.id;
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END
$$;

-- =========================================================
-- Setup OPERATORE non-SA libero (no binding, no user_emittenti_fiscali)
-- =========================================================
-- 🔴 FIXTURE RICOSTRUITA il 2026-08-18.
--   Cercava un operatore che fosse GIA' in stato GLOBAL — senza binding e senza
--   riga in `user_emittenti_fiscali` — e si affidava al fatto che in sviluppo
--   ne esistesse uno. Dal cantiere perimetro emittente (DL-A) quegli operatori
--   sono a ZERO: la ricerca tornava vuota, `au_id` usciva NULL e la funzione
--   sollevava «p_auth_user_id non valido: NULL». Sei asserzioni su sei perse.
--
--   ⚠️ La fixture non costruiva la precondizione: la CERCAVA, e ha smesso di
--   trovarla il giorno in cui il progetto ha sistemato i dati. E' lo stesso
--   difetto che ha gia' colpito test-permessi-user-overrides — «prendi il primo
--   e spera» — solo al contrario: li' il dato reale c'era di troppo, qui manca.
--
--   ⭐ Ora lo stato GLOBAL si COSTRUISCE: l'operatore sotto test e' una persona
--   costruita con `dbops.fn_pgtap_crea_operatore_umano` (in testa), che nasce
--   senza azienda come in produzione.
--   ⛔ Non si toglie la riga col verbo: sarebbe la funzione SOTTO TEST a
--   costruire la propria precondizione, e un difetto in lei renderebbe il test
--   verde per errore. E non la si toglie a mano: dal giro 10 la porta del DELETE
--   si apre solo dal verbo.
--   Il file e' transazionale: lo scope vero torna al ROLLBACK.

-- L'EF per il caso SINGLE: quello dell'azienda dell'operatore sotto test
CREATE TEMP TABLE _t_ef AS
SELECT m.emittente_fiscale_id AS ef_id FROM _mondi m WHERE m.lato = 'OP';

-- =========================================================
-- 1) Guard MULTI (>1 elementi) -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO
-- =========================================================
SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[1::bigint, 2::bigint]) $sql$,
        (SELECT au_id FROM _t_user)
    ),
    '%MULTI%',
    '1. p_emittente_ids con >1 elementi -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO'
);

-- =========================================================
-- 2) GLOBAL -> SINGLE: INSERT, changed=true
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                ARRAY[(SELECT ef_id FROM _t_ef)]
            )->>'changed')::boolean,
    true,
    '2. GLOBAL -> SINGLE: changed=true'
);

SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_user)),
    1,
    '2.bis Riga creata in user_emittenti_fiscali'
);

-- =========================================================
-- 3) SINGLE -> SINGLE stesso EF: no-op, changed=false
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                ARRAY[(SELECT ef_id FROM _t_ef)]
            )->>'changed')::boolean,
    false,
    '3. SINGLE -> SINGLE stesso EF: no-op (changed=false)'
);

-- =========================================================
-- 4) operatore SINGLE -> GLOBAL: rifiutato, la riga resta
--    Un operatore che non e' SUPER_ADMIN lavora sempre per un emittente.
-- =========================================================
SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, NULL::bigint[]) $sql$,
        (SELECT au_id FROM _t_user)
    ),
    '%Tutti gli emittenti%',
    '4. operatore SINGLE -> GLOBAL: raise E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN'
);

SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_user)),
    1,
    '5. dopo il rifiuto la riga dell''operatore resta'
);

-- =========================================================
-- 6) operatore senza riga -> GLOBAL: rifiutato anche li'
--    Prima del no-op: chiederlo e' sbagliato anche se non cambierebbe niente.
-- =========================================================
SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, '{}'::bigint[]) $sql$,
        (SELECT au_id FROM _t_user_senza)
    ),
    '%Tutti gli emittenti%',
    '6. operatore senza riga -> GLOBAL: raise, non no-op'
);

-- =========================================================
-- 7) SUPER_ADMIN SINGLE -> GLOBAL: ammesso, la riga si toglie
--    dalla porta del verbo (guard_delete, da proprietario).
--    Il SA2 riceve prima un'azienda dal verbo.
-- =========================================================
SELECT script.fn_change_user_emittenti_scope(
           (SELECT au_id FROM _t_sa2), ARRAY[(SELECT ef_id FROM _t_ef)]);

SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_sa2),
                NULL::bigint[]
            )->>'changed')::boolean,
    true,
    '7. SUPER_ADMIN SINGLE -> GLOBAL: changed=true (la porta del guard_delete, dal verbo)'
);

SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_sa2)),
    0,
    '7.bis Riga del SUPER_ADMIN rimossa dopo SINGLE -> GLOBAL'
);

-- =========================================================
-- 8) Ultimo SA: cambio scope vietato -> raise E_PROFILO_ULTIMO_SUPER_ADMIN
--    Setup: il SA costruito in testa (nasce GLOBAL, quindi il target SINGLE
--    e' un cambio reale) resta l'unico: gli altri SA si spengono. Chiama il
--    verbo su se stesso: il guard del permesso passa, quello dell'ultimo SA no.
-- =========================================================
SELECT pg_temp.disable_other_sa(
    (SELECT pab.id FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
      WHERE pa.codice = 'SUPER_ADMIN' AND pab.attivo
        AND pab.identita_digitale_id = (SELECT id_id FROM _t_sa)));

SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[%s::bigint]) $sql$,
        (SELECT au_id FROM _t_sa),
        (SELECT ef_id FROM _t_ef)
    ),
    '%SUPER_ADMIN%',
    '8. Ultimo SA: cambio scope reale -> raise E_PROFILO_ULTIMO_SUPER_ADMIN'
);

SELECT * FROM finish();
ROLLBACK;
