{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_normalize.md" %}
# ⚙️ Funzione `trgfn_indirizzi_dettaglio_normalize`

```sql
CREATE FUNCTION trgfn_indirizzi_dettaglio_normalize()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_result record;
BEGIN
  -- Delega TUTTA la logica a fn_build_indirizzo_normalizzato
  SELECT * INTO v_result
    FROM anagrafiche.fn_build_indirizzo_normalizzato(
      NEW.stradario_id, NEW.civico, NEW.estensione_civico,
      NEW.palazzina, NEW.scala, NEW.piano, NEW.interno
    );

  -- Assegna i risultati alle colonne della riga
  NEW.estensione_civico      := v_result.o_estensione_civico;
  NEW.palazzina              := v_result.o_palazzina;
  NEW.scala                  := v_result.o_scala;
  NEW.piano                  := v_result.o_piano;
  NEW.interno                := v_result.o_interno;
  NEW.via_norm               := v_result.o_via_norm;
  NEW.civico_norm            := v_result.o_civico_norm;
  NEW.indirizzo_normalizzato := v_result.o_indirizzo_normalizzato;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()
IS 'Trigger wrapper: chiama fn_build_indirizzo_normalizzato e assegna tutti i campi calcolati. Zero logica — tutta centralizzata nella funzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
