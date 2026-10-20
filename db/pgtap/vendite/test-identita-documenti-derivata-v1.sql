-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c): la tabella della famiglia viene dalla sorgente (config.fn_sorgente_tabella).
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
-- Elenco test (plan 6):
-- 1) ⭐ Il catalogo non e' vuoto e ogni famiglia attiva punta a una tabella vera
-- 2) ⭐⭐ STRUTTURALE: l'identita' di ogni famiglia DISTINGUE L'EMITTENTE
-- 3) ⭐ STRUTTURALE: sul ramo per-registro, dove c'e' `anno` l'unicita' lo contiene
-- 4) ⚠️ DATI: chi e' passato dal motore nuovo porta registro E anno insieme
-- 5) ⛔ DERIVATO: niente `serie_default` sui registri di famiglie senza `serie`
-- 6) ⭐ GEMELLO «esiste»: entrambi i rami dell'identita' sono abitati (2026-09-02)
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
--   deve distinguere due emittenti, e ci sono due forme legittime:
--     * l'indice unico porta `registro_id` — e un registro appartiene a UN
--       emittente (fatture, DDT, ordini, resi);
--     * l'indice unico e' sulla SOLA colonna del numero, e allora l'identita'
--       e' la STRINGA NUDA — unica nell'intera tabella, quindi due emittenti
--       non collidono nemmeno volendo
--       (commessa: `CMM-<sigla>-<anno>-<9 cifre>`).
--   Il test guarda la FORMA DEGLI INDICI, e ne basta una delle due.
--
--   ⛔ 2026-09-02 — E FINO A OGGI LA SCEGLIEVA GUARDANDO LE COLONNE, che e'
--   un proxy e non la proprieta'. Il giorno in cui `vendite.commesse` ha
--   ricevuto `registro_id` e `anno` come DATO — gli assi del contatore, che
--   il codice porta gia' dentro la stringa — il proxy ha cambiato ramo da
--   solo e ha preteso una chiave piu' LARGA di quella che c'era. Il dettaglio
--   sta al test 2: e' il caso da ricordare quando si scrive un presidio che
--   «deriva», perche' derivare dalla cosa sbagliata sembra derivare.
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

SELECT plan(6);

-- ============================================================
-- La base: il catalogo, con la tabella risolta e le colonne che ha
-- ============================================================
-- ⚠️ Si risolve UNA volta e si riusa: ogni test che ricomponesse questa
--   lettura potrebbe farlo in modo leggermente diverso, ed e' cosi' che due
--   presidi sulla stessa regola cominciano a dissentire.
CREATE TEMP TABLE tmp_idd_fam AS
SELECT fd.codice_interno,
       fd.descrizione,
       -- rev 2026-10-20 (2c): la tabella e' quella della sorgente (il BB del guard)
       st.schema_tabella,
       st.nome_tabella,
       fd.colonna_numero,
       st.relid
  FROM vendite.famiglie_documento fd
  LEFT JOIN LATERAL config.fn_sorgente_tabella(fd.codice_interno) st ON true
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

-- ⭐ E una terza per l'altro ramo: «l'identita' e' la STRINGA NUDA».
--   Non basta che un indice unico porti la colonna del numero — un
--   `UNIQUE (billing_account_id, numero)` la porta e lascia collidere due
--   emittenti. Serve che l'indice sia su QUELLA COLONNA E BASTA: allora la
--   stringa e' unica nell'intera tabella, e a maggior ragione fra emittenti.
--   ⚠️ Tre condizioni, e ognuna toglie un modo di non respingere niente:
--     * `indnatts = 1`  -> nessun'altra dimensione allarga la chiave;
--     * NOT NULL (o `indnullsnotdistinct`) -> due vuoti DEVONO collidere. E'
--       il difetto del 2026-08-31 in forma generale: una chiave che ammette
--       due NULL non e' una chiave;
--     * `indpred IS NULL` -> l'indice non e' parziale, quindi vale per TUTTE
--       le righe e non solo per quelle che passano un filtro.
CREATE OR REPLACE FUNCTION pg_temp.idd_unique_stringa_nuda(p_relid oid, p_col text)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
      SELECT 1
        FROM pg_index i
        JOIN pg_attribute a
          ON a.attrelid = p_relid
         AND a.attnum   = i.indkey[0]
         AND NOT a.attisdropped
       WHERE i.indrelid     = p_relid
         AND i.indisunique
         AND i.indnatts     = 1
         AND i.indnkeyatts  = 1
         AND i.indpred IS NULL
         AND a.attname = p_col
         AND (a.attnotnull OR i.indnullsnotdistinct));
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
-- Deve poter succedere, e l'unicita' deve saperlo. Due forme legittime, e ne
-- basta UNA:
--   * l'indice unico porta `registro_id` — e un registro appartiene a UN
--     emittente (fatture, DDT, ordini, resi);
--   * l'indice unico e' sulla SOLA colonna del numero — allora la stringa e'
--     unica nell'intera tabella, quindi due emittenti non possono collidere
--     nemmeno volendo (commessa: `CMM-<sigla>-<anno>-<9 cifre>`).
--
-- ⛔ 2026-09-02 — QUESTO TEST SCEGLIEVA IL RAMO NEL MODO SBAGLIATO, e va
--    raccontato perche' e' il difetto piu' istruttivo del file.
--    Chiedeva: «la tabella HA la colonna `registro_id`? allora l'unicita'
--    deve portarla; altrimenti guarda la stringa». Era un PROXY, non la
--    proprieta': funzionava solo finche' avere quella colonna coincideva con
--    l'avere l'identita' sul registro.
--    Il 2026-09-02 `vendite.commesse` ha ricevuto `registro_id` e `anno` come
--    DATO — gli assi del contatore, prima buttati via dopo aver composto il
--    codice, «non un doppione: il codice li porta dentro una stringa, qui
--    sono dato e si interrogano» (fn_get_or_create_commessa, rev 2026-09-02).
--    Il proxy ha cambiato ramo da solo e ha cominciato a PRETENDERE una
--    chiave `(registro_id, …)` al posto di `uq_commesse_codice` su `(codice)`
--    — cioe' a chiedere una chiave piu' LARGA, non piu' stretta: un
--    peggioramento travestito da rosso.
--    ⭐ La regola vera non e' «quali colonne esistono» ma «l'unicita' impedisce
--    a due emittenti di collidere», e ora e' scritta cosi'. La commessa resta
--    l'unica delle cinque famiglie la cui identita' e' la stringa nuda, ed e'
--    una decisione dichiarata nel corpo di `fn_get_or_create_commessa`, non
--    una particolarita' da tollerare.
SELECT is(
    (SELECT COALESCE(string_agg(f.codice_interno, ', ' ORDER BY f.codice_interno), '')
       FROM tmp_idd_fam f
      WHERE f.relid IS NOT NULL
        AND NOT pg_temp.idd_unique_porta(f.relid, 'registro_id')
        AND NOT pg_temp.idd_unique_stringa_nuda(f.relid, f.colonna_numero)),
    '',
    '2) Ogni famiglia ha un''unicita'' che distingue l''emittente (registro in chiave, o stringa nuda)');

