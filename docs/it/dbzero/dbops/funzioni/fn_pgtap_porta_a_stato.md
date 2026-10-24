{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_porta_a_stato.md" %}
# ⚙️ Funzione `fn_pgtap_porta_a_stato`

```sql
CREATE FUNCTION fn_pgtap_porta_a_stato(p_testata regclass, p_id bigint, p_stato text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_porta_a_stato(p_testata regclass, p_id bigint, p_stato text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: portare una testata di fixture nello stato voluto per
--   le transizioni della sua matrice, dopo che il test le ha
--   scritto in bozza cio' che i passaggi pretendono (righe,
--   indirizzi, prezzi…).
-- Uso:
--   SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO')
--     FROM tmp_ordine o;
-- rev 2026-10-24 (20261024-22, brief-modello-documento-vendita
--   N-1): tutte le testate con una matrice, non piu' solo ordine
--   e preventivo. Un documento nasce in bozza (trigger della
--   nascita) e si porta avanti da qui.
-- rev 2026-10-24 (20261024-30, R-4): anche il lotto di
--   fatturazione, VUOTO (con fatture si muove col verbo
--   vendite.fn_sync_lotto_fatture_stato).
DECLARE
    v_col       text;       -- colonna di stato della testata
    v_stati     regclass;   -- catalogo degli stati
    v_matrice   regclass;   -- matrice delle transizioni
    v_col_da    text;       -- colonna «da» della matrice
    v_col_a     text;       -- colonna «a» della matrice
    v_col_vivo  text;       -- colonna «passaggio ammesso» della matrice
    v_filtro    text;       -- condizione in piu' sui passaggi, letterale della mappa
    -- Id e codici di stato di uno qualunque degli otto
    -- vocabolari: bigint e testo in tutti, nessuna colonna
    -- comune a cui ancorarli (%TYPE[] non e' sintassi valida).
    v_target    bigint;
    v_corrente  bigint;
    v_percorso  bigint[];
    v_passo     bigint;
    v_codice    text;
    v_n         integer;    -- righe toccate (ROW_COUNT): un conteggio
BEGIN
    -- ── Il documento: errore del CHIAMANTE, non un dato ────────
    -- ⚠️ La fattura: la matrice ha anche i passaggi del LOTTO
    --   (solo_lotto = true), che il guard della fattura singola
    --   (vendite.trgfn_fatture_guard_stato) non ammette. Il
    --   percorso usa solo quelli che il guard accetta.
    SELECT m.col, m.voc, m.mat, m.da, m.a, m.vivo, m.filtro
      INTO v_col, v_stati, v_matrice, v_col_da, v_col_a, v_col_vivo, v_filtro
      FROM (VALUES
        ('vendite.preventivi'::regclass,          'stato_doc_preventivo_id', 'config.stati_doc_preventivi'::regclass, 'config.transizioni_stati_preventivi'::regclass,  'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.offerte_commerciali'::regclass, 'stato_doc_offerta_id',    'config.stati_doc_offerte'::regclass,    'config.stati_doc_offerte_transizioni'::regclass, 'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.contratti'::regclass,           'stato_doc_contratto_id',  'config.stati_doc_contratti'::regclass,  'config.transizioni_stati_contratti'::regclass,   'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.ordini'::regclass,              'stato_doc_ordine_id',     'config.stati_doc_ordini'::regclass,     'config.transizioni_stati_ordini'::regclass,      'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.ddt'::regclass,                 'stato_doc_ddt_id',        'config.stati_doc_ddt'::regclass,        'config.transizioni_stati_ddt'::regclass,         'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.resi'::regclass,                'stato_doc_reso_id',       'config.stati_doc_reso'::regclass,       'config.transizioni_stati_reso'::regclass,        'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.commesse'::regclass,            'stato_commessa_id',       'vendite.stati_commessa'::regclass,      'vendite.transizioni_stati_commessa'::regclass,   'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.fatture'::regclass,             'stato_doc_fiscale_id',    'config.stati_doc_fiscale'::regclass,    'config.stati_doc_fiscale_transizioni'::regclass, 'stato_from_id', 'stato_to_id', 'ammesso', 'AND t.solo_lotto IS FALSE'),
        ('vendite.fatturazione_lotti'::regclass,  'stato_doc_fiscale_id',    'config.stati_doc_fiscale'::regclass,    'config.stati_doc_fiscale_transizioni'::regclass, 'stato_from_id', 'stato_to_id', 'ammesso', 'AND t.solo_fattura IS FALSE')
      ) AS m(tab, col, voc, mat, da, a, vivo, filtro)
     WHERE m.tab = p_testata;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: documento non gestito: % (noti: le testate di vendita con una matrice dei passaggi)',
            p_testata;
    END IF;

    IF p_id IS NULL OR p_id <= 0 THEN
        RAISE EXCEPTION 'fn_pgtap_porta_a_stato: id testata non valido: %', p_id;
    END IF;

    -- ── Lo stato voluto, per codice_interno ──────────────────
    EXECUTE format('SELECT s.id FROM %s s WHERE s.codice_interno = $1 AND s.attivo IS TRUE',
                   v_stati)
       INTO v_target USING p_stato;
    IF v_target IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: nessuno stato attivo con codice_interno = % in %',
            p_stato, v_stati;
    END IF;

    -- ── Lo stato corrente: la testata deve esserci e vedersi ──
    EXECUTE format('SELECT t.%I FROM %s t WHERE t.id = $1', v_col, p_testata)
       INTO v_corrente USING p_id;
    IF v_corrente IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: % id = % non esiste o non e'' visibile',
            p_testata, p_id;
    END IF;

    -- ── Il percorso piu' corto nella matrice attiva ──────────
    -- ⚠️ Niente cicli: uno stato gia' visitato non si rivisita.
    --   A parita' di lunghezza, gli id minori: un ordine scelto.
    EXECUTE format($q$
        WITH RECURSIVE p(stato, percorso) AS (
            SELECT $1::bigint, ARRAY[$1::bigint]
            UNION ALL
            SELECT t.%2$I::bigint, p.percorso || t.%2$I::bigint
              FROM p
              JOIN %3$s t ON t.%1$I = p.stato AND t.%4$I IS TRUE %6$s
              JOIN %5$s s ON s.id = t.%2$I AND s.attivo IS TRUE
             WHERE NOT (t.%2$I = ANY (p.percorso))
        )
        SELECT p.percorso FROM p
         WHERE p.stato = $2
         ORDER BY cardinality(p.percorso), p.percorso
         LIMIT 1$q$, v_col_da, v_col_a, v_matrice, v_col_vivo, v_stati, v_filtro)
       INTO v_percorso USING v_corrente, v_target;

    IF v_percorso IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: nessun percorso nella matrice % da stato id % a %',
            v_matrice, v_corrente, p_stato;
    END IF;

    -- ── Il cammino: un UPDATE per passo, dai guard veri ──────
    FOREACH v_passo IN ARRAY v_percorso[2:] LOOP
        EXECUTE format('UPDATE %s SET %I = $1 WHERE id = $2', p_testata, v_col)
          USING v_passo, p_id;
        GET DIAGNOSTICS v_n = ROW_COUNT;
        IF v_n <> 1 THEN
            RAISE EXCEPTION
                'fn_pgtap_porta_a_stato: UPDATE di % id = % verso stato id % ha toccato % righe',
                p_testata, p_id, v_passo, v_n;
        END IF;
    END LOOP;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    EXECUTE format('SELECT s.codice_interno FROM %s t JOIN %s s ON s.id = t.%I WHERE t.id = $1',
                   p_testata, v_stati, v_col)
       INTO v_codice USING p_id;
    RETURN v_codice;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_porta_a_stato(p_testata regclass, p_id bigint, p_stato text)
IS 'Fixture pgTAP: porta una testata di vendita dallo stato corrente allo stato p_stato (codice_interno) per il percorso piu'' corto della sua matrice dei passaggi, un UPDATE per passo, sotto i guard veri: le condizioni d''uscita dalla bozza (righe, indirizzi, prezzi…) le scrive prima il test. Testate: preventivo, offerta, contratto, ordine, DDT, reso, commessa, fattura (la fattura con la matrice config.stati_doc_fiscale_transizioni, colonne stato_from_id/stato_to_id/ammesso, e i soli passaggi con solo_lotto = false, quelli che ammette il guard della fattura singola) e il lotto di fatturazione VUOTO (stessa matrice, i soli passaggi con solo_fattura = false; il filtro per tipo_lotto lo applica il guard del lotto, al passo; un lotto con fatture si muove col verbo vendite.fn_sync_lotto_fatture_stato). Restituisce il codice_interno dello stato raggiunto. Un documento nasce solo nello stato iniziale (script.trgfn_doc_stato_iniziale): una fixture che vuole un documento avanti lo crea e lo porta avanti da qui. Errori del chiamante (testata non gestita, id, stato o percorso inesistenti): RAISE EXCEPTION. rev 2026-10-24: tutte le testate (brief-modello-documento-vendita N-1); 20261024-30: il lotto di fatturazione (R-4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
