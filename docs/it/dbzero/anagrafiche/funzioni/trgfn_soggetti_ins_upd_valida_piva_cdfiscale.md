# Funzione `trgfn_soggetti_ins_upd_valida_piva_cdfiscale`

```sql
CREATE FUNCTION trgfn_soggetti_ins_upd_valida_piva_cdfiscale()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_valida_piva_cdfiscale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    l_codice_iso2 TEXT;
BEGIN

-- Verifica P.iva/cd.fiscale Italia
-- tipo_soggetto ='X' il codice fiscale non viene controllato
    SELECT codice_iso2
    INTO STRICT l_codice_iso2
    FROM config.stati
    WHERE id = NEW.stato_id;

    IF l_codice_iso2 = 'IT' THEN
        -- Partita IVA: se è valorizzata e non è valida, solleva errore
		IF NEW.partita_iva IS NOT NULL
		   AND NOT script.fn_valida_partita_iva(NEW.partita_iva)
		THEN
		    RAISE EXCEPTION '%',
		      script.fn_get_messaggio('PIVA_NON_VALIDA', NEW.partita_iva);
		END IF;
		-- Partita IVA Gruppo Acquisto: se è valorizzata e non è valida, solleva errore
		IF NEW.piva_gruppo_acquisto IS NOT NULL
		   AND NOT script.fn_valida_partita_iva(NEW.piva_gruppo_acquisto)
		THEN
		    RAISE EXCEPTION '%',
		      script.fn_get_messaggio('PIVA_NON_VALIDA', NEW.piva_gruppo_acquisto);
		END IF;
		
		-- Codice fiscale: se è valorizzato, tipo_soggetto ≠ 'X' e non è valido, solleva errore
		IF NEW.codice_fiscale IS NOT NULL
		   AND NEW.tipo_soggetto <> 'X'
		   AND NOT script.fn_valida_codice_fiscale(NEW.codice_fiscale)
		THEN
		    RAISE EXCEPTION '%',
		      script.fn_get_messaggio('CF_NON_VALIDO', NEW.codice_fiscale);
		END IF;

    END IF;

    RETURN NEW;
END;
$function$
```