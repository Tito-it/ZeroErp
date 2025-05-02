CREATE OR REPLACE FUNCTION anagrafiche.fn_generate_account_code(p_istanza_id integer, p_utility_id integer)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
  seq_val BIGINT;
  prefix  TEXT;
  sep     TEXT;
  len     INT;
  seq_name TEXT;
  tipo    TEXT := 'billing_account';
  new_code TEXT;
BEGIN
  -- Recupera parametri da configurazione
  SELECT prefisso, separatore, lunghezza_numero, nome_sequenza
    INTO prefix, sep, len, seq_name
    FROM config.sistema_codici
   WHERE codice_tipo = tipo AND attivo = TRUE
   LIMIT 1;

  IF seq_name IS NULL THEN
    RAISE EXCEPTION 'Sequenza non configurata per tipo %', tipo;
  END IF;

  -- Genera valore sequenziale
  EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
  new_code := prefix || sep || lpad(seq_val::TEXT, len, '0');

  -- Inserisce record in billing_account
  INSERT INTO anagrafiche.billing_account(
    istanza_id,
    soggetto_ruolo_id,
    utility_id,
    parent_account_id,
    account_code,
    valid_from
  )
  SELECT
    i.id,
    i.soggetto_ruolo_id,
    p_utility_id,
    NULL,
    new_code,
    CURRENT_DATE
  FROM anagrafiche.istanze_utilities i
  WHERE i.id = p_istanza_id;

  RETURN new_code;
END;
$function$
