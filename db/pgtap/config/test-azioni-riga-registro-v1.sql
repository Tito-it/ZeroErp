-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il PRESIDIO del registro delle azioni di riga (config.azioni_riga,
--   20261027-23) e la prima superficie, vendite.vw_lotti_gruppi_azioni (20261027-24).
--   Brief: brief-modello-documento-vendita §15.10 (D-N1, F-5, Q-F5 = vista DB di
--   Tid, 2026-10-27); §15.17 (D-S2 = (b), Tid 2026-10-28: test 8, 20261028-02).
-- ------------------------------------------------------------
-- Un pulsante di riga ha tre pezzi che devono dire la stessa cosa: il verbo che
--   RIFIUTA (col primo motivo della sua fn_check), la superficie che il frontend
--   LEGGE (la vista con le colonne del motivo) e la fn_check che entrambi
--   chiamano. I test 2-6 valgono per OGNI riga attiva del registro: una riga
--   nuova e' presidiata senza toccare questo file.
-- ⚠️ Il registro porta TEXT, non regclass/regprocedure: un reg* salva l'OID e
--   stampa un numero quando l'oggetto sparisce, senza errore. Che puntino a
--   oggetti vivi lo dice questo file.
-- Indice test (1..8):
--   1) il registro non e' vuoto (altrimenti 2-6 sarebbero verdi per sottrazione)
--   2) ogni superficie e' una VISTA viva, security_invoker
--   3) ogni superficie ha le due colonne del motivo, di tipo text
--   4) ogni fn_check e ogni verbo esistono, con un nome solo (nessun overload)
--   5) ogni superficie DIPENDE dalla sua fn_check (pg_depend della regola)
--   6) ogni verbo CHIAMA la sua fn_check (definizione della funzione)
--   7) vw_lotti_gruppi_azioni: su un lotto costruito, il motivo della vista e'
--      il primo motivo della fn_check, riga per riga
--   8) la scheda Critiche: ogni segnalazione che nomina un documento
--      (fn_list_lotto_segnalazioni.gruppo_key) ha la sua riga nella vista, col
--      motivo della fn_check, anche se il documento non e' ne' nel perimetro
--      ne' negli esiti (D-S2, 20261028-02)
-- ------------------------------------------------------------
BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: in un test che chiude in ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

CREATE TEMP TABLE t_reg AS
SELECT r.codice_interno, r.superficie, r.colonna_motivo, r.colonna_motivo_chiave,
       r.fn_check, r.verbo,
       to_regclass(r.superficie) AS vista
  FROM config.azioni_riga r
 WHERE r.attivo;

SELECT ok(
    (SELECT count(*) FROM t_reg) > 0,
    '1) il registro delle azioni di riga ha almeno una riga attiva'
);

SELECT is(
    (SELECT string_agg(r.codice_interno, ',' ORDER BY r.codice_interno)
       FROM t_reg r
       LEFT JOIN pg_class c ON c.oid = r.vista
      WHERE c.oid IS NULL OR c.relkind <> 'v'
         OR NOT coalesce('security_invoker=true' = ANY (c.reloptions), false)),
    NULL,
    '2) ogni superficie e'' una vista viva, security_invoker'
);

SELECT is(
    (SELECT string_agg(r.codice_interno || '.' || k.col, ',' ORDER BY r.codice_interno, k.col)
       FROM t_reg r
       CROSS JOIN LATERAL (VALUES (r.colonna_motivo), (r.colonna_motivo_chiave)) k(col)
      WHERE NOT EXISTS (SELECT 1 FROM pg_attribute a
                         WHERE a.attrelid = r.vista AND a.attname = k.col
                           AND NOT a.attisdropped AND a.atttypid = 'text'::regtype)),
    NULL,
    '3) ogni superficie ha le due colonne del motivo, di tipo text'
);

