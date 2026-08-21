{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_piva_libera.md" %}
# ⚙️ Funzione `fn_pgtap_piva_libera`

```sql
CREATE FUNCTION fn_pgtap_piva_libera()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_piva_libera()
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una partita IVA VALIDA e non
--   ancora usata, cosi' nessun test deve piu' cancellare il
--   residuo della corsa precedente per poter ripartire.
DECLARE
    v_base   bigint := 88800000000;
    v_body   text;
    v_check  int;
    v_piva   text;
    v_i      int;
    v_d      int;
    v_sum    int;
    v_try    int := 0;
BEGIN
    LOOP
        v_try := v_try + 1;
        EXIT WHEN v_try > 100000;
        v_body := lpad(((v_base + v_try) % 10000000000)::text, 10, '0');

        -- Cifra di controllo (Luhn sulle 10 cifre del corpo).
        v_sum := 0;
        FOR v_i IN 1..10 LOOP
            v_d := substr(v_body, v_i, 1)::int;
            IF v_i % 2 = 0 THEN
                v_d := v_d * 2;
                IF v_d > 9 THEN v_d := v_d - 9; END IF;
            END IF;
            v_sum := v_sum + v_d;
        END LOOP;
        v_check := (10 - (v_sum % 10)) % 10;
        v_piva := v_body || v_check::text;

        -- ⚠️ Si passa comunque dal validatore di dominio invece di
        --   fidarsi del calcolo: se un giorno la regola cambia, qui
        --   si vede subito.
        IF script.fn_valida_partita_iva(v_piva)
           AND NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti s
                            WHERE s.partita_iva = v_piva
                               OR s.codice_fiscale = v_piva
                               OR s.id_fiscale_univoco_cf_piva = v_piva) THEN
            RETURN v_piva;
        END IF;
    END LOOP;

    RAISE EXCEPTION 'fn_pgtap_piva_libera: nessuna partita IVA libera trovata';
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_piva_libera()
IS 'Restituisce una partita IVA VALIDA (checksum verificato da script.fn_valida_partita_iva) e non ancora presente in anagrafiche.soggetti, per le fixture pgTAP. Serve perche'' il vincolo che faceva collidere le corse dei vecchi test e'' uq_soggetto_idstato_id_fiscale_univoco: con un identificativo fisso la seconda corsa sbatte sul residuo della prima, e dal 2026-01-23 quel residuo non si puo'' piu'' cancellare (dbops.automation_delete_block_ruoli). Vede anche le righe non ancora committate, quindi due chiamate nella stessa transazione danno valori diversi. Brief: work-in-progress/brief-db-bonifica-baseline-pgtap-vendite.md';
```

---
{% include-markdown "signature-core.md" %}
