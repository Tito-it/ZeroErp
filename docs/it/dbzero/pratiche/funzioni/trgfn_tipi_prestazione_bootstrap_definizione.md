# ⚙️ Funzione `trgfn_tipi_prestazione_bootstrap_definizione`

```sql
CREATE FUNCTION trgfn_tipi_prestazione_bootstrap_definizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_tipi_prestazione_bootstrap_definizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: garantire l'invariante "ogni tipo di prestazione ha il
--        suo preset v1 PUBBLICATA" fin dalla nascita del tipo.
--        Cosi' auto-pin/auto-default risolvono sempre e i seed
--        (o le fixture di test) non devono creare definizioni.
BEGIN
  INSERT INTO pratiche.workflow_definizioni
         (tipo_prestazione_id, emittente_fiscale_id, versione, stato,
          descrizione, tx_id)
  VALUES (NEW.id, NULL, 1, 'PUBBLICATA',
          'v1 — preset iniziale del tipo ' || NEW.codice_interno,
          NEW.tx_id)
  ON CONFLICT (tipo_prestazione_id, emittente_fiscale_id)
     WHERE stato = 'PUBBLICATA'
     DO NOTHING;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_tipi_prestazione_bootstrap_definizione()
IS 'AFTER INSERT su pratiche.tipi_prestazione: crea il preset v1 PUBBLICATA della definizione workflow del nuovo tipo (idempotente). Invariante Fase 0: ogni tipo ha sempre un preset risolvibile da fn_risolvi_definizione.';
```

---
{% include-markdown "signature-core.md" %}
