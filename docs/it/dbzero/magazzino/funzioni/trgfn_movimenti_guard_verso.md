{% include-markdown "it/dbzero/magazzino/manual/trgfn_movimenti_guard_verso.md" %}
# ⚙️ Funzione `trgfn_movimenti_guard_verso`

```sql
CREATE FUNCTION trgfn_movimenti_guard_verso()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_movimenti_guard_verso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_segno   magazzino.causali.segno%TYPE;
  v_causale magazzino.causali.codice_interno%TYPE;
BEGIN
  -- Scopo: la rete di M-1. Il verso di un movimento sta nella quantita'
  --   (qta firmata) e deve coincidere con il verso della causale
  --   (causali.segno, -1 o +1). Vale per il registro e per gli attesi.
  -- Regole:
  --   - causale inesistente: non e' affar suo, parla la FK (RETURN NEW);
  --   - sign(qta) <> segno: E_MAG_MOVIMENTO_VERSO_INCOERENTE (TECNICO,
  --     senza `campo`: il verso lo compone l'operazione, non una persona);
  --   - qta = 0 cade qui (sign = 0), prima del CHECK qta <> 0.
  SELECT c.segno, c.codice_interno
    INTO v_segno, v_causale
    FROM magazzino.causali c
   WHERE c.id = NEW.causale_id;

  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  IF sign(NEW.qta) <> v_segno THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'magazzino.trgfn_movimenti_guard_verso',
      'E_MAG_MOVIMENTO_VERSO_INCOERENTE',
      jsonb_build_object(
        'detail',     'sign(qta) diverso da causali.segno',
        'tabella',    TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        'causale_id', NEW.causale_id,
        'causale',    v_causale,
        'segno',      v_segno,
        'qta',        NEW.qta
      ),
      NEW.tx_id,
      v_causale, v_segno::text, NEW.qta::text
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION magazzino.trgfn_movimenti_guard_verso()
IS 'Guard del VERSO (M-1): rifiuta un movimento o un atteso la cui quantita'' non ha il segno della causale (sign(qta) <> causali.segno) con E_MAG_MOVIMENTO_VERSO_INCOERENTE, classe TECNICO — il verso lo compone l''operazione dalla causale, un mismatch e'' un chiamante rotto, e il contesto non porta campo. Causale inesistente: RETURN NEW, parla la FK. qta = 0 cade qui (sign = 0) prima del CHECK qta <> 0, che resta come seconda rete. Montata su magazzino.movimenti e magazzino.movimenti_attesi. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.9.';
```

</div>

---
{% include-markdown "signature-core.md" %}
