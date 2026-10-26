{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_piva_libera.md" %}
# ⚙️ Funzione `fn_pgtap_piva_libera`

> ⚠️ **2 firme** con lo stesso nome: ognuna ha il suo blocco qui sotto, in ordine di argomenti.

## Firma `()`

```sql
CREATE FUNCTION fn_pgtap_piva_libera()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
IS 'Restituisce una partita IVA VALIDA (checksum verificato da script.fn_valida_partita_iva) e non ancora presente in anagrafiche.soggetti, per le fixture pgTAP. Serve perche'' il vincolo che faceva collidere le corse dei vecchi test e'' uq_soggetto_idstato_id_fiscale_univoco: con un identificativo fisso la seconda corsa sbatte sul residuo della prima, e dal 2026-01-23 quel residuo non si puo'' piu'' cancellare (dbops.automation_delete_block_ruoli). Vede anche le righe non ancora committate, quindi due chiamate nella stessa transazione danno valori diversi. Brief: brief-db-bonifica-baseline-pgtap-vendite.md';
```

</div>

## Firma `(p_skip integer)`

```sql
CREATE FUNCTION fn_pgtap_piva_libera(p_skip integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_piva_libera(p_skip integer)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: come dbops.fn_pgtap_piva_libera(), ma SALTANDO le prime
--   p_skip libere. Serve quando una fixture ne vuole DUE o piu'
--   nella stessa istruzione.
--
-- ⚠️ IL PERCHE', ed e' un difetto vero della sorella senza
--   argomenti scoperto sul campo. Quella dice «due chiamate nella
--   stessa transazione danno valori diversi», e regge solo se fra
--   l'una e l'altra la prima e' stata INSERITA: e' la riga nuova
--   che la rende occupata. Dentro una sola SELECT
--   (`SELECT fn(), fn()`) non c'e' nessun insert in mezzo, le due
--   chiamate vedono lo stesso database e tornano lo STESSO valore
--   — e la fixture si schianta su
--   uq_soggetto_idstato_id_fiscale_univoco, dando la colpa al test.
--   Con p_skip il chiamante distingue le sue: fn(0), fn(1), fn(2).
DECLARE
    v_base   bigint := 88800000000;
    v_body   text;
    v_check  int;
    v_piva   text;
    v_i      int;
    v_d      int;
    v_sum    int;
    v_try    int := 0;
    v_saltate int := 0;
BEGIN
    IF p_skip IS NULL OR p_skip < 0 THEN
        RAISE EXCEPTION 'fn_pgtap_piva_libera: p_skip deve essere >= 0';
    END IF;

    LOOP
        v_try := v_try + 1;
        EXIT WHEN v_try > 100000;
        v_body := lpad(((v_base + v_try) % 10000000000)::text, 10, '0');

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

        IF script.fn_valida_partita_iva(v_piva)
           AND NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti s
                            WHERE s.partita_iva = v_piva
                               OR s.codice_fiscale = v_piva
                               OR s.id_fiscale_univoco_cf_piva = v_piva) THEN
            IF v_saltate >= p_skip THEN
                RETURN v_piva;
            END IF;
            v_saltate := v_saltate + 1;
        END IF;
    END LOOP;

    RAISE EXCEPTION 'fn_pgtap_piva_libera(%): nessuna partita IVA libera trovata', p_skip;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_piva_libera(p_skip integer)
IS 'Come dbops.fn_pgtap_piva_libera(), ma salta le prime p_skip libere. ⚠️ Serve perche'' la sorella senza argomenti torna lo STESSO valore se la si chiama due volte nella stessa ISTRUZIONE: e'' l''insert della riga a rendere occupato un identificativo, e dentro una sola SELECT non c''e'' nessun insert in mezzo. Una fixture che vuole due partite IVA distinte usa fn(0) e fn(1). Firma separata e senza DEFAULT di proposito: un default renderebbe ambigue le chiamate a zero argomenti gia'' scritte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
