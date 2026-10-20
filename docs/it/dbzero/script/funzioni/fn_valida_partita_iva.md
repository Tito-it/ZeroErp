{% include-markdown "it/dbzero/script/manual/fn_valida_partita_iva.md" %}
# ⚙️ Funzione `fn_valida_partita_iva`

```sql
CREATE FUNCTION fn_valida_partita_iva(piva text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
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
      -- ----------------------------------------------------------------
      -- Lo script esegue una validazione formale della Partita IVA   
      -- calcolando il carattere di controllo finale.
      -- ----------------------------------------------------------------

      -- Controlli iniziali formali (11 cifre numeriche)
      IF piva IS NULL OR LENGTH(piva) <> 11 OR piva ~ '[^0-9]' THEN
          RETURN FALSE;
      END IF;
     -- Calcola somma con algoritmo di Luhn modificato (specifico Italia)
      FOR i IN 1..10 LOOP
          cifra := CAST(SUBSTRING(piva FROM i FOR 1) AS INT);

          IF MOD(i, 2) = 0 THEN
              -- Posizioni PARI (2,4,6,...) → raddoppio
              -- Posizioni pari: cifra raddoppiata, se >9 sottrai 9
              doppio := cifra * 2;
              IF doppio > 9 THEN
                  doppio := doppio - 9;
              END IF;
              somma := somma + doppio;
          ELSE
              -- Posizioni DISPARI → somma diretta
              -- Posizioni dispari: cifra invariata
              somma := somma + cifra;
          END IF;
      END LOOP;
      -- Calcola il carattere di controllo finale (check digit)
      check_digit := (10 - (somma % 10)) % 10;
      -- Ritorna TRUE se il carattere finale corrisponde, FALSE altrimenti
      RETURN check_digit = CAST(SUBSTRING(piva FROM 11 FOR 1) AS INT);
  END;
  $function$

COMMENT ON FUNCTION script.fn_valida_partita_iva(piva text)
IS 'Validazione formale partita IVA italiana. 
  Restituisce TRUE se la partita IVA supera il controllo del carattere finale (check digit),
   altrimenti FALSE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
