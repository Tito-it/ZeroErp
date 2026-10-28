{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_pratica_terminale.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_pratica_terminale`

```sql
CREATE FUNCTION trgfn_flussi_guard_pratica_terminale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_pratica_terminale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: difesa lato DB. Una pratica in stato TERMINALE e' conclusa
--   e i suoi flussi sono congelati: ne' nuovi flussi (INSERT) ne'
--   modifiche a flussi esistenti (UPDATE: stato, esito, note_esito,
--   qualunque campo operativo).
-- Regole:
--   1. "Terminale" = stato pratica senza alcuna transizione di stato
--      in uscita attiva (config.transizioni_stati_pratiche). Nessun
--      id/codice hardcodato: la definizione si auto-mantiene.
--   2. Il guard e' su pratiche.flussi: la transizione della pratica
--      verso lo stato terminale (UPDATE su pratiche.pratiche) non
--      passa di qui e resta permessa.
--   3. Codice errore distinto per operazione (creazione vs modifica)
--      per messaggi utente piu' chiari lato BE/FE.
DECLARE
    v_stato_id      pratiche.pratiche.stato_id%TYPE;
    v_stato_codice  config.stati_pratiche.codice_interno%TYPE;
BEGIN
    -- Stato corrente della pratica padre (esiste sempre: FK fk_flussi_pratica).
    SELECT p.stato_id, sp.codice_interno
      INTO v_stato_id, v_stato_codice
      FROM pratiche.pratiche p
      JOIN config.stati_pratiche sp ON sp.id = p.stato_id
     WHERE p.id = NEW.pratica_id;

    -- Pratica ancora operabile (lo stato ha almeno una uscita attiva):
    -- nessun blocco.
    IF EXISTS (
        SELECT 1
          FROM config.transizioni_stati_pratiche t
         WHERE t.stato_da_id = v_stato_id
           AND t.attivo
    ) THEN
        RETURN NEW;
    END IF;

    -- Pratica terminale: blocca con errore parlante.
    IF TG_OP = 'INSERT' THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_flussi_guard_pratica_terminale',
            'E_PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO',
            jsonb_build_object(
                'pratica_id', NEW.pratica_id,
                'stato', v_stato_codice
            ),
            NEW.tx_id,
            v_stato_codice
        );
    ELSE
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_flussi_guard_pratica_terminale',
            'E_PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE',
            jsonb_build_object(
                'pratica_id', NEW.pratica_id,
                'flusso_id', NEW.id,
                'stato', v_stato_codice
            ),
            NEW.tx_id,
            v_stato_codice
        );
    END IF;

    RETURN NEW;  -- non raggiunto: fn_log_and_raise_error solleva.
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_pratica_terminale()
IS 'BEFORE INSERT OR UPDATE su flussi: blocca creazione/modifica di flussi se la pratica padre e'' in stato terminale (stato senza transizioni di stato in uscita attive). Non blocca la transizione della pratica a terminale (guard su flussi, non su pratiche).';
```

</div>

---
{% include-markdown "signature-core.md" %}
