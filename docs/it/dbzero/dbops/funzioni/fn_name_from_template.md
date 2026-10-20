{% include-markdown "it/dbzero/dbops/manual/fn_name_from_template.md" %}
# ⚙️ Funzione `fn_name_from_template`

```sql
CREATE FUNCTION fn_name_from_template(p_template text, p_schema text, p_table text, p_parent text, p_child text, p_fk text, p_op text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_name_from_template(p_template text, p_schema text, p_table text, p_parent text DEFAULT NULL::text, p_child text DEFAULT NULL::text, p_fk text DEFAULT NULL::text, p_op text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
  DECLARE
    s text;
    h6 text := CASE WHEN p_fk IS NOT NULL AND length(p_fk)>0
                THEN substr(to_hex(hashtextextended(p_fk,0)),1,6) ELSE '' END;
    s_no_if text;
  BEGIN
    -- ----------------------------------------------
    --  p_template → stringa modello, può contenere placeholder come 
    --  {schema}, {table}, {parent}, {child}, {fk}, {op}.
    --       es. {schema}.{table} → {schema}.{table}
    --   p_schema → nome dello schema di destinazione.
    --   p_table → nome della tabella di destinazione.
    --   p_parent → nome della tabella padre (per FK).
    --   p_child → nome della tabella figlia (per FK).
    --   p_fk → nome della foreign key.
    --    p_op → operazione (INS, UPD, DEL, ecc.).
    ----------------------------------------------

    --s := p_template;
    s  := COALESCE(p_template, '{table}');
   

    s := replace(s, '{schema}', COALESCE(p_schema,''));
    s := replace(s, '{table}',  COALESCE(p_table,''));
    s := replace(s, '{parent}', COALESCE(p_parent,''));
    s := replace(s, '{child}',  COALESCE(p_child,''));
    s := replace(s, '{fk}',     COALESCE(p_fk,''));
    s := replace(s, '{op}',     COALESCE(p_op,''));
  
    -- hash sempre (se presente nel template esplicito)
    s := replace(s,'{fkhash6}',h6);

    -- hash solo se il nome è lungo
    IF position('{fkhash6_if_long}' IN s) > 0 THEN
      s_no_if := replace(s,'{fkhash6_if_long}','');
      IF length(s_no_if) > 63 THEN
        s := replace(s,'{fkhash6_if_long}',h6);
      ELSE
        s := s_no_if;
      END IF;
    END IF;

    -- elimina i doppi underscore 
    s:= regexp_replace(s, '_{2,}', '_', 'g');
    s := regexp_replace(s, '^_+|_+$', '', 'g');

     -- guard 63 char con hash consistente
    IF length(s) > 63 THEN
      s := left(s, 63-1-6) || '_' || substr(to_hex(hashtextextended(s,0)), 1, 6);
    END IF;

    RETURN s;
  END;
  $function$

COMMENT ON FUNCTION dbops.fn_name_from_template(p_template text, p_schema text, p_table text, p_parent text, p_child text, p_fk text, p_op text)
IS 'Questa funzione ha lo scopo di generare in modo dinamico un nome di oggetto (trigger, funzione, ecc.) 
    a partire da un template parametrico, garantendo che:
    1)I segnaposto nel template vengano sostituiti con i valori reali di schema, tabella, parent, child, 
    chiave esterna o operazione.
    2)   Il nome finale non superi il limite di PostgreSQL (63 caratteri): in caso di overflow
     viene troncato e completato con un digest hash per assicurare l’univocità.';
```

</div>

---
{% include-markdown "signature-core.md" %}
