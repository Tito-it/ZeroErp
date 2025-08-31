# ⚙️ Funzione `trgfn_prevnote_validate`

```sql
CREATE FUNCTION trgfn_prevnote_validate()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_prevnote_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE v_prev_id BIGINT;
BEGIN
  IF NEW.anchor_tipo = 'RIGA' THEN
    SELECT preventivo_id INTO v_prev_id
    FROM vendite.preventivi_righe
    WHERE id = NEW.target_riga_id;

    IF NOT FOUND OR v_prev_id IS DISTINCT FROM NEW.target_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite','note_preventivo','E_NOTE_RIGA_MISMATCH',
        jsonb_build_object('target_id',NEW.target_id,'target_riga_id',NEW.target_riga_id),
        NULL::uuid,
        format('La riga %s non appartiene al preventivo %s', NEW.target_riga_id, NEW.target_id)
      );
    END IF;
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
