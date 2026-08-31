-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test 4 conta documenti su tabelle con la RLS accesa
--   (vendite.fatture, vendite.commesse). Da dentro un perimetro un documento
--   rotto di un ALTRO emittente sarebbe invisibile, e il conteggio direbbe
--   «nessun difetto» proprio nel caso da segnalare: uno zero fail-open.
--   ⚠️ I test 1, 2, 3 e 5 sono strutturali e girerebbero da chiunque —
--   restano qui perche' il file e' uno.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra.
-- pgTAP test per Zero ERP
-- Test: L'IDENTITA' DEI DOCUMENTI, derivata dal catalogo delle famiglie
--       vendite.famiglie_documento  (20260830-13)
--       Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §6
-- ------------------------------------------------------------
-- Elenco test (plan 5):
-- 1) ⭐ Il catalogo non e' vuoto e ogni famiglia attiva punta a una tabella vera
-- 2) ⭐⭐ STRUTTURALE: l'identita' di ogni famiglia DISTINGUE L'EMITTENTE
-- 3) ⭐ STRUTTURALE: dove esiste la colonna `anno`, l'unicita' la contiene
-- 4) ⚠️ DATI: chi e' passato dal motore nuovo porta registro E anno insieme
-- 5) ⛔ DERIVATO: niente `serie_default` sui registri di famiglie senza `serie`
--
-- ⛔ COSA NON C'E', E PERCHE': non esiste un test «dove c'e' la colonna `serie`
--   l'unicita' la contiene». E' stato scritto il 2026-08-31 ed e' stato TOLTO
--   il giorno stesso, perche' asseriva una regola che non esiste: la serie
--   EFFETTIVA di un documento e' COALESCE(documento.serie, registro.serie_default,
--   ''), cioe' la colonna e' un OVERRIDE del registro, non una dimensione
--   autonoma dell'identita'. Con `registro_id` gia' in chiave, metterci anche
--   la serie e' una scelta per-documento — la fattura non la mette, e la sua
--   chiave risulta piu' STRETTA, non piu' larga. Nessun buco.
--
-- Scopo:
--   ⛔ IL DIFETTO CHE QUESTO FILE ESISTE PER INTERCETTARE E' MUTO. Fino al
--   2026-08-31 `uq_ddt_v_anno_serie_numero` era su (anno, serie, numero) e
--   `anno` era vuoto su OGNI riga: in SQL due valori vuoti non collidono mai,
--   quindi quel vincolo NON RESPINGEVA NIENTE. Nessun errore, nessun sintomo,
--   nessun modo di accorgersene guardando il sistema funzionare. Lo stesso su
--   resi e ordini: tre documenti su quattro, e per mesi.
--   ⇒ Un difetto cosi' non lo trova chi usa il programma. Lo trova solo chi
--   scrive il test che lo cerca.
--
--   ⭐⭐ E IL PRESIDIO NON ELENCA LE TABELLE: le legge da
--   vendite.famiglie_documento. Ne discende la proprieta' che vale l'intero
--   file — il giorno in cui si registra la SESTA famiglia, questo test la
--   controlla da se', e nessuno deve ricordarsi di venire ad aggiungerla.
--   E' lo stesso principio con cui il presidio sul cambio emittente del
--   billing account si deriva invece di copiarsi.
--
--   ⭐ LA BIFORCAZIONE E' DERIVATA, NON SCRITTA. L'identita' di un documento
--   deve distinguere due emittenti, e ci sono due modi legittimi:
--     * la chiave porta `registro_id` — e un registro appartiene a UN
--       emittente (fatture, DDT, ordini, resi);
--     * la tabella quella colonna non ce l'ha, e allora l'identita' e' la
--       STRINGA NUDA, che porta la sigla dell'emittente dentro di se'
--       (commessa: `CMM-<sigla>-<anno>-<progressivo>`).
--   Il test sceglie il ramo guardando `pg_attribute`, non un elenco.
--
--   ⚠️ IL TEST 4 GUARDA I DATI, E DA SOLO NON BASTEREBBE: su una tabella
--   vuota non trova cattivi e passa — e' il difetto del «test che conta i
--   cattivi e diventa muto». Per questo il presidio VERO sono il 2 e il 3,
--   che guardano la STRUTTURA: valgono a database vuoto, valgono in CI, e
--   diventano rossi il giorno prima che esista il primo documento sbagliato.
--   Il 4 resta come complemento, per i dati gia' sporchi che la struttura non
--   vede.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che il numero sia GIUSTO. Prova che
--   l'identita' e' ben formata e che il vincolo che la presidia esiste
--   davvero. Il numero giusto e' di
--   db/pgtap/vendite/test-documenti-numerazione-trasloco-v1.sql.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- La base: il catalogo, con la tabella risolta e le colonne che ha
-- ============================================================
-- ⚠️ Si risolve UNA volta e si riusa: ogni test che ricomponesse questa
--   lettura potrebbe farlo in modo leggermente diverso, ed e' cosi' che due
--   presidi sulla stessa regola cominciano a dissentire.
CREATE TEMP TABLE tmp_idd_fam AS
SELECT fd.codice_interno,
       fd.descrizione,
       fd.schema_tabella,
       fd.nome_tabella,
       fd.colonna_numero,
       to_regclass(format('%I.%I', fd.schema_tabella, fd.nome_tabella)) AS relid
  FROM vendite.famiglie_documento fd
 WHERE fd.attivo;

