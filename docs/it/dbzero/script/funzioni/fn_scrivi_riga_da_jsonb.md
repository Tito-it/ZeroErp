{% include-markdown "it/dbzero/script/manual/fn_scrivi_riga_da_jsonb.md" %}
# ⚙️ Funzione `fn_scrivi_riga_da_jsonb`

```sql
CREATE FUNCTION fn_scrivi_riga_da_jsonb(p_tabella regclass, p_dati jsonb, p_dove jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scrivi_riga_da_jsonb(p_tabella regclass, p_dati jsonb, p_dove jsonb DEFAULT NULL::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_colonne     text;   -- colonne di p_dati, quotate
    v_valori      text;   -- le stesse, lette dal record r
    v_dove_col    text;   -- colonne di p_dove, quotate
    v_dove_val    text;
    v_riga        jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere una riga di p_tabella con le SOLE colonne di
    --   p_dati (valori convertiti da jsonb_populate_record):
    --     * p_dove NULL     -> INSERT; le assenti al DEFAULT;
    --     * p_dove {col: v} -> UPDATE delle righe con quei
    --                          valori; le assenti invariate.
    --   Ritorna la riga scritta (to_jsonb), NULL se l'UPDATE
    --   non trova righe. p_dati vuoto: INSERT DEFAULT VALUES,
    --   oppure nessuna scrittura e la riga com'e'.
    --
    -- Regole:
    --   - le chiavi le sceglie chi chiama (rifiutare o scartare
    --     e' una regola sua): qui ogni chiave e' una colonna;
    --   - UPDATE: una riga. Se p_dove ne individua piu' d'una le
    --     scrive tutte e ritorna la prima: p_dove e' una chiave.
    -- =========================================================
    IF p_tabella IS NULL
       OR p_dati IS NULL OR jsonb_typeof(p_dati) <> 'object'
       OR (p_dove IS NOT NULL
           AND (jsonb_typeof(p_dove) <> 'object' OR p_dove = '{}'::jsonb)) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'script.fn_scrivi_riga_da_jsonb', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tabella',    p_tabella::text,
                               'tipo_dati',  jsonb_typeof(p_dati),
                               'tipo_dove',  jsonb_typeof(p_dove)),
            NULL::uuid,
            'script.fn_scrivi_riga_da_jsonb',
            'tabella, dati o chiave della riga mancanti');
    END IF;

    SELECT string_agg(quote_ident(k), ', ' ORDER BY k),
           string_agg('r.' || quote_ident(k), ', ' ORDER BY k)
      INTO v_colonne, v_valori
      FROM jsonb_object_keys(p_dati) AS k;

    IF p_dove IS NULL THEN
        IF v_colonne IS NULL THEN
            EXECUTE format(
                'INSERT INTO %s AS t DEFAULT VALUES RETURNING to_jsonb(t.*)',
                p_tabella)
               INTO v_riga;
        ELSE
            EXECUTE format(
                'INSERT INTO %s AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::%s, $1) AS r '
                'RETURNING to_jsonb(t.*)',
                p_tabella, v_colonne, v_valori, p_tabella)
               INTO v_riga
              USING p_dati;
        END IF;
        RETURN v_riga;
    END IF;

    SELECT string_agg('t.' || quote_ident(k), ', ' ORDER BY k),
           string_agg('w.' || quote_ident(k), ', ' ORDER BY k)
      INTO v_dove_col, v_dove_val
      FROM jsonb_object_keys(p_dove) AS k;

    IF v_colonne IS NULL THEN
        EXECUTE format(
            'SELECT to_jsonb(t.*) FROM %s AS t, jsonb_populate_record(NULL::%s, $1) AS w '
            'WHERE ROW(%s) = ROW(%s)',
            p_tabella, p_tabella, v_dove_col, v_dove_val)
           INTO v_riga
          USING p_dove;
    ELSE
        -- ROW(...) anche con una colonna sola.
        EXECUTE format(
            'UPDATE %s AS t SET (%s) = ROW(%s) '
            '  FROM jsonb_populate_record(NULL::%s, $1) AS r, '
            '       jsonb_populate_record(NULL::%s, $2) AS w '
            ' WHERE ROW(%s) = ROW(%s) '
            'RETURNING to_jsonb(t.*)',
            p_tabella, v_colonne, v_valori, p_tabella, p_tabella,
            v_dove_col, v_dove_val)
           INTO v_riga
          USING p_dati, p_dove;
    END IF;

    RETURN v_riga;
END;
$function$

COMMENT ON FUNCTION script.fn_scrivi_riga_da_jsonb(p_tabella regclass, p_dati jsonb, p_dove jsonb)
IS 'BB (2026-10-17): scrive una riga di p_tabella con le SOLE colonne di p_dati, valori convertiti da jsonb_populate_record sul tipo di riga. p_dove NULL: INSERT, le colonne assenti al DEFAULT (p_dati vuoto: DEFAULT VALUES). p_dove {colonna: valore, ...}: UPDATE delle righe con quei valori, le colonne assenti invariate (p_dati vuoto: nessuna scrittura, ritorna la riga). Ritorna la riga scritta (to_jsonb), NULL se l''UPDATE non trova righe. Le chiavi le sceglie chi chiama: ogni chiave deve essere una colonna (rifiutare o scartare quelle estranee e'' una regola del chiamante). I trigger della tabella scattano come sempre. INVOKER. Chiamata malformata: E_SCRIPT_CHIAMATA_NON_VALIDA. Regola del 2: prende il posto delle copie in config.fn_pannello_scrivi (passo 3) e vendite.fn_create_contratto (passi 3 e 4). Brief: brief-db-processi-accensione-per-ambiente (2b-1).';
```

---
{% include-markdown "signature-core.md" %}
