# ⚙️ Funzione `trgfn_resi_guard_magazzino`

```sql
CREATE FUNCTION trgfn_resi_guard_magazzino()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_magazzino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la regola del magazzino di rientro che un CHECK non vede
--   (D-3b-a): il magazzino e' dell'emittente del reso.
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, regola del 2):
--   «immutabile fuori bozza» non e' piu' qui. Lo dice il BB
--   vendite.trgfn_doc_testata_lock_fuori_bozza
--   (trg_resi_a05_lock_fuori_bozza_upd), con lo stesso codice
--   E_RESO_MAGAZZINO_IMMUTABILE e la stessa frase, e parla prima.
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.magazzino_id IS NOT DISTINCT FROM OLD.magazzino_id
       AND NEW.emittente_fiscale_id IS NOT DISTINCT FROM OLD.emittente_fiscale_id THEN
        RETURN NEW;
    END IF;

    -- Dell'emittente del reso (M-6), dal BB: letto sotto RLS, un
    -- magazzino di un altro emittente non si vede, e la frase e' la stessa.
    IF NEW.magazzino_id IS NOT NULL
       AND NOT script.fn_magazzino_dell_emittente(NEW.magazzino_id, NEW.emittente_fiscale_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.trgfn_resi_guard_magazzino',
            'E_RESO_MAGAZZINO_INCOERENTE',
            jsonb_build_object('reso_id', NEW.id, 'magazzino_id', NEW.magazzino_id,
                               'emittente_reso', NEW.emittente_fiscale_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_magazzino()
IS 'Guard BEFORE INSERT OR UPDATE su vendite.resi (D-3b-a), che esce subito se magazzino ed emittente non cambiano. E_RESO_MAGAZZINO_INCOERENTE: il magazzino non e'' dell''emittente del reso, dal BB script.fn_magazzino_dell_emittente (letto sotto RLS: invisibile e inesistente rispondono uguale). Fascia z10: dopo trgfn_resi_normalize, che all''INSERT eredita l''emittente dalla bolla. Il magazzino mancante NON e'' qui: e'' un motivo della conferma (script.fn_check_reso_merce). Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso. rev 2026-10-09 (brief-db-esecutivi-ba-coppia, regola del 2): «immutabile fuori bozza» (E_RESO_MAGAZZINO_IMMUTABILE) passa al BB vendite.trgfn_doc_testata_lock_fuori_bozza, trigger trg_resi_a05_lock_fuori_bozza_upd: stesso codice, stessa frase, e parla prima di questo guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