-- ⭐ Una funzione sola per «questa tabella ha questa colonna?»: la stessa
--   domanda fatta in piu' punti deve avere una sede sola.
CREATE OR REPLACE FUNCTION pg_temp.idd_ha_colonna(p_relid oid, p_col text)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM pg_attribute a
                  WHERE a.attrelid = p_relid
                    AND a.attname  = p_col
                    AND a.attnum   > 0
                    AND NOT a.attisdropped);
$$;

-- ⭐ E una sola per «esiste un indice UNIQUE che porta questa colonna?».
--   ⚠️ Si guarda `indisunique` e non il NOME del vincolo: un presidio che
--   cercasse `uq_<tabella>_...` misurerebbe una convenzione di nomenclatura,
--   non l'unicita'.
CREATE OR REPLACE FUNCTION pg_temp.idd_unique_porta(p_relid oid, p_col text)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
      SELECT 1
        FROM pg_index i
        JOIN pg_attribute a
          ON a.attrelid = p_relid
         AND a.attname  = p_col
         AND a.attnum   > 0
         AND NOT a.attisdropped
       WHERE i.indrelid = p_relid
         AND i.indisunique
         AND a.attnum = ANY (i.indkey::int2[]));
$$;

-- ============================================================
-- 1) ⭐ Il catalogo non e' vuoto, e ogni famiglia punta a una tabella vera
-- ============================================================
-- ⛔ E' il gemello anti-muto di tutto il file: se il catalogo si svuotasse,
--   i test 2..5 non troverebbero niente da controllare e passerebbero tutti.
--   Un presidio che diventa verde perche' non ha piu' niente da guardare e'
--   peggio di nessun presidio.
SELECT is(
    (SELECT COALESCE(string_agg(f.codice_interno, ', ' ORDER BY f.codice_interno), '')
       FROM tmp_idd_fam f
      WHERE f.relid IS NULL)
    || CASE WHEN (SELECT count(*) FROM tmp_idd_fam) = 0
            THEN 'CATALOGO VUOTO' ELSE '' END,
    '',
    '1) Il catalogo delle famiglie non e'' vuoto e ogni riga attiva punta a una tabella reale');

-- ============================================================
-- 2) ⭐⭐ L'IDENTITA' DISTINGUE L'EMITTENTE
-- ============================================================
-- La domanda: due emittenti possono avere lo stesso numero senza collidere?
-- Deve poter succedere, e l'unicita' deve saperlo. Due modi legittimi, e il
-- test sceglie da se' quale si applica:
--   * la tabella ha `registro_id` -> l'indice unico deve portarlo;
--   * non ce l'ha -> l'identita' e' la stringa nuda, e l'indice unico deve
--     portare la colonna del numero (dentro cui vive la sigla dell'emittente).
SELECT is(
    (SELECT COALESCE(string_agg(f.codice_interno, ', ' ORDER BY f.codice_interno), '')
       FROM tmp_idd_fam f
      WHERE f.relid IS NOT NULL
        AND NOT pg_temp.idd_unique_porta(
                f.relid,
                CASE WHEN pg_temp.idd_ha_colonna(f.relid, 'registro_id')
                     THEN 'registro_id'
                     ELSE f.colonna_numero
                END)),
    '',
    '2) Ogni famiglia ha un''unicita'' che distingue l''emittente (registro in chiave, o stringa nuda)');

-- ============================================================
-- 3) ⭐ Dove c'e' `anno`, l'unicita' lo contiene
-- ============================================================
-- ⛔ E' esattamente il difetto del 2026-08-31: una colonna `anno` che esiste,
--   che nessuno riempie, e un vincolo che la porta in chiave — quindi non
--   respinge niente, perche' due NULL non collidono. Qui si presidia il primo
--   anello: se l'anno c'e', deve stare nella chiave. Il secondo anello — che
--   sia VALORIZZATO — e' il test 5.
SELECT is(
    (SELECT COALESCE(string_agg(f.codice_interno, ', ' ORDER BY f.codice_interno), '')
       FROM tmp_idd_fam f
      WHERE f.relid IS NOT NULL
        AND pg_temp.idd_ha_colonna(f.relid, 'anno')
        AND NOT pg_temp.idd_unique_porta(f.relid, 'anno')),
    '',
    '3) Dove la tabella ha la colonna `anno`, l''unicita'' la contiene');

