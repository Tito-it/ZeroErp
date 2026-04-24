# ⚙️ Funzione `fn_listini_versioni_close_scadute`

```sql
CREATE FUNCTION fn_listini_versioni_close_scadute()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listini_versioni_close_scadute()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: chiudere in batch le versioni listino ATTIVA con
-- valido_al gia' scaduto (valido_al < CURRENT_DATE).
-- L'UPDATE attraversa il guard trigger
-- trg_listini_versioni_a10_guard_transizione_stato_upd che
-- ammette ATTIVA -> CHIUSA solo con valido_al scaduto:
-- condizione per costruzione soddisfatta.
-- Richiamata dal job pgAgent notturno
-- 'listini_versioni_close_scadute_daily'. Ritorna il numero
-- di righe effettivamente chiuse.
DECLARE
    v_count integer;
BEGIN
    UPDATE vendite.listini_versioni
       SET stato = 'CHIUSA'
     WHERE stato = 'ATTIVA'
       AND valido_al IS NOT NULL
       AND valido_al < CURRENT_DATE;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$function$

COMMENT ON FUNCTION vendite.fn_listini_versioni_close_scadute()
IS 'Chiude in batch versioni listino ATTIVA con valido_al scaduto. Eseguita dal job pgAgent notturno. Ritorna numero righe chiuse.';
```

---
{% include-markdown "signature-core.md" %}
