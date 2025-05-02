CREATE OR REPLACE FUNCTION script.fn_valida_partita_iva(piva text)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    i INT;
    somma INT := 0;
    cifra INT;
    doppio INT;
    check_digit INT;
BEGIN
    -- Controllo base
    IF piva IS NULL OR LENGTH(piva) <> 11 OR piva ~ '[^0-9]' THEN
        RETURN FALSE;
    END IF;

    FOR i IN 1..10 LOOP
        cifra := CAST(SUBSTRING(piva FROM i FOR 1) AS INT);

        IF MOD(i, 2) = 0 THEN
            -- Posizioni PARI (2,4,6,...) → raddoppio
            doppio := cifra * 2;
            IF doppio > 9 THEN
                doppio := doppio - 9;
            END IF;
            somma := somma + doppio;
        ELSE
            -- Posizioni DISPARI → somma diretta
            somma := somma + cifra;
        END IF;
    END LOOP;

    check_digit := (10 - (somma % 10)) % 10;

    RETURN check_digit = CAST(SUBSTRING(piva FROM 11 FOR 1) AS INT);
END;
$function$

