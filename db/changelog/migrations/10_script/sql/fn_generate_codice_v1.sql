CREATE OR REPLACE FUNCTION script.fn_generate_codice(tipo TEXT)
                RETURNS TEXT
                LANGUAGE plpgsql
                AS $$
              DECLARE
                seq_val    BIGINT;
                prefix     TEXT;
                sep        TEXT;
                len        INT;
                seq_name   TEXT;
                risultato  TEXT;
              BEGIN
/*			   Crea la funzione generica script.fn_generate_codice(tipo TEXT) che:
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
                  RAISE EXCEPTION '%',
                    script.fn_get_messaggio('SEQUENZA_NON_CONFIGURATA', tipo);
                END IF;
              END;
              $$;
