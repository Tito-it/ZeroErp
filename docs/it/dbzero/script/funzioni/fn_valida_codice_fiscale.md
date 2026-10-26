{% include-markdown "it/dbzero/script/manual/fn_valida_codice_fiscale.md" %}
# ⚙️ Funzione `fn_valida_codice_fiscale`

```sql
CREATE FUNCTION fn_valida_codice_fiscale(cf text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_valida_codice_fiscale(cf text)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$DECLARE
      cf_up       TEXT := UPPER(cf);
      i           INT;
      somma       INT := 0;
      c           CHAR;
      val         INT;
      check_char  CHAR;
  BEGIN
      -- ----------------------------------------------------------------
      -- Lo script esegue una validazione formale del codice fiscale
      -- calcolando il carattere di controllo finale.
      -- Non verifica congruenza con data di nascita, sesso o luogo di nascita.
      -- Importante è in grado di validare codice fiscale omocodico (stessa data, luogo di nascita, sesso, nome e cognome)
      -- ----------------------------------------------------------------

      -- 1) preliminare
      IF cf_up IS NULL OR LENGTH(cf_up) <> 16 OR cf_up ~ '[^A-Z0-9]' THEN
          RETURN FALSE;
      END IF;

      -- 2) ciclo sulle prime 15 posizioni (sostituzione caratteri)
      FOR i IN 1..15 LOOP
          c := SUBSTRING(cf_up, i, 1);

          IF (i % 2) = 1 THEN
              -- posizioni dispari: valore da tabella “strana” (inclusi 0–9 e A–Z)
              val := CASE c
                  WHEN '0' THEN  1 WHEN '1' THEN  0 WHEN '2' THEN  5 WHEN '3' THEN  7
                  WHEN '4' THEN  9 WHEN '5' THEN 13 WHEN '6' THEN 15 WHEN '7' THEN 17
                  WHEN '8' THEN 19 WHEN '9' THEN 21
                  WHEN 'A' THEN  1 WHEN 'B' THEN  0 WHEN 'C' THEN  5 WHEN 'D' THEN  7
                  WHEN 'E' THEN  9 WHEN 'F' THEN 13 WHEN 'G' THEN 15 WHEN 'H' THEN 17
                  WHEN 'I' THEN 19 WHEN 'J' THEN 21 WHEN 'K' THEN  2 WHEN 'L' THEN  4
                  WHEN 'M' THEN 18 WHEN 'N' THEN 20 WHEN 'O' THEN 11 WHEN 'P' THEN  3
                  WHEN 'Q' THEN  6 WHEN 'R' THEN  8 WHEN 'S' THEN 12 WHEN 'T' THEN 14
                  WHEN 'U' THEN 16 WHEN 'V' THEN 10 WHEN 'W' THEN 22 WHEN 'X' THEN 25
                  WHEN 'Y' THEN 24 WHEN 'Z' THEN 23
                  ELSE -1
              END;
          ELSE
              -- posizioni pari: numeri → valore numerico, lettere A→0…Z→25
              IF c BETWEEN '0' AND '9' THEN
                  val := CAST(c AS INT);
              ELSE
                  val := ASCII(c) - ASCII('A');
              END IF;
          END IF;

          IF val < 0 THEN
              RETURN FALSE;   -- carattere non riconosciuto
          END IF;

          somma := somma + val;
      END LOOP;

      -- 3) calcolo carattere di controllo
      check_char := CHR(65 + (somma % 26));

      -- 4) confronto con il sedicesimo carattere
      RETURN check_char = SUBSTRING(cf_up, 16, 1);
  END;

  $function$

COMMENT ON FUNCTION script.fn_valida_codice_fiscale(cf text)
IS 'Controlla la validità formale del Codice Fiscale calcolando il carattere di controllo finale.
  Importante è in grado di validare codice fiscale omocodico (stessa data, luogo di nascita, sesso, nome e cognome)
  Non verifica congruenza con data di nascita, sesso o luogo di nascita. 
  Tali controlli vengono demandati al backend (Django/FastAPI) per maggiore flessibilità e
  semplicità di manutenzione. Eventuali validazioni approfondite saranno gestite da servizi esterni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
