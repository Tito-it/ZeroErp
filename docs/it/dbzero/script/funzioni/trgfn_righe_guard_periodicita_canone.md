{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_periodicita_canone.md" %}
# ⚙️ Funzione `trgfn_righe_guard_periodicita_canone`

```sql
CREATE FUNCTION trgfn_righe_guard_periodicita_canone()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_periodicita_canone()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga di contratto o di offerta a canone senza
--   periodicita'. Regola completa nell'intestazione del changeSet
--   20261101-05.
-- Uso:   BEFORE INSERT OR UPDATE OF tipo_erogazione, periodicita
--        FOR EACH ROW, fascia _a10_, dopo il default dal listino, su
--        vendite.contratti_righe e vendite.offerte_commerciali_eccezioni.
-- TG_ARGV[0]: colonna del documento padre ('contratto_id',
--   'offerta_id'), solo per il contesto dell'errore.
DECLARE
    v_col_padre text := TG_ARGV[0];
BEGIN
    IF NEW.tipo_erogazione IS DISTINCT FROM 'CANONE'
       OR NEW.periodicita IS NOT NULL THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_RIGA_CANONE_SENZA_PERIODICITA',
        jsonb_build_object(
            'campo',          'periodicita',
            'riga_id',        NEW.id,
            v_col_padre,      to_jsonb(NEW) -> v_col_padre,
            'articolo_id',    NEW.articolo_id,
            'tipo_eccezione', NEW.tipo_eccezione),
        NEW.tx_id,
        VARIADIC ARRAY[]::text[]);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_periodicita_canone()
IS 'Guard: una riga a canone di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni dice ogni quanto si addebita (E_RIGA_CANONE_SENZA_PERIODICITA, DATO_ERRATO, campo = periodicita). ADESIONE e OVERRIDE la ereditano dal listino prima di qui (script.trgfn_righe_default_periodicita_da_listino), l''AGGIUNTA la scrive l''operatore (F-9). L''ESCLUSIONE non ha erogazione e non si giudica. Una funzione per le due tabelle gemelle: il passaggio offerta → contratto copia la periodicita''. TG_ARGV[0] = colonna del documento padre, solo per il contesto. Trigger _a10_ BEFORE INSERT OR UPDATE OF tipo_erogazione, periodicita, dopo il default: parla prima dei CHECK chk_contrighe_canone_periodicita / chk_offerte_eccezioni_canone_periodicita, che restano la rete. Contesto: campo, riga_id, la colonna padre, articolo_id, tipo_eccezione. Nasce il 2026-11-01 (20261101-05), brief-db-contratto-righe-periodiche-in-commessa §6.11 (passo 4, la (b) di Tid del 2026-10-29: l''obbligo entra col form).';
```

</div>

---
{% include-markdown "signature-core.md" %}
