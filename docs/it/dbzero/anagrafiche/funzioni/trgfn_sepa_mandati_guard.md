{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_sepa_mandati_guard.md" %}
# ⚙️ Funzione `trgfn_sepa_mandati_guard`

```sql
CREATE FUNCTION trgfn_sepa_mandati_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_sepa_mandati_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: il mandato SEPA (pagamenti.sepa_mandati), BEFORE
    --   INSERT OR UPDATE.
    --   1) stato ATTIVO vuole data_attivazione (E_DATA_ERRATA);
    --   2) l'UMR senza spazi, per il confronto e l'unicita';
    --   3) iban_snapshot e' l'IBAN del conto del legame addebitato
    --      (soggetto_ruolo_conto_id): un derivato, scritto qui a
    --      ogni scrittura. IBAN del conto e conto del legame non
    --      cambiano (lucchetti), quindi lo snapshot resta quello
    --      della firma. Un legame che non c'e' lo rifiuta la FK.
    -- =========================================================
    IF NEW.stato = 'ATTIVO' AND NEW.data_attivazione IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_sepa_mandati_guard',
            'E_DATA_ERRATA',
            jsonb_build_object(
              'campo', 'data_attivazione',
              'tabella','pagamenti.sepa_mandati',
              'stato', NEW.stato,
              'data_attivazione', NEW.data_attivazione
            ), NULL::uuid, 'data attivazione per stato ATTIVO');
    END IF;

    IF NEW.umr IS NOT NULL THEN
        NEW.umr := regexp_replace(NEW.umr, '\s+', '', 'g');
    END IF;

    SELECT c.iban
      INTO NEW.iban_snapshot
      FROM anagrafiche.soggetti_ruoli_conti_bancari l
      JOIN anagrafiche.conti_bancari c ON c.id = l.conto_bancario_id
     WHERE l.id = NEW.soggetto_ruolo_conto_id;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_sepa_mandati_guard()
IS 'BEFORE INSERT OR UPDATE su pagamenti.sepa_mandati. Un mandato ATTIVO ha la data di attivazione (E_DATA_ERRATA, campo data_attivazione); l''UMR si salva senza spazi; iban_snapshot e'' sempre l''IBAN del conto del legame addebitato (soggetto_ruolo_conto_id), scritto qui a ogni scrittura: un valore mandato da fuori si sovrascrive. IBAN del conto e conto del legame hanno il lucchetto, quindi lo snapshot resta quello con cui il mandato e'' nato. intestatario_snapshot resta il dato scritto da chi crea il mandato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
