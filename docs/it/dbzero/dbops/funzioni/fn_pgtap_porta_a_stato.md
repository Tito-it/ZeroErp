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
-- Scopo: portare una testata di fixture (ordine, preventivo) nello
--   stato voluto per le transizioni della sua matrice, dopo che il
--   test le ha scritto le righe in bozza.
-- Uso:
--   SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO')
--     FROM tmp_ordine o;
DECLARE
    v_col       text;       -- colonna di stato della testata
    v_stati     regclass;   -- catalogo degli stati
    v_matrice   regclass;   -- matrice delle transizioni
    v_target    bigint;
    v_corrente  bigint;
    v_percorso  bigint[];
    v_passo     bigint;
    v_n         integer;
    v_codice    text;
BEGIN
    -- ── Il documento: errore del CHIAMANTE, non un dato ────────
    IF p_testata = 'vendite.ordini'::regclass THEN
        v_col     := 'stato_doc_ordine_id';
        v_stati   := 'config.stati_doc_ordini'::regclass;
        v_matrice := 'config.transizioni_stati_ordini'::regclass;
    ELSIF p_testata = 'vendite.preventivi'::regclass THEN
        v_col     := 'stato_doc_preventivo_id';
        v_stati   := 'config.stati_doc_preventivi'::regclass;
        v_matrice := 'config.transizioni_stati_preventivi'::regclass;
    ELSE
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: documento non gestito: % (noti: vendite.ordini, vendite.preventivi)',
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
            SELECT t.stato_a_id::bigint, p.percorso || t.stato_a_id::bigint
              FROM p
              JOIN %s t ON t.stato_da_id = p.stato AND t.attivo IS TRUE
              JOIN %s s ON s.id = t.stato_a_id AND s.attivo IS TRUE
             WHERE NOT (t.stato_a_id = ANY (p.percorso))
        )
        SELECT p.percorso FROM p
         WHERE p.stato = $2
         ORDER BY cardinality(p.percorso), p.percorso
         LIMIT 1$q$, v_matrice, v_stati)
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
IS 'Fixture pgTAP: porta una testata di vendite.ordini o vendite.preventivi dallo stato corrente allo stato p_stato (codice_interno) per il percorso piu'' corto della matrice delle transizioni attive (config.transizioni_stati_ordini / _preventivi), un UPDATE della colonna di stato per passo: ogni passo passa dai guard di transizione veri, come in produzione. Serve alla forma «bozza, righe, transizioni»: da 20261008-90/-91 le righe si scrivono solo in bozza, e una testata nata fuori bozza non prende piu'' righe. A parita'' di lunghezza vince il percorso con gli id di stato minori. ⛔ Documento non gestito, stato sconosciuto, percorso assente, testata invisibile o UPDATE che non tocca una riga: eccezione, mai un ritorno silenzioso. Ritorna il codice_interno raggiunto; esce con i vincoli IMMEDIATE. Brief: brief-db-righe-e-componenti-debiti-residui (§1, D-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
