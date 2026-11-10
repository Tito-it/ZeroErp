{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_cf_libero.md" %}
# ⚙️ Funzione `fn_pgtap_cf_libero`

```sql
CREATE FUNCTION fn_pgtap_cf_libero()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_cf_libero()
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un codice fiscale VALIDO e non
--   ancora usato, cosi' nessun test deve piu' cancellare il
--   soggetto residuo della corsa precedente per poter ripartire.
DECLARE
    v_lettere text := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    v_corpo   text;
    v_cf      text;
    v_i       int;
    v_j       int;
BEGIN
    -- Il corpo varia su una lettera; il CARATTERE DI CONTROLLO non
    -- si calcola, si CERCA: si provano le 26 lettere e si tiene
    -- quella che script.fn_valida_codice_fiscale accetta. Cosi' la
    -- regola resta UNA, quella di dominio, invece di essere
    -- reimplementata qui e divergere alla prima modifica.
    FOR v_i IN 1..26 LOOP
        v_corpo := 'TST' || substr(v_lettere, v_i, 1) || 'PG'
                   || '80A01' || 'H501';
        FOR v_j IN 1..26 LOOP
            v_cf := v_corpo || substr(v_lettere, v_j, 1);
            IF script.fn_valida_codice_fiscale(v_cf)
               AND NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti s
                                WHERE s.codice_fiscale = v_cf
                                   OR s.id_fiscale_univoco_cf_piva = v_cf) THEN
                RETURN v_cf;
            END IF;
        END LOOP;
    END LOOP;

    RAISE EXCEPTION 'fn_pgtap_cf_libero: nessun codice fiscale libero trovato';
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_cf_libero()
IS 'Fixture pgTAP: un codice fiscale VALIDO secondo script.fn_valida_codice_fiscale e non ancora presente in anagrafiche.soggetti. Sorella di dbops.fn_pgtap_piva_libera: stesso problema (uq_soggetto_idstato_id_fiscale_univoco contro identificativi gia'' scritti), stessa soluzione. Il carattere di controllo non lo calcola, lo CERCA provando l''alfabeto e chiedendo al validatore di dominio: reimplementare l''algoritmo qui vorrebbe dire tenerne due copie. ⚠️ Non e'' un generatore di codici fiscali reali: il corpo e'' fittizio e serve solo a superare validatore e unicita'' in un test. Vede anche le righe non ancora committate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
