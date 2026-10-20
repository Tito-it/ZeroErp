{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_erogazione_obbligatoria.md" %}
# ⚙️ Funzione `trgfn_righe_guard_erogazione_obbligatoria`

```sql
CREATE FUNCTION trgfn_righe_guard_erogazione_obbligatoria()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_erogazione_obbligatoria()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga di contratto o di offerta che si fattura
--   (ogni tipo che non e' ESCLUSIONE) senza tipo_erogazione.
-- Uso:   BEFORE INSERT OR UPDATE OF tipo_erogazione, tipo_eccezione
--        FOR EACH ROW, fascia _a10_, su vendite.contratti_righe e
--        vendite.offerte_commerciali_eccezioni.
-- TG_ARGV[0]: nome della colonna del documento padre ('contratto_id',
--   'offerta_id'), solo per il contesto dell'errore.
DECLARE
    v_col_padre text := TG_ARGV[0];
BEGIN
    IF NEW.tipo_erogazione IS NOT NULL
       OR NEW.tipo_eccezione::text = 'ESCLUSIONE' THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_RIGA_EROGAZIONE_OBBLIGATORIA',
        jsonb_build_object(
            'campo',          'tipo_erogazione',
            'riga_id',        NEW.id,
            v_col_padre,      to_jsonb(NEW) -> v_col_padre,
            'articolo_id',    NEW.articolo_id,
            'tipo_eccezione', NEW.tipo_eccezione),
        NEW.tx_id,
        VARIADIC ARRAY[]::text[]);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_erogazione_obbligatoria()
IS 'Guard: una riga di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni che si fattura (ogni tipo che non e'' ESCLUSIONE: oggi OVERRIDE e AGGIUNTA) vuole tipo_erogazione (E_RIGA_EROGAZIONE_OBBLIGATORIA, DATO_ERRATO, campo = tipo_erogazione). Sull''ESCLUSIONE e'' vuota, come gli altri dati di vendita: lo dice script.trgfn_righe_guard_esclusione_senza_dati (rev 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende). Una funzione per le due tabelle gemelle, come trgfn_righe_default_fonte_qta: fn_push_offerta_a_contratto ricopia l''erogazione dall''offerta, e la regola deve essere la stessa ai due capi. TG_ARGV[0] = colonna del documento padre (contratto_id, offerta_id), solo per il contesto. Trigger _a10_ BEFORE INSERT OR UPDATE OF tipo_erogazione, tipo_eccezione: parla prima dei CHECK chk_contrighe_erogazione_per_tipo_eccezione / chk_offerte_eccezioni_erogazione_per_tipo_eccezione, che restano la rete. Contesto: campo, riga_id, la colonna padre, articolo_id, tipo_eccezione. Nasce il 2026-10-04, brief-db-erogazione-obbligatoria-righe-fatturate (decisione di Tid).';
```

</div>

---
{% include-markdown "signature-core.md" %}
