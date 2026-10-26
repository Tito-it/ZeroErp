{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_efba_guard_albero_emittente.md" %}
# ⚙️ Funzione `trgfn_efba_guard_albero_emittente`

```sql
CREATE FUNCTION trgfn_efba_guard_albero_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_albero_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ba_id anagrafiche.billing_account.id%TYPE;
BEGIN
    -- Su DELETE il BA interessato sta in OLD; in creazione in NEW.
    -- Se il mapping viene spostato da un BA a un altro (caso
    -- teorico: la UNIQUE lo rende raro) vanno verificati entrambi.
    v_ba_id := COALESCE(NEW.billing_account_id, OLD.billing_account_id);

    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id THEN
        PERFORM anagrafiche.fn_guard_albero_ba_emittente(OLD.billing_account_id);
        PERFORM anagrafiche.fn_guard_albero_ba_emittente(NEW.billing_account_id);
        RETURN NULL;
    END IF;

    IF v_ba_id IS NOT NULL THEN
        -- Movimenti 2 e 3: mapping specifico creato, cambiato o tolto.
        PERFORM anagrafiche.fn_guard_albero_ba_emittente(v_ba_id);
        RETURN NULL;
    END IF;

    -- Movimento 4: la riga senza billing_account_id e' quella del
    -- GESTORE GLOBALE. Raggio N — vedi l'intestazione del changeSet.
    PERFORM anagrafiche.fn_guard_albero_ba_gestore_globale();
    RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_albero_emittente()
IS 'Trigger AFTER su anagrafiche.emittenti_fiscali_billing_account: presidia i TRE movimenti che cambiano l''emittente di un BA — modifica del mapping, cancellazione del mapping (il BA ricade sul gestore globale) e spostamento di is_default (raggio N). Delega a fn_guard_albero_ba_emittente / fn_guard_albero_ba_gestore_globale. AFTER perche'' il guard rilegge il mapping per risolvere l''emittente. Brief P-1 §11.3. ⚠️ rev 2026-08-26: quei movimenti NON sono piu'' ordinari. Dal 20260826-49 anagrafiche.trgfn_efba_guard_storia_emittente li ammette solo finche'' il billing account non ha STORIA — nessuna fattura e nessuna commessa — perche'' un documento gia'' emesso congela chi lo ha emesso e spostare il cliente lo lascerebbe orfano. ⛔ Non e'' un divieto: e'' una CONDIZIONE. Un billing account nasce gia'' agganciato all''emittente dell''operatore che lo crea, quindi puo'' nascere sbagliato, e la correzione deve restare possibile finche'' su quel cliente non e'' passato del lavoro. Questo guard e'' il fratello dell''altro e resta necessario: uno dice «l''albero non puo'' diventare misto», l''altro «la storia non si sposta». Brief: brief-db-billing-account-cambio-emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
