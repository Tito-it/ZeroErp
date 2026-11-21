{% include-markdown "it/dbzero/ui/manual/trgfn_lista_definizione_guard_dichiarazioni.md" %}
# ⚙️ Funzione `trgfn_lista_definizione_guard_dichiarazioni`

```sql
CREATE FUNCTION trgfn_lista_definizione_guard_dichiarazioni()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_lista_definizione_guard_dichiarazioni()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: le dichiarazioni di una lista (multi_emittente,
-- perimetro_emittente, legge_lineage) le scrive solo il proprietario
-- della tabella, cioe' il migrate dal CSV del seed.
-- Ogni riga: colonna, valore nuovo, valore di confronto. Il confronto
-- e' il valore precedente in UPDATE, quello ammesso senza permesso in
-- INSERT.
DECLARE
  v_colonna text;
BEGIN
  SELECT d.colonna
    INTO v_colonna
    FROM (VALUES
            (1, 'multi_emittente', NEW.multi_emittente,
             CASE WHEN TG_OP = 'INSERT' THEN false ELSE OLD.multi_emittente END),
            (2, 'perimetro_emittente', NEW.perimetro_emittente,
             CASE WHEN TG_OP = 'INSERT' THEN true ELSE OLD.perimetro_emittente END),
            (3, 'legge_lineage', NEW.legge_lineage,
             CASE WHEN TG_OP = 'INSERT' THEN false ELSE OLD.legge_lineage END)
         ) AS d(ordine, colonna, nuovo, confronto)
   WHERE d.nuovo IS DISTINCT FROM d.confronto
   ORDER BY d.ordine
   LIMIT 1;

  IF v_colonna IS NULL THEN
    RETURN NEW;
  END IF;

  -- La regola «chi e' il proprietario» ha una sede sola, il BB.
  IF script.fn_is_proprietario_tabella(TG_RELID) THEN
    RETURN NEW;
  END IF;

  PERFORM script.fn_log_and_raise_error(
    'database',
    'ui.trgfn_lista_definizione_guard_dichiarazioni',
    'E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE',
    jsonb_build_object(
      'campo', v_colonna,
      'lista_id', NEW.id,
      'lista_codice', NEW.codice,
      'current_user', current_user
    ),
    NULL::uuid,
    v_colonna,
    NEW.codice::text
  );

  RETURN NEW;  -- irraggiungibile: la riga sopra solleva
END;
$function$

COMMENT ON FUNCTION ui.trgfn_lista_definizione_guard_dichiarazioni()
IS 'Guard BEFORE INSERT OR UPDATE OF multi_emittente, perimetro_emittente, legge_lineage su ui.lista_definizione: le tre dichiarazioni della lista le scrive solo il proprietario della tabella (script.fn_is_proprietario_tabella), cioè il migrate dal CSV del seed, su ogni riga. In INSERT passa il valore che non promette niente (multi_emittente false, perimetro_emittente true, legge_lineage false); in UPDATE ogni cambio di valore da un altro ruolo è rifiutato con E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE, che nomina la colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