-- ============================================================
-- 3) ⭐ Dove c'e' `anno`, l'unicita' lo contiene
-- ============================================================
-- ⛔ E' esattamente il difetto del 2026-08-31: una colonna `anno` che esiste,
--   che nessuno riempie, e un vincolo che la porta in chiave — quindi non
--   respinge niente, perche' due NULL non collidono. Qui si presidia il primo
--   anello: se l'anno c'e', deve stare nella chiave. Il secondo anello — che
--   sia VALORIZZATO — e' il test 4.
--
-- ⭐ 2026-09-02 — LA REGOLA VALE SUL RAMO PER-REGISTRO, e la condizione e'
--   scritta dal lato POSITIVO: «l'identita' e' sul registro». Non e' uno
--   sconto per la commessa, e' la stessa proprieta' del test 2 letta qui:
--   dove l'identita' e' la STRINGA NUDA l'anno vive gia' DENTRO quella
--   stringa (`CMM-<sigla>-<anno>-<9 cifre>`), quindi l'unicita' lo contiene
--   davvero — solo non come colonna separata. Pretenderlo anche in chiave
--   sarebbe chiedere di ripetere in un indice cio' che la chiave gia' dice,
--   e allargherebbe la chiave invece di stringerla.
--   ⚠️ Il difetto originale resta coperto per intero: DDT, ordini, resi e
--   fatture stanno tutti sul ramo per-registro, che e' dove la colonna `anno`
--   e' una DIMENSIONE della chiave e non un pezzo di testo.
SELECT is(
    (SELECT COALESCE(string_agg(f.codice_interno, ', ' ORDER BY f.codice_interno), '')
       FROM tmp_idd_fam f
      WHERE f.relid IS NOT NULL
        AND pg_temp.idd_unique_porta(f.relid, 'registro_id')
        AND pg_temp.idd_ha_colonna(f.relid, 'anno')
        AND NOT pg_temp.idd_unique_porta(f.relid, 'anno')),
    '',
    '3) Dove l''identita'' e'' sul registro e c''e'' la colonna `anno`, l''unicita'' la contiene');

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

-- ============================================================
-- 6) ⭐ GEMELLO «ESISTE» DELLA BIFORCAZIONE — entrambi i rami sono abitati
-- ============================================================
-- ⚠️ I test 2 e 3 contano i cattivi su due rami diversi, e un ramo VUOTO li
--   rende muti senza farlo vedere: se un giorno nessuna famiglia avesse piu'
--   l'identita' sul registro, il test 3 sarebbe verde perche' non ha piu'
--   niente da guardare — e sarebbe proprio il momento in cui il difetto del
--   2026-08-31 potrebbe rientrare dalla finestra.
-- ⛔ Non si asserisce QUANTE famiglie stanno di qua e di la': sarebbe fissare
--   la fotografia di oggi. Si asserisce che nessuno dei due rami e' vuoto —
--   che e' una proprieta' del presidio, non della popolazione.
SELECT is(
    (SELECT CASE WHEN count(*) FILTER (
                     WHERE pg_temp.idd_unique_porta(f.relid, 'registro_id')) = 0
                 THEN 'RAMO REGISTRO VUOTO ' ELSE '' END
         || CASE WHEN count(*) FILTER (
                     WHERE pg_temp.idd_unique_stringa_nuda(f.relid, f.colonna_numero)) = 0
                 THEN 'RAMO STRINGA NUDA VUOTO' ELSE '' END
       FROM tmp_idd_fam f
      WHERE f.relid IS NOT NULL),
    '',
    '6) Entrambi i rami dell''identita'' sono abitati (i test 2 e 3 hanno candidati)');

SELECT * FROM finish();
ROLLBACK;
