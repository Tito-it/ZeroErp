{% include-markdown "it/dbzero/dbops/manual/fn_seed_primo_impianto_argomenti.md" %}
# ⚙️ Funzione `fn_seed_primo_impianto_argomenti`

```sql
CREATE FUNCTION fn_seed_primo_impianto_argomenti(p_argomenti text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_primo_impianto_argomenti(p_argomenti text[])
 RETURNS TABLE(valido boolean, dettaglio text, forma text, colonne_software text[], colonne_installazione text[], colonne_libere text[])
 LANGUAGE plpgsql
 IMMUTABLE PARALLEL SAFE
AS $function$
-- Scopo: gli argomenti di un trigger del seed di primo impianto
--   letti per nome. Una riga sola; valido = false con il motivo in
--   dettaglio e forma ed elenchi a NULL se il montaggio non rispetta
--   la grammatica. colonne_libere c'e' sempre.
-- Uso: SELECT * FROM dbops.fn_seed_primo_impianto_argomenti(TG_ARGV);
DECLARE
    -- la base dell'array non e' sempre 1 (TG_ARGV parte da 0): una
    -- fetta dell'array riparte da 1
    a      text[] := p_argomenti[array_lower(p_argomenti, 1):array_upper(p_argomenti, 1)];
    v_sw   dbops.automazione_seed_primo_impianto.colonne_software%TYPE;
    v_inst dbops.automazione_seed_primo_impianto.colonne_installazione%TYPE;
    -- text nudo: il motivo di una lettura non valida
    errore text;
BEGIN
    colonne_libere := ARRAY['id', 'meta', 'data_insert', 'user_insert',
                            'data_update', 'user_update', 'tx_id'];

    IF a IS NULL THEN
        a := ARRAY[]::text[];
    END IF;

    IF cardinality(a) >= 3 THEN
        v_sw   := array_remove(string_to_array(regexp_replace(a[2], '\s', '', 'g'), ','), '');
        v_inst := array_remove(string_to_array(regexp_replace(a[3], '\s', '', 'g'), ','), '');
    END IF;

    errore := CASE
        WHEN cardinality(a) = 0 THEN
            'nessun argomento: attesa la forma (RIGA, COLONNA o SOLO_INSERIMENTO)'
        WHEN a[1] IN ('RIGA', 'SOLO_INSERIMENTO') AND cardinality(a) <> 1 THEN
            format('%s argomenti, atteso 1 per la forma %s', cardinality(a), a[1])
        WHEN a[1] = 'COLONNA' AND cardinality(a) <> 3 THEN
            format('%s argomenti, attesi 3 per la forma COLONNA', cardinality(a))
        WHEN a[1] = 'COLONNA' AND (cardinality(v_sw) = 0 OR cardinality(v_inst) = 0) THEN
            'forma COLONNA: i due elenchi devono essere tutti e due non vuoti'
        WHEN a[1] = 'COLONNA' AND v_sw && v_inst THEN
            'forma COLONNA: una colonna sta in tutti e due gli elenchi'
        WHEN a[1] = 'COLONNA' AND (v_sw || v_inst) && colonne_libere THEN
            'forma COLONNA: un elenco nomina una colonna libera'
        WHEN a[1] NOT IN ('RIGA', 'COLONNA', 'SOLO_INSERIMENTO') OR a[1] IS NULL THEN
            format('forma %s sconosciuta: attesa RIGA, COLONNA o SOLO_INSERIMENTO',
                   COALESCE(a[1], 'NULL'))
    END;

    valido                := errore IS NULL;
    dettaglio             := errore;
    forma                 := CASE WHEN errore IS NULL THEN a[1] END;
    colonne_software      := CASE WHEN errore IS NULL AND a[1] = 'COLONNA' THEN v_sw END;
    colonne_installazione := CASE WHEN errore IS NULL AND a[1] = 'COLONNA' THEN v_inst END;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION dbops.fn_seed_primo_impianto_argomenti(p_argomenti text[])
IS 'La grammatica degli argomenti di un trigger su script.trgfn_seed_primo_impianto, letta per nome: [0] la forma (RIGA, COLONNA o SOLO_INSERIMENTO); nella forma COLONNA [1] le colonne del software e [2] quelle dell''installazione, separate da virgola, non vuote, disgiunte e senza colonne libere. Una riga sola: valido = false con il motivo in dettaglio se il montaggio non la rispetta. colonne_libere (id, meta, colonne d''audit, tx_id) c''e'' sempre: sono le colonne che nessun elenco nomina e che non contano per «personalizzata». La leggono il trigger, dbops.fn_seed_primo_impianto_divergenze e il runner. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
