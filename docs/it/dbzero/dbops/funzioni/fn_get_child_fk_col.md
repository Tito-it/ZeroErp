{% include-markdown "it/dbzero/dbops/manual/fn_get_child_fk_col.md" %}
# ⚙️ Funzione `fn_get_child_fk_col`

```sql
CREATE FUNCTION fn_get_child_fk_col(p_conoid oid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_child_fk_col(p_conoid oid)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_child_oid oid;
    v_col smallint;
    v_name text;
  BEGIN
    SELECT c.conrelid, c.conkey[1] INTO v_child_oid, v_col
    FROM pg_constraint c
    WHERE c.oid = p_conoid;

    SELECT a.attname INTO v_name
    FROM pg_attribute a
    WHERE a.attrelid = v_child_oid
      AND a.attnum   = v_col;

    RETURN v_name;
  END;
  $function$

COMMENT ON FUNCTION dbops.fn_get_child_fk_col(p_conoid oid)
IS '
  Ritorna il **nome della colonna figlia** (lato *child*) coinvolta in un
  vincolo di **foreign key** identificato dall’OID del vincolo
  (`pg_constraint.oid`).

  • **Ritorno**: `text` — Nome della colonna (`pg_attribute.attname`) sul
    lato child. Restituisce **NULL** se l’OID non corrisponde ad alcun vincolo
    o se non è possibile risalire alla colonna.

  • **Parametro**
    - `p_conoid oid`: OID del vincolo in `pg_constraint`.

  • **Logica**
    - Legge da `pg_constraint` il `conrelid` (tabella child) e l’indice della
      prima colonna `conkey[1]`.
    - Risale a `pg_attribute` per ottenere `attname` della colonna child.

  • **Casi d’uso**
    - Utility nei processi di automazione per derivare il nome della colonna
      figlia partendo dal vincolo FK (es. generazione trigger/validation).

  • **Note**
    - La funzione considera **solo la prima colonna** della FK:
      per vincoli **composti** restituisce la colonna in posizione 1.
      Estensioni future potrebbero esporre **tutte** le colonne
      (es. funzione che ritorna `text[]`).
    - Non applica filtri su colonne “dropped”; qualora necessario, valutare
      l’uso di `a.attisdropped = false`.
    - La funzione è di fatto **STABLE** (consulta soli cataloghi di sistema).

  ';
```

</div>

---
{% include-markdown "signature-core.md" %}
