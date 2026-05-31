# ⚙️ Funzione `trgfn_righe_default_fonte_qta`

```sql
CREATE FUNCTION trgfn_righe_default_fonte_qta()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_default_fonte_qta()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Scopo: normalizza fonte_quantita_attesa al default coerente con tipo_erogazione.
    -- Generica: nessun riferimento a una tabella specifica (usabile su qualunque
    -- *_righe / *_eccezioni con le colonne tipo_erogazione + fonte_quantita_attesa).
    -- INSERT: fonte NULL -> imposta default dalla matrice.
    -- UPDATE: se tipo cambia e la nuova combinazione e' vietata (❌) -> resetta.
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

COMMENT ON FUNCTION script.trgfn_righe_default_fonte_qta()
IS 'Generica/table-agnostic. Normalizza fonte_quantita_attesa al default per tipo_erogazione. INSERT: imposta default se NULL. UPDATE OF tipo_erogazione: resetta solo se la nuova combinazione tipo+fonte e'' vietata (❌, matrice 20260519). Generalizza vendite.trgfn_contratti_righe_default_fonte_qta. Riusata da contratti_righe e offerte_commerciali_eccezioni. Rev 2026-05-31.';
```

---
{% include-markdown "signature-core.md" %}
