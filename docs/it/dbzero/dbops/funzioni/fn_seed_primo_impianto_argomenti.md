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
-- Forma FIGLIA: [1] la colonna che porta l'id del padre, [2] il padre
--   come schema.tabella; gli elenchi escono NULL. Colonna e padre li
--   legge il trigger, dopo che questa funzione li ha validati.
-- Forma COLONNA: [1] le colonne del software, [2] quelle
--   dell'installazione, [3] facoltativo, le colonne derivate (un
--   sottoinsieme di [2]: il software non le riporta a OLD). Le derivate
--   le legge il trigger, dopo questa validazione: la firma resta quella
--   che leggono dbops.fn_seed_colonne_del_software e le viste della posta.
-- Gli elenchi li legge dbops.fn_seed_elenco_colonne, la stessa lettura
--   del trigger: un elenco assente e' vuoto, e la forma lo rifiuta.
-- Uso: SELECT * FROM dbops.fn_seed_primo_impianto_argomenti(TG_ARGV);
DECLARE
    -- la base dell'array non e' sempre 1 (TG_ARGV parte da 0): una
    -- fetta dell'array riparte da 1
    a      text[] := p_argomenti[array_lower(p_argomenti, 1):array_upper(p_argomenti, 1)];
    v_sw   dbops.automazione_seed_primo_impianto.colonne_software%TYPE;
    v_inst dbops.automazione_seed_primo_impianto.colonne_installazione%TYPE;
    v_der  dbops.automazione_seed_primo_impianto.colonne_derivate%TYPE;
    -- text nudo: il motivo di una lettura non valida
    errore text;
BEGIN
    colonne_libere := ARRAY['id', 'meta', 'data_insert', 'user_insert',
                            'data_update', 'user_update', 'tx_id'];

    IF a IS NULL THEN
        a := ARRAY[]::text[];
    END IF;

    IF cardinality(a) >= 3 AND a[1] = 'COLONNA' THEN
        v_sw   := dbops.fn_seed_elenco_colonne(a[2]);
        v_inst := dbops.fn_seed_elenco_colonne(a[3]);
    END IF;
    IF cardinality(a) = 4 AND a[1] = 'COLONNA' THEN
        v_der  := dbops.fn_seed_elenco_colonne(a[4]);
    END IF;

    errore := CASE
        WHEN cardinality(a) = 0 THEN
            'nessun argomento: attesa la forma (RIGA, COLONNA, SOLO_INSERIMENTO o FIGLIA)'
        WHEN a[1] IN ('RIGA', 'SOLO_INSERIMENTO') AND cardinality(a) <> 1 THEN
            format('%s argomenti, atteso 1 per la forma %s', cardinality(a), a[1])
        WHEN a[1] = 'COLONNA' AND cardinality(a) NOT IN (3, 4) THEN
            format('%s argomenti, attesi 3 o 4 per la forma COLONNA', cardinality(a))
        WHEN a[1] = 'FIGLIA' AND cardinality(a) <> 3 THEN
            format('%s argomenti, attesi 3 per la forma FIGLIA', cardinality(a))
        WHEN a[1] = 'COLONNA' AND (cardinality(v_sw) = 0 OR cardinality(v_inst) = 0) THEN
            'forma COLONNA: i due elenchi devono essere tutti e due non vuoti'
        WHEN a[1] = 'COLONNA' AND v_sw && v_inst THEN
            'forma COLONNA: una colonna sta in tutti e due gli elenchi'
        WHEN a[1] = 'COLONNA' AND (v_sw || v_inst) && colonne_libere THEN
            'forma COLONNA: un elenco nomina una colonna libera'
        WHEN a[1] = 'COLONNA' AND cardinality(a) = 4 AND cardinality(v_der) = 0 THEN
            'forma COLONNA: il quarto argomento, le colonne derivate, e'' vuoto'
        WHEN a[1] = 'COLONNA' AND cardinality(a) = 4 AND NOT (v_der <@ v_inst) THEN
            'forma COLONNA: una colonna derivata non sta fra quelle dell''installazione'
        WHEN a[1] = 'FIGLIA' AND COALESCE(a[2], '') !~ '^[a-z_][a-z0-9_]*$' THEN
            format('forma FIGLIA: %s non e'' il nome di una colonna', COALESCE(a[2], 'NULL'))
        WHEN a[1] = 'FIGLIA' AND COALESCE(a[3], '') !~ '^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$' THEN
            format('forma FIGLIA: %s non e'' un padre nella forma schema.tabella', COALESCE(a[3], 'NULL'))
        WHEN a[1] NOT IN ('RIGA', 'COLONNA', 'SOLO_INSERIMENTO', 'FIGLIA') OR a[1] IS NULL THEN
            format('forma %s sconosciuta: attesa RIGA, COLONNA, SOLO_INSERIMENTO o FIGLIA',
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
IS 'La grammatica degli argomenti di un trigger su script.trgfn_seed_primo_impianto, letta per nome: [0] la forma (RIGA, COLONNA, SOLO_INSERIMENTO o FIGLIA); nella forma COLONNA [1] le colonne del software e [2] quelle dell''installazione, separate da virgola (lette da dbops.fn_seed_elenco_colonne), non vuote, disgiunte e senza colonne libere, e facoltativo [3] le colonne derivate, un sottoinsieme non vuoto di [2] che il software non riporta a OLD (le legge il trigger dopo questa validazione); nella forma FIGLIA [1] la colonna della figlia che porta l''id del padre e [2] il padre come schema.tabella, e gli elenchi escono NULL (colonna e padre li legge il trigger dopo questa validazione). Una riga sola: valido = false con il motivo in dettaglio se il montaggio non la rispetta. colonne_libere (id, meta, colonne d''audit, tx_id) c''e'' sempre: sono le colonne che nessun elenco nomina e che non contano per «personalizzata». La leggono il trigger, dbops.fn_seed_primo_impianto_divergenze, dbops.fn_seed_colonne_del_software e il runner. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
