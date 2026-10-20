{% include-markdown "it/dbzero/script/manual/trgfn_componenti_ricalcola_padre.md" %}
# ⚙️ Funzione `trgfn_componenti_ricalcola_padre`

```sql
CREATE FUNCTION trgfn_componenti_ricalcola_padre()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_ricalcola_padre()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- TG_ARGV[0]: schema (es. 'vendite')
    -- TG_ARGV[1]: tab_padre (es. 'preventivi_righe')
    -- TG_ARGV[2]: tab_figli (es. 'preventivi_righe_componenti')
    -- TG_ARGV[3]: col FK figli->padre (es. 'riga_preventivo_id')
    v_riga_padre_id BIGINT;
BEGIN
    -- Legge FK padre dalla riga coinvolta:
    -- OLD per DELETE, NEW per INSERT/UPDATE.
    IF TG_OP = 'DELETE' THEN
        EXECUTE format('SELECT ($1).%I', TG_ARGV[3])
          INTO v_riga_padre_id USING OLD;
    ELSE
        EXECUTE format('SELECT ($1).%I', TG_ARGV[3])
          INTO v_riga_padre_id USING NEW;
    END IF;

    PERFORM script.fn_ricalcola_prezzo_padre_da_componenti(
        TG_ARGV[0], TG_ARGV[1], TG_ARGV[2], TG_ARGV[3],
        v_riga_padre_id
    );

    RETURN NULL;  -- AFTER trigger
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_ricalcola_padre()
IS 'Trigger function AFTER INS/UPD/DLT: ricalcola prezzo_unitario riga padre da SUM figli attivi. TG_ARGV[0]=schema [1]=tab_padre [2]=tab_figli [3]=col_fk_padre. Usata da 5 tabelle *_righe_componenti CASO A.';
```

</div>

---
{% include-markdown "signature-core.md" %}
