{% include-markdown "it/dbzero/vendite/manual/fn_documento_listino_operativo.md" %}
# ⚙️ Funzione `fn_documento_listino_operativo`

```sql
CREATE FUNCTION fn_documento_listino_operativo(p_documento text, p_documento_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_listino_operativo(p_documento text, p_documento_id bigint)
 RETURNS TABLE(listino_id bigint, listino_versione_id bigint, tipo_variazione_globale character varying, valore_variazione_globale numeric)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la versione di listino che governa le righe di un
--   contratto o di un'offerta, con la variazione globale.
--   Versione fissata se c'e'; altrimenti quella in vigore oggi
--   (fn_listino_versione_in_vigore); NULL senza listino.
-- Ritorna: zero righe se il documento non c'e' (o non si vede).
-- ⚠️ p_documento e p_documento_id nudi DICHIARATI: un selettore
--   senza colonna-vocabolario e un id polimorfo (due testate).
BEGIN
    IF p_documento = 'CONTRATTO' THEN
        RETURN QUERY
        SELECT c.listino_id,
               COALESCE(c.listino_versione_id,
                        CASE WHEN c.listino_id IS NOT NULL THEN
                            vendite.fn_listino_versione_in_vigore(c.listino_id, CURRENT_DATE)
                        END),
               c.tipo_variazione_globale,
               c.valore_variazione_globale
          FROM vendite.contratti c
         WHERE c.id = p_documento_id;

    ELSIF p_documento = 'OFFERTA' THEN
        -- listino_id e' NOT NULL sull'offerta: il CASE resta per
        -- dire la stessa regola con le stesse parole.
        RETURN QUERY
        SELECT o.listino_id,
               COALESCE(o.listino_versione_id,
                        CASE WHEN o.listino_id IS NOT NULL THEN
                            vendite.fn_listino_versione_in_vigore(o.listino_id, CURRENT_DATE)
                        END),
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

COMMENT ON FUNCTION vendite.fn_documento_listino_operativo(p_documento text, p_documento_id bigint)
IS 'La versione di listino che governa le righe di un documento di vendita con eccezioni (p_documento = CONTRATTO | OFFERTA): listino_versione_id della testata se fissata (attivazione del contratto, emissione dell''offerta), altrimenti la versione in vigore oggi (vendite.fn_listino_versione_in_vigore: ATTIVA o CHIUSA, la BOZZA non e'' operativa), NULL senza listino. Porta anche la variazione globale della testata. Zero righe se il documento non c''e'' o non si vede (INVOKER, testate in RLS). Altro p_documento: E_DOC_TIPO_NON_GESTITO. Sede unica (regola del 2) per script.fn_check_esclusione_articolo_documento, script.trgfn_righe_guard_aggiunta_fuori_listino e vendite.fn_documento_righe_preview, che prima la riscrivevano ciascuno per il solo contratto. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R4, R5).';
```

---
{% include-markdown "signature-core.md" %}
