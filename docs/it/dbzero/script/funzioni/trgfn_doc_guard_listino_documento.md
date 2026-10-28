# ⚙️ Funzione `trgfn_doc_guard_listino_documento`

```sql
CREATE FUNCTION trgfn_doc_guard_listino_documento()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_guard_listino_documento()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- Scopo: rifiutare un contratto o un'offerta il cui listino non e'
--   della utility o dell'emittente del documento (F-2 di Tid,
--   2026-10-08): solleva il primo motivo di
--   script.fn_check_listino_documento, col campo listino_id. Il
--   predicato sta nella check: qui si solleva soltanto
--   (linee-guida-sql §12.5.2).
-- Uso:   BEFORE INSERT, e BEFORE UPDATE WHEN cambiano listino_id,
--        utility_id o emittente_fiscale_id, fascia _a10_, su
--        vendite.contratti e vendite.offerte_commerciali.
-- TG_ARGV[0]: documento (CONTRATTO | OFFERTA_COMMERCIALE), solo per il contesto.
DECLARE
    -- Tipo nudo DICHIARATO: un selettore del trigger, nessuna colonna.
    v_documento text := TG_ARGV[0];
    v_motivi    jsonb;
BEGIN
    v_motivi := script.fn_check_listino_documento(
        NEW.listino_id, NEW.utility_id, NEW.emittente_fiscale_id);

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        v_motivi,
        v_motivi -> 0 -> 'dettaglio' ->> 'campo',
        NEW.tx_id,
        jsonb_build_object('documento', v_documento,
                           'documento_id', NEW.id,
                           'utility_id', NEW.utility_id,
                           'emittente_fiscale_id', NEW.emittente_fiscale_id));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_guard_listino_documento()
IS 'Guard generico (vendite.contratti, vendite.offerte_commerciali): solleva il primo motivo di script.fn_check_listino_documento — E_DOC_LISTINO_UTILITY_DIVERSA o E_DOC_LISTINO_EMITTENTE_DIVERSO — col campo listino_id (canale COLUMN). Il listino di un documento è della sua utility e del suo emittente (decisione F-2 di Tid del 2026-10-08). TG_ARGV[0] = documento (CONTRATTO | OFFERTA), solo per il contesto. Montato BEFORE INSERT e BEFORE UPDATE quando cambiano listino_id, utility_id o emittente_fiscale_id (le righe già scritte restano come sono), dopo a10_default_emittente e a10_guard_emittente_ba. Listino NULL (negoziato puro del contratto): nessun rifiuto. Nasce il 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2. ⭐ rev 2026-10-19 (20261019-70, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
