{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_titoli_iva_ambiti_guard.md" %}
# ⚙️ Funzione `trgfn_soggetti_titoli_iva_ambiti_guard`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_ambiti_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga di ambito che rende incoerente il
--   titolo. Non riscrive il predicato: CHIAMA
--   anagrafiche.fn_check_titolo_iva_ambito e solleva il PRIMO
--   motivo. ⚠️ L'ordine dell'array e' il contratto: se cambiasse,
--   il codice sollevato e il motivo mostrato direbbero cose diverse.
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    v_motivi := anagrafiche.fn_check_titolo_iva_ambito(NEW.titolo_iva_id);

    IF jsonb_array_length(v_motivi) = 0 THEN
        RETURN NEW;
    END IF;

    v_primo := v_motivi -> 0;

    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', 'trgfn_soggetti_titoli_iva_ambiti_guard',
        v_primo ->> 'codice',
        jsonb_build_object('campo', 'ambito')
            || COALESCE(v_primo -> 'dettaglio', '{}'::jsonb),
        NEW.tx_id,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(
                           COALESCE(v_primo -> 'valori', '[]'::jsonb))));

    RETURN NEW;   -- irraggiungibile: la riga sopra solleva sempre
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard()
IS 'Guard sulle righe di anagrafiche.soggetti_titoli_iva_ambiti. ⭐ Non contiene il predicato: CHIAMA anagrafiche.fn_check_titolo_iva_ambito e solleva il codice del PRIMO motivo. Il presidio da scrivere non e'' «gli esiti coincidono» ma «il guard non contiene piu'' il predicato» (linee-guida-sql §12.5.2). ⚠️ L''ordine dell''array e'' il contratto: se divergesse, il codice sollevato e il motivo mostrato direbbero cose diverse. ⚠️ AFTER e non BEFORE: la riga nuova deve essere gia'' visibile perche'' la fn_check la conti — un BEFORE valuterebbe il titolo senza di essa e lascerebbe passare proprio la riga che crea il conflitto. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

---
{% include-markdown "signature-core.md" %}
