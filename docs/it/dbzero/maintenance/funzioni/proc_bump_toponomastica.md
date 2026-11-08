{% include-markdown "it/dbzero/maintenance/manual/proc_bump_toponomastica.md" %}
# ⚙️ Procedura `proc_bump_toponomastica`

```sql
CREATE PROCEDURE proc_bump_toponomastica(IN p_toponomastica_id integer, IN p_descrizione text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_bump_toponomastica(IN p_toponomastica_id integer, IN p_descrizione text)
 LANGUAGE plpgsql
AS $procedure$
-- Scopo: correggere la descrizione di un toponimo gia' in uso
--   (config.toponomastica) e portare la correzione fino agli
--   indirizzi: stradario generale e indirizzi di dettaglio.
DECLARE
  v_stradario_id config.stradario.id%TYPE;
BEGIN
  -- ⚠️ IL BYPASS DURA QUANTO L'UPDATE, NON DI PIU'.
  --   `set_config(..., true)` vale per la TRANSAZIONE: lasciato
  --   acceso, ogni modifica successiva a config.toponomastica
  --   nella stessa transazione girerebbe senza
  --   trgfn_toponomastica_protect_update. Il blocco EXCEPTION lo
  --   spegne anche quando l'UPDATE fallisce.
  --   Brief: brief-db-revisione-maintenance D1.
  PERFORM set_config('zeroerp.maintenance_toponomastica', 'on', true);

  BEGIN
    -- Il trigger AFTER UPDATE del toponimo
    -- (trgfn_toponomastica_bump_normalize) rinormalizza le righe
    -- di config.stradario_generale che lo usano.
    UPDATE config.toponomastica
       SET descrizione = p_descrizione
     WHERE id = p_toponomastica_id;
  EXCEPTION WHEN OTHERS THEN
    PERFORM set_config('zeroerp.maintenance_toponomastica', 'off', true);
    RAISE;
  END;

  PERFORM set_config('zeroerp.maintenance_toponomastica', 'off', true);

  -- ⭐ La cascata fino agli indirizzi di dettaglio: la loro via
  --   normalizzata si calcola solo quando la riga viene scritta.
  --   Una via alla volta, con la procedura che ne e' la sede.
  --   Brief: brief-db-revisione-maintenance D9.
  FOR v_stradario_id IN
    SELECT s.id
      FROM config.stradario s
      JOIN config.stradario_generale sg ON sg.id = s.stradario_generale_id
     WHERE sg.toponomastica_id = p_toponomastica_id
     ORDER BY s.id
  LOOP
    CALL maintenance.proc_bump_indirizzi_dettaglio(v_stradario_id);
  END LOOP;
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_bump_toponomastica(IN p_toponomastica_id integer, IN p_descrizione text)
IS 'Corregge la descrizione di un toponimo in uso: accende il flag zeroerp.maintenance_toponomastica solo per la UPDATE di config.toponomastica e lo spegne prima di proseguire, anche in caso di errore (vale per la transazione: lasciato acceso, ogni modifica successiva ai toponimi passerebbe senza guard). Il trigger del toponimo rinormalizza config.stradario_generale; poi la procedura chiama maintenance.proc_bump_indirizzi_dettaglio per ogni via che usa il toponimo, cosi'' anche gli indirizzi di dettaglio prendono la descrizione nuova.';
```

</div>

---
{% include-markdown "signature-core.md" %}
