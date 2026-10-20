{% include-markdown "it/dbzero/maintenance/manual/proc_bump_indirizzi_dettaglio.md" %}
# ⚙️ Procedura `proc_bump_indirizzi_dettaglio`

```sql
CREATE PROCEDURE proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
 LANGUAGE plpgsql
AS $procedure$
-- Scopo: rinormalizzare anagrafiche.indirizzi_dettaglio dopo un
--   cambio di via, attraversando il guard che in condizioni
--   normali blocca la modifica di stradario_id.
--
-- ⚠️ IL BYPASS DEVE DURARE QUANTO LA PROCEDURA, NON DI PIU'.
--   `set_config(..., true)` vale per la TRANSAZIONE: lasciandolo
--   acceso, ogni istruzione successiva della stessa transazione
--   girerebbe senza la protezione di
--   trgfn_indirizzi_dettaglio_protect_update, e nessuno se ne
--   accorgerebbe. Prima non veniva mai spento: funzionava solo
--   perche' la procedura veniva chiamata da sola, in autocommit,
--   e la transazione moriva subito dopo.
--   Il blocco EXCEPTION serve a spegnerlo anche quando l'UPDATE
--   fallisce: una porta che si richiude solo se tutto va bene non
--   e' una porta chiusa.
--   Brief: brief-db-pgtap-runner-rls-baseline §18.
BEGIN
  PERFORM set_config('zeroerp.maintenance_indirizzi_dettaglio', 'on', true);

  BEGIN
    UPDATE anagrafiche.indirizzi_dettaglio
    SET stradario_id = stradario_id
    WHERE stradario_id = p_stradario_id;
  EXCEPTION WHEN OTHERS THEN
    PERFORM set_config('zeroerp.maintenance_indirizzi_dettaglio', 'off', true);
    RAISE;
  END;

  PERFORM set_config('zeroerp.maintenance_indirizzi_dettaglio', 'off', true);
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
IS 'Rinormalizza anagrafiche.indirizzi_dettaglio per una via, attraversando trgfn_indirizzi_dettaglio_protect_update tramite il flag zeroerp.maintenance_indirizzi_dettaglio. Il flag viene rimesso a ''off'' prima di uscire, anche in caso di errore: altrimenti il bypass resterebbe attivo per tutta la transazione chiamante e ogni modifica successiva a indirizzi_dettaglio girerebbe senza protezione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
