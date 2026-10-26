{% include-markdown "it/dbzero/vendite/manual/fn_documento_righe_eccezione.md" %}
# ⚙️ Funzione `fn_documento_righe_eccezione`

```sql
CREATE FUNCTION fn_documento_righe_eccezione(p_documento character varying, p_documento_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_righe_eccezione(p_documento character varying, p_documento_id bigint)
 RETURNS TABLE(id bigint, articolo_id uuid, tipo_eccezione vendite.tipo_eccezione_contratto, prezzo_unitario numeric, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, tipo_erogazione character varying, fonte_quantita_attesa character varying, ordine smallint, attivo boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: le righe eccezione (OVERRIDE, ESCLUSIONE, AGGIUNTA) di un
--   contratto o di un'offerta, con le stesse colonne. Tutte, attive
--   e no: filtra chi legge.
-- ⚠️ p_documento e' il codice della sorgente (CONTRATTO |
--   OFFERTA_COMMERCIALE), ancorato a config.sorgenti.codice_interno
--   (grammatica unica dei tipi di documento, lotto 1). p_documento_id
--   nudo DICHIARATO: un id polimorfo (due testate).
BEGIN
    IF p_documento = 'CONTRATTO' THEN
        RETURN QUERY
        SELECT cr.id, cr.articolo_id, cr.tipo_eccezione, cr.prezzo_unitario,
               cr.quantita, cr.qta_operativa, cr.uom_operativa_id,
               cr.tipo_erogazione, cr.fonte_quantita_attesa, cr.ordine,
               cr.attivo
          FROM vendite.contratti_righe cr
         WHERE cr.contratto_id = p_documento_id;

    ELSIF p_documento = 'OFFERTA_COMMERCIALE' THEN
        RETURN QUERY
        SELECT oe.id, oe.articolo_id, oe.tipo_eccezione, oe.prezzo_unitario,
               oe.quantita, oe.qta_operativa, oe.uom_operativa_id,
               oe.tipo_erogazione, oe.fonte_quantita_attesa, oe.ordine,
               oe.attivo
          FROM vendite.offerte_commerciali_eccezioni oe
         WHERE oe.offerta_id = p_documento_id;

    ELSE
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_documento_righe_eccezione',
            'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento',    p_documento,
                               'documento_id', p_documento_id),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_righe_eccezione(p_documento character varying, p_documento_id bigint)
IS 'Le righe eccezione (OVERRIDE, ESCLUSIONE, AGGIUNTA) di un contratto (vendite.contratti_righe) o di un''offerta (vendite.offerte_commerciali_eccezioni), con le stesse colonne: le due tabelle sono gemelle per progetto. p_documento = CONTRATTO | OFFERTA; altro valore: E_DOC_TIPO_NON_GESTITO. Tutte le righe, attive e no. INVOKER: legge sotto la RLS di chi chiede. Colonne ancorate a contratti_righe (stesso tipo base sull''offerta; una funzione non porta il typmod). Consumatore: vendite.fn_documento_righe_preview, che senza di lei sceglierebbe la tabella in tre punti. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R4). ⭐ rev 2026-10-19 (20261019-19, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
