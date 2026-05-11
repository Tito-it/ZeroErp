{% include-markdown "it/dbzero/script/manual/trgfn_componenti_propaga_qta.md" %}
# ⚙️ Funzione `trgfn_componenti_propaga_qta`

```sql
CREATE FUNCTION trgfn_componenti_propaga_qta()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_propaga_qta()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- TG_ARGV[0]: schema (es. 'vendite')
    -- TG_ARGV[1]: tab_figli (es. 'preventivi_righe_componenti')
    -- TG_ARGV[2]: col FK figli->padre (es. 'riga_preventivo_id')
    v_sql text;
BEGIN
    -- Guard difensivo: quantita non cambiata
    -- (UPDATE OF quantita garantisce gia' il cambio, ma
    -- il guard protegge da chiamate dirette accidentali)
    IF NEW.quantita IS NOT DISTINCT FROM OLD.quantita THEN
        RETURN NULL;
    END IF;

    -- Aggiorna quantita su tutti i figli attivi:
    -- quantita = coeff_qta_snapshot * NEW.quantita (padre)
    v_sql := format(
        $q$UPDATE %1$I.%2$I
              SET quantita = coeff_qta_snapshot * $1
            WHERE %3$I = $2
              AND attivo = TRUE$q$,
        TG_ARGV[0],
        TG_ARGV[1],
        TG_ARGV[2]
    );
    EXECUTE v_sql USING NEW.quantita, NEW.id;

    RETURN NULL;  -- AFTER trigger
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_propaga_qta()
IS 'Trigger function AFTER UPDATE OF quantita su riga padre: propaga quantita ai figli attivi come coeff_qta_snapshot * NEW.quantita. TG_ARGV[0]=schema [1]=tab_figli [2]=col_fk_figli->padre. Usata su 5 tabelle sorgente CASO A.';
```

---
{% include-markdown "signature-core.md" %}
