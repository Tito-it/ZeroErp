# ⚙️ Funzione `trgfn_offerte_commerciali_rientro_padre`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_rientro_padre()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_rientro_padre()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: quando una revisione di offerta viene ANNULLATA, il padre
--   torna nello stato che le sue revisioni vive dicono: fuori dal
--   superamento se non ne resta nessuna. Lo decide e lo scrive la
--   proiezione vendite.fn_offerta_proietta_stato_revisione.
-- E' l'inverso di trgfn_offerte_commerciali_revisione: la regola di
--   dominio e' «una revisione abortita non rimpiazza nessuno».
-- rev 2026-10-26 (20261026-19, brief-modello-documento-vendita §13,
--   O-2): le condizioni sul padre, l'UPDATE e il letterale dello stato
--   passano alla proiezione, che scrive attraverso la porta. Qui
--   resta la causa: una revisione che entra in uno stato d'annullo.
BEGIN
    -- (1) Interessa solo il momento in cui lo stato DIVENTA di annullamento.
    --     Un UPDATE che lascia lo stato invariato, o che si muove fra due
    --     stati non abortiti, non ha niente a che vedere col rientro.
    IF NEW.stato_doc_offerta_id IS NOT DISTINCT FROM OLD.stato_doc_offerta_id THEN
        RETURN NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM config.stati_doc_offerte s
         WHERE s.id = NEW.stato_doc_offerta_id
           AND s.is_abortito IS TRUE
    ) OR EXISTS (
        SELECT 1 FROM config.stati_doc_offerte s
         WHERE s.id = OLD.stato_doc_offerta_id
           AND s.is_abortito IS TRUE
    ) THEN
        RETURN NULL;
    END IF;

    -- (2) Deve essere una revisione: senza padre non c'e' niente da riportare.
    IF NEW.revisione_padre_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- (3) Il padre, dalle sue revisioni vive. ⚠️ Ricorsione: la
    --     proiezione riaccende questo trigger sul padre, che entra in
    --     uno stato non abortito e si ferma alla condizione (1).
    PERFORM vendite.fn_offerta_proietta_stato_revisione(NEW.revisione_padre_id);

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_rientro_padre()
IS 'AFTER UPDATE OF stato_doc_offerta_id su vendite.offerte_commerciali (_z90_): quando una revisione ENTRA in uno stato d''annullo (is_abortito), chiama la proiezione vendite.fn_offerta_proietta_stato_revisione sul padre, che lo riporta dal superamento allo stato d''emissione (vocabolario) se non gli resta nessuna revisione viva, attraverso la porta. La regola «nessun rientro con una figlia viva» resta nel guard di transizione. Chi annulla la revisione lo conferma prima: il padre che torna emesso e'' un legame dell''annullo (vendite.fn_documento_legami, vendite.fn_annulla_offerta; O-4). rev 2026-10-26 (20261026-19, brief-modello-documento-vendita §13, O-2): prima scriveva il padre con un UPDATE suo e il letterale ''EMESSA'', e decideva qui le condizioni sul padre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
