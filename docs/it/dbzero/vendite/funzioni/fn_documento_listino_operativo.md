{% include-markdown "it/dbzero/vendite/manual/fn_documento_listino_operativo.md" %}
# ⚙️ Funzione `fn_documento_listino_operativo`

```sql
CREATE FUNCTION fn_documento_listino_operativo(p_documento character varying, p_documento_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_listino_operativo(p_documento character varying, p_documento_id bigint)
 RETURNS TABLE(listino_id bigint, listino_versione_id bigint, tipo_variazione_globale character varying, valore_variazione_globale numeric)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: la versione di listino che governa le righe di un
--   contratto o di un'offerta, con la variazione globale.
--   Versione fissata se c'e'; altrimenti quella in vigore oggi;
--   NULL senza listino. La regola e' vendite.fn_listino_versione_operativa
--   (rev 2026-10-07, la stessa che congela all'emissione e all'attivazione).
-- Ritorna: zero righe se il documento non c'e' (o non si vede).
-- ⚠️ p_documento e' il codice della sorgente (CONTRATTO |
--   OFFERTA_COMMERCIALE), ancorato a config.sorgenti.codice_interno
--   (grammatica unica dei tipi di documento, lotto 1). p_documento_id
--   nudo DICHIARATO: un id polimorfo (due testate).
BEGIN
    IF p_documento = 'CONTRATTO' THEN
        RETURN QUERY
        SELECT c.listino_id,
               vendite.fn_listino_versione_operativa(c.listino_id, c.listino_versione_id),
               c.tipo_variazione_globale,
               c.valore_variazione_globale
          FROM vendite.contratti c
         WHERE c.id = p_documento_id;

    ELSIF p_documento = 'OFFERTA_COMMERCIALE' THEN
        RETURN QUERY
        SELECT o.listino_id,
               vendite.fn_listino_versione_operativa(o.listino_id, o.listino_versione_id),
               o.tipo_variazione_globale,
               o.valore_variazione_globale
          FROM vendite.offerte_commerciali o
         WHERE o.id = p_documento_id;

    ELSE
        -- Errore di CHIAMANTE, non di dato (stesso codice del
        -- lettore di stato delle testate).
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_documento_listino_operativo',
            'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento',    p_documento,
                               'documento_id', p_documento_id),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_listino_operativo(p_documento character varying, p_documento_id bigint)
IS 'La versione di listino che governa le righe di un documento di vendita con eccezioni (p_documento = CONTRATTO | OFFERTA): listino_versione_id della testata se fissata (attivazione del contratto, emissione dell''offerta), altrimenti la versione in vigore oggi (vendite.fn_listino_versione_in_vigore: ATTIVA o CHIUSA, la BOZZA non e'' operativa), NULL senza listino. Porta anche la variazione globale della testata. Zero righe se il documento non c''e'' o non si vede (INVOKER, testate in RLS). Altro p_documento: E_DOC_TIPO_NON_GESTITO. Sede unica (regola del 2) per script.fn_check_esclusione_articolo_documento, script.trgfn_righe_guard_aggiunta_fuori_listino e vendite.fn_documento_righe_preview, che prima la riscrivevano ciascuno per il solo contratto. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R4, R5). Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.3): la versione la chiede a vendite.fn_listino_versione_operativa, la stessa regola sui valori con cui i guard congelano la versione all''emissione dell''offerta e all''attivazione del contratto. ⭐ rev 2026-10-19 (20261019-18, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

---
{% include-markdown "signature-core.md" %}