-- Le funzioni per nome: schema.nome, una sola (un overload renderebbe ambiguo
-- che cosa chiamano superficie e verbo).
CREATE TEMP TABLE t_fn AS
SELECT r.codice_interno, k.ruolo, k.nome,
       (SELECT array_agg(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = split_part(k.nome, '.', 1)
           AND p.proname = split_part(k.nome, '.', 2)) AS oids
  FROM t_reg r
 CROSS JOIN LATERAL (VALUES ('fn_check', r.fn_check), ('verbo', r.verbo)) k(ruolo, nome);

SELECT is(
    (SELECT string_agg(f.codice_interno || '.' || f.ruolo, ',' ORDER BY f.codice_interno, f.ruolo)
       FROM t_fn f WHERE coalesce(cardinality(f.oids), 0) <> 1),
    NULL,
    '4) ogni fn_check e ogni verbo esistono, con un nome solo'
);

SELECT is(
    (SELECT string_agg(r.codice_interno, ',' ORDER BY r.codice_interno)
       FROM t_reg r
       JOIN t_fn f ON f.codice_interno = r.codice_interno AND f.ruolo = 'fn_check'
      WHERE NOT EXISTS (
              SELECT 1 FROM pg_rewrite w
                JOIN pg_depend d ON d.objid = w.oid AND d.classid = 'pg_rewrite'::regclass
               WHERE w.ev_class = r.vista
                 AND d.refclassid = 'pg_proc'::regclass
                 AND d.refobjid = f.oids[1])),
    NULL,
    '5) ogni superficie dipende dalla sua fn_check: tooltip ed errore dalla stessa funzione'
);

SELECT is(
    (SELECT string_agg(r.codice_interno, ',' ORDER BY r.codice_interno)
       FROM t_reg r
       JOIN t_fn v ON v.codice_interno = r.codice_interno AND v.ruolo = 'verbo'
      WHERE cardinality(v.oids) = 1
        AND position(r.fn_check IN pg_get_functiondef(v.oids[1])) = 0),
    NULL,
    '6) ogni verbo chiama la sua fn_check'
);

-- ============================================================
-- 7) La prima superficie su un lotto costruito
-- ============================================================
CREATE TEMP TABLE t_com AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('pgtap azioni riga', NULL, NULL, false, true);

CREATE TEMP TABLE t_lotto AS
SELECT l.* FROM t_com c,
       dbops.fn_pgtap_crea_lotto('pgtap azioni riga', 'DRAFT', c.billing_account_id) l;

-- Due documenti nel lotto: uno solo dichiarato nel perimetro, uno con un esito
-- in ERRORE (il caso in cui l'azione e' viva).
INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT (SELECT lotto_id FROM t_lotto), 'COMMESSA:' || (SELECT commessa_id FROM t_com);

INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione,
                                              errore_codice, errore_messaggio)
SELECT (SELECT lotto_id FROM t_lotto), 'PGTAP:azioni-riga-errore', 'ERRORE',
       'E_PGTAP', 'esito in errore costruito dal test';

SELECT is(
    (SELECT count(*) FILTER (WHERE v.uscita_blocco_reason_key IS NOT DISTINCT FROM
                                   (script.fn_check_documento_escludibile_da_giro(v.lotto_id, v.gruppo_key)
                                      -> 0 ->> 'reason_key'))
            || '/' || count(*)
       FROM vendite.vw_lotti_gruppi_azioni v
      WHERE v.lotto_id = (SELECT lotto_id FROM t_lotto)),
    '2/2',
    '7) vw_lotti_gruppi_azioni: il motivo di ogni riga e'' il primo della fn_check (perimetro unito agli esiti)'
);

-- ============================================================
-- 8) La scheda Critiche legge la stessa superficie (D-S2)
-- ============================================================
-- Una segnalazione del giornale che nomina un documento fuori dal perimetro e
-- dagli esiti: senza il ramo del giornale la LEFT JOIN della scheda sarebbe
-- vuota, cioe' «si puo' togliere». Una del GIRO (gruppo_key NULL) non conta:
-- li' il verbo non ha oggetto.
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, gruppo_key)
SELECT (SELECT lotto_id FROM t_lotto), 'segnalazione costruita dal test', 'C', g.k
  FROM (VALUES ('PGTAP:azioni-riga-giornale'), (NULL)) g(k);

SELECT is(
    (SELECT count(*) FILTER (WHERE v.gruppo_key IS NOT NULL
                               AND v.uscita_blocco_reason_key IS NOT DISTINCT FROM
                                   (script.fn_check_documento_escludibile_da_giro(s.lotto_id, s.gruppo_key)
                                      -> 0 ->> 'reason_key'))
            || '/' || count(*)
       FROM (SELECT (SELECT lotto_id FROM t_lotto) AS lotto_id, x.gruppo_key
               FROM vendite.fn_list_lotto_segnalazioni(
                        p_lotto_id    => (SELECT lotto_id FROM t_lotto),
                        p_solo_attive => false) x
              WHERE x.gruppo_key IS NOT NULL) s
       LEFT JOIN vendite.vw_lotti_gruppi_azioni v
              ON v.lotto_id = s.lotto_id AND v.gruppo_key = s.gruppo_key),
    '1/1',
    '8) ogni segnalazione che nomina un documento ha la sua riga nella vista, col motivo della fn_check');

SELECT * FROM finish();
ROLLBACK;
