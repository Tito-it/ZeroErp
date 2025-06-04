CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
              BEGIN
		/*	 Se il codice soggetto è null si richiama la funzione per la generazione automatico, 
			il codice sarà generato come indicato nella tabella sistema_codici 
		*/
                IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE' ) AND NEW.soggetto_codice IS NULL THEN
                  NEW.soggetto_codice := script.fn_generate_codice('soggetto');
                END IF;
                RETURN NEW;
              END;
              $$;
