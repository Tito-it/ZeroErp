{% include-markdown "it/dbzero/documenti/manual/trgfn_template_documenti_versioni_assegna_numero.md" %}
# ⚙️ Funzione `trgfn_template_documenti_versioni_assegna_numero`

```sql
CREATE FUNCTION trgfn_template_documenti_versioni_assegna_numero()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_documenti_versioni_assegna_numero()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Il numero di una versione nuova: il successivo all'ultimo del
--   suo modello. Sede unica della numerazione, per la versione
--   scritta da zero e per la copia (documenti.fn_crea_bozza_da_versione).
--
-- Regole:
--   - chi non e' il proprietario della tabella non sceglie il
--     numero: un valore passato si sostituisce;
--   - il proprietario (seed, changeSet) che scrive un numero lo
--     tiene: e' come nascono gli standard;
--   - le nascite nello stesso modello si mettono in fila su un lock
--     di transazione per modello, preso prima di leggere il
--     massimo: due nascite contemporanee prendono due numeri. Il
--     vincolo uq_template_documenti_versioni_template_versione
--     resta la difesa a valle.
--   Il numero dopo la nascita non cambia: lo ferma il lucchetto di
--   colonna (script.trgfn_lock_columns).
BEGIN
  IF NEW.versione IS NOT NULL
     AND script.fn_is_proprietario_tabella(TG_RELID) THEN
    RETURN NEW;
  END IF;

  -- Spazio dei nomi: la colonna numerata; perimetro: il modello.
  PERFORM pg_advisory_xact_lock(
      hashtext('documenti.template_documenti_versioni.versione'),
      hashtext(NEW.template_documento_id::text));

  SELECT COALESCE(max(v.versione), 0) + 1
    INTO NEW.versione
    FROM documenti.template_documenti_versioni v
   WHERE v.template_documento_id = NEW.template_documento_id;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_documenti_versioni_assegna_numero()
IS 'Il numero di una versione di template nuova: il successivo all''ultimo del suo modello. E'' la sede unica della numerazione, per la versione scritta da zero e per la copia (documenti.fn_crea_bozza_da_versione). Chi non e'' il proprietario della tabella non sceglie il numero: un valore passato si sostituisce. Il proprietario (seed, changeSet) che scrive un numero lo tiene, come nascono gli standard. Le nascite nello stesso modello si mettono in fila su un lock di transazione per modello, preso prima di leggere il massimo: due nascite contemporanee prendono due numeri diversi, e il vincolo uq_template_documenti_versioni_template_versione resta la difesa a valle. Dopo la nascita il numero non cambia: lo ferma il lucchetto di colonna (E_CODICE_NON_MODIFICABILE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
