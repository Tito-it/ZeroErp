{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_titoli_iva_guard_ambito.md" %}
# ⚙️ Funzione `trgfn_soggetti_titoli_iva_guard_ambito`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_guard_ambito()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la stessa regola dell'ambito, applicata quando a cambiare
--   e' il TITOLO e non le sue righe. Due titoli diventano
--   sovrapposti anche allargando `valido_al`, riattivando un
--   titolo spento o cambiandone il tipo: in nessuno di quei casi
--   la tabella figlia viene toccata, quindi il guard sulle figlie
--   non scatta. Chiama la stessa fn_check.
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    v_motivi := anagrafiche.fn_check_titolo_iva_ambito(NEW.id);

    IF jsonb_array_length(v_motivi) = 0 THEN
        RETURN NULL;
    END IF;

    v_primo := v_motivi -> 0;

    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', 'trgfn_soggetti_titoli_iva_guard_ambito',
        v_primo ->> 'codice',
        jsonb_build_object('campo', 'valido_al')
            || COALESCE(v_primo -> 'dettaglio', '{}'::jsonb),
        NEW.tx_id,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(
                           COALESCE(v_primo -> 'valori', '[]'::jsonb))));

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito()
IS 'La stessa regola dell''ambito, applicata quando a cambiare e'' il TITOLO invece delle sue righe. ⭐ Non e'' un doppione del guard sulle figlie: due titoli diventano sovrapposti anche allargando valido_al, riattivando un titolo spento o cambiandone il tipo — e in nessuno di quei casi la tabella figlia viene toccata, quindi quel guard non scatta. Chiama la stessa anagrafiche.fn_check_titolo_iva_ambito: la regola e'' scritta in un posto solo. ⚠️ AFTER UPDATE, perche'' la fn_check legge la riga com''e'' DOPO la modifica. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

---
{% include-markdown "signature-core.md" %}
