{% include-markdown "it/dbzero/script/manual/fn_generate_codice.md" %}
# ⚙️ Funzione `fn_generate_codice`

```sql
CREATE FUNCTION fn_generate_codice(tipo text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_generate_codice(tipo text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
  seq_val    BIGINT;
  prefix     config.sistema_codici.prefisso%TYPE;
  sep        config.sistema_codici.separatore%TYPE;
  len        config.sistema_codici.lunghezza_numero%TYPE;
  seq_name   TEXT;
  risultato  TEXT;
  v_context_name text := 'script.fn_generate_codice';
  v_usa_sequenza config.sistema_codici.usa_sequenza%TYPE;
  v_schema_tabella config.sistema_codici.schema_tabella%TYPE;
  v_nome_tabella config.sistema_codici.nome_tabella%TYPE;
  v_nome_colonna config.sistema_codici.nome_colonna%TYPE;
BEGIN
  /*	Crea la funzione generica script.fn_generate_codice(tipo TEXT) che:
        - legge da config.sistema_codici i parametri per quel tipo
        - rispetta il flag usa_sequenza (se false restituisce NULL)
        - richiede la sequenza gia' presente (<schema>.<tabella>_<colonna>_seq)
        - concatena prefisso, separatore e numero formattato
  */
  SELECT prefisso,
         separatore,
         lunghezza_numero,
         usa_sequenza,
         schema_tabella,
         nome_tabella,
         nome_colonna
    INTO prefix,
         sep,
         len,
         v_usa_sequenza,
         v_schema_tabella,
         v_nome_tabella,
         v_nome_colonna
    FROM config.sistema_codici
  WHERE codice_interno = tipo;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
        'database',
        v_context_name,
        'E_SEQUENZA_NON_CONFIGURATA',
        jsonb_build_object('codice_interno',tipo),
        NULL::uuid,
        tipo::TEXT
      );
  END IF;

  IF v_usa_sequenza IS DISTINCT FROM TRUE THEN
    RETURN NULL;
  END IF;

  IF v_schema_tabella IS NULL OR v_nome_tabella IS NULL OR v_nome_colonna IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'database',
        v_context_name,
        'E_SEQUENZA_NON_CONFIGURATA',
        jsonb_build_object('codice_interno',tipo),
        NULL::uuid,
        tipo::TEXT
      );
  END IF;

  seq_name := format('%I.%I_%I_seq', v_schema_tabella, v_nome_tabella, v_nome_colonna);

  IF to_regclass(seq_name) IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'database',
        v_context_name,
        'E_SEQUENZA_NON_CONFIGURATA',
        jsonb_build_object('codice_interno', tipo, 'sequence_name', seq_name),
        NULL::uuid,
        tipo::TEXT
      );
  END IF;

  EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
  risultato := prefix || sep || lpad(seq_val::TEXT, len, '0');
  RETURN risultato;
END;
$function$

COMMENT ON FUNCTION script.fn_generate_codice(tipo text)
IS 'Genera un codice basato su config.sistema_codici. Se usa_sequenza = false restituisce NULL. Richiede sequenza pre-provisionata <schema>.<tabella>_<colonna>_seq.';
```

</div>

---
{% include-markdown "signature-core.md" %}
