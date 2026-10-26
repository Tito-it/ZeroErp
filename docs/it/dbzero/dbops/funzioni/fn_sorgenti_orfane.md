{% include-markdown "it/dbzero/dbops/manual/fn_sorgenti_orfane.md" %}
# ⚙️ Funzione `fn_sorgenti_orfane`

```sql
CREATE FUNCTION fn_sorgenti_orfane()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sorgenti_orfane()
 RETURNS TABLE(tabella regclass, riga_id bigint, sorgente_tipo_id bigint, sorgente_codice_interno character varying, sorgente_riga bigint, sorgente_uid text, target_table regclass)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: le righe la cui sorgente (tipo + chiave) punta a un record del
--   target_table che non c'e' piu' (D-9). Il guard tipizzato impedisce di
--   INSERIRLE; questa funzione trova quelle rimaste orfane DOPO, cancellando il
--   bersaglio — la FK non c'e' e non puo' esserci. Per ogni tabella del
--   perimetro e per ogni sorgente_tipo_id presente, un anti-join dinamico
--   verso target_table sulla chiave che key_selector dichiara (id | uid).
-- DEFINER del PROPRIETARIO (attraversa la RLS: un orfano in una tabella
--   protetta va visto comunque), STABLE: legge e basta. I nomi di tabella e
--   colonna vengono dal catalogo (regclass, %I): mai da un input.
-- ⚠️ rev 18-09: il ciclo interno legge TRE SCALARI TIPIZZATI, non un record.
--   Un `record` riempito da SQL DINAMICO ha tupla indeterminata per
--   plpgsql_check: ogni campo letto dopo e' «non ancora assegnato» (55000) e
--   il presidio dei riferimenti morti lo riferisce REALE. Con i tipi
--   dichiarati (%TYPE su config.sorgenti) il controllo sa cosa legge.
--   `v_t` resta un record: viene da un SELECT statico, le colonne si sanno.
DECLARE
    v_t             record;
    v_tipo_id       config.sorgenti.id%TYPE;
    v_key_selector  config.sorgenti.key_selector%TYPE;
    v_target_table  config.sorgenti.target_table%TYPE;
BEGIN
    FOR v_t IN SELECT * FROM dbops.fn_sorgenti_orfane_perimetro() LOOP
        -- Per ogni tipo di sorgente presente nella tabella: il bersaglio e la
        -- chiave dichiarati a catalogo (regclass e key_selector).
        FOR v_tipo_id, v_key_selector, v_target_table IN
            EXECUTE format(
                'SELECT DISTINCT s.id, s.key_selector, s.target_table '
                '  FROM %1$s x JOIN config.sorgenti s ON s.id = x.%2$I '
                ' WHERE s.target_table IS NOT NULL',
                v_t.tabella, v_t.col_tipo)
        LOOP
            -- La chiave: uid -> t.uid = x.sorgente_uid; altrimenti t.id = x.sorgente_riga.
            -- Scelta QUI, non in un CASE SQL: il bersaglio potrebbe non avere uid.
            -- Confronto su ::text: non tutte le tabelle del perimetro tipizzano
            -- sorgente_uid come uuid (vendite ne ha di text).
            RETURN QUERY EXECUTE format(
                $q$
                SELECT %1$L::regclass, x.id::bigint, s.id, s.codice_interno,
                       x.%2$I::bigint, x.%3$I::text, s.target_table
                  FROM %1$s x
                  JOIN config.sorgenti s ON s.id = x.%4$I
                 WHERE x.%4$I = %5$L
                   AND x.%6$I IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM %7$s t WHERE t.%8$I::text = x.%6$I::text)
                $q$,
                v_t.tabella::text, v_t.col_riga, v_t.col_uid, v_t.col_tipo, v_tipo_id,
                CASE WHEN v_key_selector = 'uid' THEN v_t.col_uid ELSE v_t.col_riga END,
                v_target_table::text,
                CASE WHEN v_key_selector = 'uid' THEN 'uid' ELSE 'id' END);
        END LOOP;
    END LOOP;
    RETURN;
END;
$function$

COMMENT ON FUNCTION dbops.fn_sorgenti_orfane()
IS 'Le righe la cui SORGENTE (sorgente_tipo_id + sorgente_riga | sorgente_uid) punta a un record di config.sorgenti.target_table che non esiste piu'' (D-9, aggancio 8-quater). Perimetro derivato dal vincolo (fn_sorgenti_orfane_perimetro: FK verso config.sorgenti + le due colonne di chiave), anti-join dinamico per tabella e per tipo sulla chiave che key_selector dichiara (id | uid). Il guard tipizzato del Lotto 1 impedisce di inserire un orfano; qui si trovano quelli creati dopo, cancellando il bersaglio — la FK non c''e'' e non puo'' esserci. SECURITY DEFINER del PROPRIETARIO, non di un superuser (attraversa la RLS), STABLE. Letta da dbops.vw_sorgenti_orfane, che deve restare vuota. ⚠️ rev 18-09 (20260918-27): il ciclo interno legge tre scalari con %TYPE su config.sorgenti e non un record — un record riempito da SQL dinamico ha tupla indeterminata per plpgsql_check, e il presidio dei riferimenti morti (test-riferimenti-morti-v1) lo riferiva REALE (55000 sul RETURN QUERY). Chi tocca questa funzione tenga la forma: la regola vale per ogni FOR ... IN EXECUTE. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
