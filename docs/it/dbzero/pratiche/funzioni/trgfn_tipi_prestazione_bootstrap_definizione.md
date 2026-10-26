{% include-markdown "it/dbzero/pratiche/manual/trgfn_tipi_prestazione_bootstrap_definizione.md" %}
# ⚙️ Funzione `trgfn_tipi_prestazione_bootstrap_definizione`

```sql
CREATE FUNCTION trgfn_tipi_prestazione_bootstrap_definizione()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_tipi_prestazione_bootstrap_definizione()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pratiche', 'script', 'config', 'dbops', 'pg_temp'
AS $function$
-- Scopo: garantire l'invariante "ogni tipo di prestazione ha il
--        suo preset v1 PUBBLICATA" fin dalla nascita del tipo.
--        Cosi' auto-pin/auto-default risolvono sempre e i seed
--        (o le fixture di test) non devono creare definizioni.
--
-- ⚠️ SECURITY DEFINER, e non e' una comodita'.
--   pratiche.workflow_definizioni e' in SOLA LETTURA per il ruolo
--   applicativo per scelta (20260703-15): ci si scrive solo
--   attraverso le funzioni del dominio. Da INVOKER questo INSERT
--   girava coi privilegi del chiamante e falliva con «permesso
--   negato», rendendo impossibile a zeroerp_app creare un tipo di
--   prestazione. Il bootstrap pero' non e' una scrittura che
--   l'utente sceglie: e' il dominio che si prepara da se', a
--   partire da NEW e da nient'altro.
--   Stessa strada di fn_fork_nuova_versione (20260703-16) e
--   fn_pubblica_definizione (20260703-17).
--   search_path fisso: l'INSERT scatena i trigger di
--   workflow_definizioni, che lo ereditano.
--   Brief: brief-db-pgtap-runner-rls-baseline §13.2.
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
IS 'AFTER INSERT su pratiche.tipi_prestazione: crea il preset v1 PUBBLICATA della definizione workflow del nuovo tipo (idempotente). Invariante Fase 0: ogni tipo ha sempre un preset risolvibile da fn_risolvi_definizione. SECURITY DEFINER con search_path fisso: workflow_definizioni e'' in sola lettura per il ruolo applicativo (20260703-15), e da INVOKER questo bootstrap rendeva impossibile creare un tipo di prestazione. Stessa strada di fn_fork_nuova_versione e fn_pubblica_definizione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
