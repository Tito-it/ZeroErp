{% include-markdown "it/dbzero/script/manual/fn_check_prezzi_in_attesa.md" %}
# ⚙️ Funzione `fn_check_prezzi_in_attesa`

```sql
CREATE FUNCTION fn_check_prezzi_in_attesa(p_testata regclass, p_documento_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_prezzi_in_attesa(p_testata regclass, p_documento_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dei motivi di script.fn_check_prezzi_autorizzati, il SOLO
--   prezzo in attesa di approvazione. Chi lo chiede: la creazione di
--   una revisione (preventivo e offerta), nella madre che la crea e nel
--   pulsante che la propone.
-- ⚠️ plpgsql e non un corpo SQL `RETURN`: e' la forma di tutti gli altri
--   changeSet, quella che dbops/test-riferimenti-morti-v1 compila, e il
--   driver la spezza senza sorprese (vedi 20260921-21, BEGIN ATOMIC).
BEGIN
    -- ⚠️ `[]` e non NULL quando non c'e' niente: i consumatori sommano
    --   array e leggono jsonb_array_length.
    RETURN (
        SELECT COALESCE(jsonb_agg(m.motivo ORDER BY m.pos), '[]'::jsonb)
          FROM jsonb_array_elements(
                   script.fn_check_prezzi_autorizzati(p_testata, p_documento_id))
               WITH ORDINALITY AS m(motivo, pos)
         WHERE m.motivo ->> 'codice' = 'E_DOC_PREZZO_PENDENTE');
END;
$function$

COMMENT ON FUNCTION script.fn_check_prezzi_in_attesa(p_testata regclass, p_documento_id bigint)
IS 'Building block: dei motivi di script.fn_check_prezzi_autorizzati, il SOLO prezzo in attesa di approvazione (E_DOC_PREZZO_PENDENTE) — [] se non ce ne sono. Decide se di un documento si puo'' creare una REVISIONE: la usano le madri vendite.fn_crea_revisione_preventivo / fn_crea_revisione_offerta (che sollevano il primo motivo) e le capability fn_available_actions_preventivo / fn_available_actions_offerta (che spengono «Crea revisione» col motivo). ⭐ Perche'': le revisioni ricopiano stato e pratica di approvazione 1:1, e una riga in attesa ricopiata restava legata alla pratica della revisione vecchia — in attesa per sempre. Decisione di Tid del 2026-09-24: la revisione non si crea finche'' c''e'' un prezzo in attesa; approvato e rifiutato si ricopiano come prima (azzerarli farebbe passare un prezzo rifiutato). ⚠️ Il rifiutato qui NON conta, ed e'' voluto. Brief: brief-db-preventivi-congelamento-pricing §10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
