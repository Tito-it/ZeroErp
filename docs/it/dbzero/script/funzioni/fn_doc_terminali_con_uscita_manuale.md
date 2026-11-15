{% include-markdown "it/dbzero/script/manual/fn_doc_terminali_con_uscita_manuale.md" %}
# ⚙️ Funzione `fn_doc_terminali_con_uscita_manuale`

```sql
CREATE FUNCTION fn_doc_terminali_con_uscita_manuale(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_terminali_con_uscita_manuale(p_testata regclass)
 RETURNS TABLE(stato text, uscita text)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- ⚠️ Tipi nudi DICHIARATI: p_testata e' una testata qualunque della
--   mappa di script.fn_doc_stato_modello; stato e uscita sono il
--   codice_interno di sette vocabolari diversi.
DECLARE
    m record;
BEGIN
    -- =========================================================
    -- Scopo: le coppie (stato terminale, destinazione) per cui la
    --   matrice della testata ha un passaggio A MANO attivo che esce
    --   da uno stato terminale. Nessuna riga = la configurazione
    --   rispetta terminale (S-1, lettura A).
    -- Regole:
    --   - a mano = meta.manuale vero (dichiarato su ogni riga dal
    --     CHECK ck_*_meta_manuale_dichiarato);
    --   - una riga spenta (colonna di vita falsa) non e' un'uscita;
    --   - il filtro della mappa (le righe di un solo documento in
    --     una matrice condivisa) vale anche qui;
    --   - testata fuori mappa, o vocabolario senza terminale:
    --     E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    SELECT * INTO m FROM script.fn_doc_stato_modello(p_testata);

    IF m.vocabolario IS NULL
       OR NOT EXISTS (SELECT 1
                        FROM pg_catalog.pg_attribute a
                       WHERE a.attrelid = m.vocabolario
                         AND a.attname = 'terminale'
                         AND NOT a.attisdropped) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_terminali_con_uscita_manuale',
            'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_doc_terminali_con_uscita_manuale',
            'p_testata: una testata della mappa (script.fn_doc_stato_modello) il cui vocabolario dichiara la colonna terminale');
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT s.codice_interno::text, sa.codice_interno::text
           FROM %1$s s
           JOIN %2$s t  ON t.%3$I = s.id
           JOIN %1$s sa ON sa.id = t.%4$I
          WHERE s.terminale
            AND t.%5$I IS TRUE
            AND COALESCE((t.meta ->> ''manuale'')::boolean, false)
            %6$s
          ORDER BY 1, 2',
        m.vocabolario, m.matrice, m.colonna_da, m.colonna_a, m.colonna_vivo, m.filtro);
END;
$function$

COMMENT ON FUNCTION script.fn_doc_terminali_con_uscita_manuale(p_testata regclass)
IS 'Gli stati terminali del vocabolario della testata p_testata che hanno un passaggio a mano attivo in uscita, con la destinazione (stato, uscita: codice_interno). Nessuna riga = la configurazione rispetta terminale: da uno stato terminale non esce nessun passaggio a mano. A mano = meta.manuale vero; una riga spenta non conta; il filtro della mappa di script.fn_doc_stato_modello vale anche qui. Implicazione, non equivalenza: uno stato senza uscite a mano puo'' non essere terminale. Una testata fuori mappa, o il cui vocabolario non ha la colonna terminale, solleva E_SCRIPT_CHIAMATA_NON_VALIDA. La usa script.trgfn_doc_terminale_senza_uscita_manuale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
