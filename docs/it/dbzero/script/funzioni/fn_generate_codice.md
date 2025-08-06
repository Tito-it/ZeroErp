{% include-markdown "it/dbzero/script/manual/fn_generate_codice.md" %}
# ⚙️ Funzione `fn_generate_codice`

```sql
CREATE FUNCTION fn_generate_codice(tipo text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_generate_codice(tipo text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
  seq_val    BIGINT;
  prefix     TEXT;
  sep        TEXT;
  len        INT;
  seq_name   TEXT;
  risultato  TEXT;
BEGIN
  /*	Crea la funzione generica script.fn_generate_codice(tipo TEXT) che:
        - legge da config.sistema_codici i parametri per quel tipo
        - invoca nextval sul nome di sequenza
        - concatena prefisso, separatore e numero formattato
  */
  SELECT prefisso, separatore, lunghezza_numero, nome_sequenza
    INTO prefix, sep, len, seq_name
    FROM config.sistema_codici
   WHERE codice_tipo = tipo
     AND attivo = TRUE;

  IF seq_name IS NOT NULL THEN
    EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
    risultato := prefix || sep || lpad(seq_val::TEXT, len, '0');
    RETURN risultato;
  ELSE
    -- Se non esiste una sequenza per questo tipo, lancia un errore
       PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'SEQUENZA_NON_CONFIGURATA',
          jsonb_build_object('codice_tipo',tipo),
          NULL::uuid,
          tipo::TEXT
        );
  END IF;
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