-- ============================================================
-- 4) ⚠️ I DATI: chi e' passato dal motore nuovo porta registro E anno
-- ============================================================
-- ⚠️ Complemento, non presidio: su una tabella vuota non trova cattivi e
--   passa. Il presidio sono il 2 e il 3, che guardano la struttura.
--
-- ⛔ LA CONDIZIONE «HA IL REGISTRO» NON E' UNO SCONTO, E' LA REGOLA.
--   I documenti numerati PRIMA del trasloco del 2026-08-31 non hanno ne'
--   registro ne' anno, e non li avranno mai: «nessuna rinumerazione del
--   pregresso, per nessun numeratore» e' una decisione del cantiere, non una
--   dimenticanza. Un test che li contasse sarebbe rosso PER SEMPRE — e un
--   presidio che nasce rosso non lo guarda piu' nessuno.
--   ⇒ La regola vera e': chi ha preso il numero dal motore nuovo — e lo si
--   riconosce perche' HA il registro — deve portare anche l'anno. Chi il
--   registro non ce l'ha e' storia, e si dichiara come tale.
-- ⚠️ SQL dinamico: le tabelle vengono dal catalogo e passano da %I.
CREATE TEMP TABLE tmp_idd_rotti (famiglia text, componente text, quante bigint);

DO $$
DECLARE
    f   record;
    c   text;
    n   bigint;
BEGIN
    FOR f IN SELECT * FROM tmp_idd_fam WHERE relid IS NOT NULL LOOP
        -- ⚠️ `registro_id` non si controlla piu': e' il DISCRIMINANTE fra il
        --   motore nuovo e il pregresso, quindi chiederne la presenza
        --   escluderebbe per costruzione le righe che si vogliono trovare.
        CONTINUE WHEN NOT pg_temp.idd_ha_colonna(f.relid, 'registro_id');

        FOREACH c IN ARRAY ARRAY['anno'] LOOP
            CONTINUE WHEN NOT pg_temp.idd_ha_colonna(f.relid, c);

            EXECUTE format(
                'SELECT count(*) FROM %I.%I d'
                || ' WHERE d.%I IS NOT NULL'
                || '   AND btrim(d.%I::text) <> $1'
                -- ⛔ Il pregresso resta fuori, e si riconosce da qui.
                || '   AND d.registro_id IS NOT NULL'
                || '   AND d.%I IS NULL',
                f.schema_tabella, f.nome_tabella,
                f.colonna_numero, f.colonna_numero, c)
              INTO n
             USING ''::text;

            IF n > 0 THEN
                INSERT INTO tmp_idd_rotti VALUES (f.codice_interno, c, n);
            END IF;
        END LOOP;
    END LOOP;
END;
$$;

SELECT is(
    (SELECT COALESCE(
                string_agg(r.famiglia || '.' || r.componente || '=' || r.quante,
                           ', ' ORDER BY r.famiglia, r.componente), '')
       FROM tmp_idd_rotti r),
    '',
    '4) Ogni documento numerato SUL REGISTRO porta anche l''anno');

-- ============================================================
-- 5) ⛔ DERIVATO: niente `serie_default` dove la `serie` non ha casa
-- ============================================================
-- ⚠️ Il contatore porta SEMPRE la serie in chiave, ma non tutte le tabelle
--   hanno una colonna dove scriverla: vendite.resi non ce l'ha. Un registro
--   con `serie_default` valorizzato farebbe girare il numero su una serie che
--   il documento non puo' raccontare — e la sua UNIQUE non la conterrebbe.
-- ⭐ La regola e' DERIVATA e non nominata: non dice «i registri RESO», dice
--   «i registri delle famiglie la cui tabella non ha la colonna serie». Una
--   famiglia nuova con lo stesso difetto entra nel presidio da sola.
SELECT is(
    (SELECT COALESCE(string_agg(DISTINCT r.codice::text, ', '), '')
       FROM vendite.registri_fatturazione r
       JOIN tmp_idd_fam f ON f.codice_interno = r.famiglia_documento
      WHERE r.attivo
        AND f.relid IS NOT NULL
        AND COALESCE(btrim(r.serie_default), '') <> ''
        AND NOT pg_temp.idd_ha_colonna(f.relid, 'serie')),
    '',
    '5) Nessun registro porta una serie_default che il suo documento non puo'' raccontare');

SELECT * FROM finish();
ROLLBACK;
