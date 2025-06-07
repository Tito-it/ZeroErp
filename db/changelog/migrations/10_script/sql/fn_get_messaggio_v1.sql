-- FUNCTION: script.fn_get_messaggio(text, text, text)
-- DROP FUNCTION IF EXISTS script.fn_get_messaggio(text, text, text);
-- Restituisce il testo messaggio
-- ========================================================================
-- FUNCTION: script.fn_get_messaggio(
--              p_codice Text,
--              p_lingua text DEFAULT 'it',
--    VARIADIC p_valori text[]  -- array contenente tutti i placeholder
--
-- Viene recupearto il messaggio se non esiste si rimanda l'errore "messaggio non definito " , 
-- se esiste vengono sotituiti tutti gli eventuali placeholder con l'array
-- ====================================================================


CREATE OR REPLACE FUNCTION script.fn_get_messaggio(
	p_codice text,
	p_valore text DEFAULT NULL::text,
	p_lingua text DEFAULT 'it'::text)
    RETURNS text
    LANGUAGE 'plpgsql'
    COST 100
    IMMUTABLE PARALLEL UNSAFE
AS $BODY$
DECLARE
  tmpl TEXT;
BEGIN


  SELECT messaggio INTO tmpl
    FROM config.messaggi_errore
   WHERE codice = p_codice
     AND lingua = p_lingua;

  IF tmpl IS NULL THEN
    RETURN '[MESSAGGIO NON DEFINITO: ' || p_codice || ']';
  END IF;

  IF p_valore IS NOT NULL THEN
    RETURN REPLACE(tmpl, '%', p_valore);
  ELSE
    RETURN tmpl;
  END IF;
END;
$BODY$;

COMMENT ON FUNCTION script.fn_get_messaggio(text, text, text)
    IS 'Restituisce il messaggio formattato per codice, valore e lingua. Vengono sostituiti tutti i placeholder';