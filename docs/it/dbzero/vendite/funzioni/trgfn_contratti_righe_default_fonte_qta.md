# ⚙️ Funzione `trgfn_contratti_righe_default_fonte_qta`

```sql
CREATE FUNCTION trgfn_contratti_righe_default_fonte_qta()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_default_fonte_qta()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Scopo: normalizza fonte_quantita_attesa al default coerente con tipo_erogazione.
    -- Casistica INSERT: fonte NULL → imposta default dalla matrice.
    -- Casistica UPDATE: se tipo cambia e la nuova combinazione è vietata (❌) → resetta.
    -- Le combinazioni 🟡 rare ma non vietate non vengono alterate.

    IF NEW.fonte_quantita_attesa IS NULL THEN
        -- INSERT senza fonte o UPDATE che azzera fonte (difensivo, NOT NULL è il backstop).
        NEW.fonte_quantita_attesa := CASE NEW.tipo_erogazione
            WHEN 'CANONE'     THEN 'FISSA'
            WHEN 'UNA_TANTUM' THEN 'FISSA'
            WHEN 'ORARIO'     THEN 'MANUALE'
            WHEN 'CONSUMO'    THEN 'LETTURE'
            ELSE                   'FISSA'
        END;

    ELSIF TG_OP = 'UPDATE'
          AND NEW.tipo_erogazione IS DISTINCT FROM OLD.tipo_erogazione
          AND (
                  (NEW.tipo_erogazione = 'CONSUMO'
                       AND NEW.fonte_quantita_attesa IN ('FISSA', 'TIMESHEET'))
              OR  (NEW.tipo_erogazione IN ('CANONE', 'UNA_TANTUM')
                       AND NEW.fonte_quantita_attesa IN ('TIMESHEET', 'LETTURE'))
              OR  (NEW.tipo_erogazione = 'ORARIO'
                       AND NEW.fonte_quantita_attesa = 'LETTURE')
          )
    THEN
        -- Tipo cambiato e la combinazione attuale diventa vietata → reset al default.
        NEW.fonte_quantita_attesa := CASE NEW.tipo_erogazione
            WHEN 'CANONE'     THEN 'FISSA'
            WHEN 'UNA_TANTUM' THEN 'FISSA'
            WHEN 'ORARIO'     THEN 'MANUALE'
            WHEN 'CONSUMO'    THEN 'LETTURE'
            ELSE                   'FISSA'
        END;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_default_fonte_qta()
IS 'Normalizza fonte_quantita_attesa al default per tipo_erogazione. INSERT: imposta default se NULL. UPDATE OF tipo_erogazione: resetta solo se la nuova combinazione tipo+fonte è ❌ (matrice 20260519). Le combinazioni 🟡 rare non vengono alterate. Compatibile con guard_pending (nome alfabeticamente precedente: esegue prima).';
```

---
{% include-markdown "signature-core.md" %}
