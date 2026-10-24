# ⚙️ Funzione `fn_check_righe_documento`

```sql
CREATE FUNCTION fn_check_righe_documento(p_documento character varying, p_documento_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_righe_documento(p_documento character varying, p_documento_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- =========================================================
-- Scopo:
--   Le righe ATTIVE di un'offerta o di un contratto che la riga intera
--   (script.fn_check_riga_documento_su_contesto) non ammette: un motivo
--   E_DOC_RIGA_NON_AMMESSA per riga, in ordine di riga. '[]' = tutte
--   ammesse.
--
-- ⭐ Perche' (brief-db-offerta-emissione-ed-erogazione §I.2; R-6 e A-5 di
--   brief-db-articoli-ammessi-per-documento): i guard di riga giudicano
--   la riga quando la si scrive, ma la regola dipende da dati che stanno
--   fuori (listino operativo, vocabolario del perimetro). Le righe gia'
--   scritte le intercetta il primo passo che le usa: l'emissione
--   dell'offerta, il push al contratto, l'attivazione del contratto. Guard
--   e capability di quei passi chiamano questa funzione: pulsante e
--   rifiuto non possono dissentire.
--
-- Il motivo e' del DOCUMENTO e nomina la riga: {codice
--   E_DOC_RIGA_NON_AMMESSA, reason RIGA_NON_AMMESSA, reason_key
--   common.azione_reason.riga_non_ammessa, valori [etichetta del
--   documento, codice dell'articolo], dettaglio {campo, documento,
--   documento_id, riga_id, articolo_id, motivo_riga}}: motivo_riga e' il
--   primo motivo della riga, col suo codice e la sua reason_key.
--
-- Il contesto del documento (listino operativo e i suoi articoli) si
--   legge UNA volta; per riga cambia solo tipo_eccezione.
-- =========================================================
DECLARE
    -- Nudi DICHIARATI: il contesto e i motivi sono jsonb composti.
    v_contesto jsonb;
    v_motivi   jsonb;
BEGIN
    IF p_documento IS NULL OR p_documento NOT IN ('OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'script.fn_check_righe_documento',
            'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    -- Il tipo d'eccezione e' obbligatorio per costruire il contesto di
    -- offerta e contratto; qui e' un segnaposto, sostituito riga per riga.
    v_contesto := script.fn_articolo_riga_contesto(
        p_documento, p_documento_id, 'AGGIUNTA'::vendite.tipo_eccezione_contratto);

    SELECT COALESCE(jsonb_agg(
               jsonb_build_object(
                   'codice',     'E_DOC_RIGA_NON_AMMESSA',
                   'reason',     'RIGA_NON_AMMESSA',
                   'reason_key', 'common.azione_reason.riga_non_ammessa',
                   'valori',     jsonb_build_array(v_contesto ->> 'etichetta', a.codice),
                   'dettaglio',  jsonb_build_object(
                                     'campo',        'articolo_id',
                                     'documento',    p_documento,
                                     'documento_id', p_documento_id,
                                     'riga_id',      g.riga_id,
                                     'articolo_id',  g.articolo_id,
                                     'motivo_riga',  g.motivo))
               ORDER BY g.riga_id), '[]'::jsonb)
      INTO v_motivi
      FROM (
          SELECT r.riga_id, r.articolo_id,
                 script.fn_check_riga_documento_su_contesto(
                     v_contesto || jsonb_build_object('tipo_eccezione', r.tipo_eccezione),
                     r.articolo_id, NULL, r.tipo_erogazione, r.fonte) -> 0 AS motivo
            FROM (
                SELECT e.id, e.articolo_id, e.tipo_eccezione,
                       e.tipo_erogazione, e.fonte_quantita_attesa
                  FROM vendite.offerte_commerciali_eccezioni e
                 WHERE p_documento = 'OFFERTA_COMMERCIALE'
                   AND e.offerta_id = p_documento_id
                   AND e.attivo
                UNION ALL
                SELECT cr.id, cr.articolo_id, cr.tipo_eccezione,
                       cr.tipo_erogazione, cr.fonte_quantita_attesa
                  FROM vendite.contratti_righe cr
                 WHERE p_documento = 'CONTRATTO'
                   AND cr.contratto_id = p_documento_id
                   AND cr.attivo
            ) r(riga_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte)
      ) g
      JOIN catalogo.articoli a ON a.id = g.articolo_id
     WHERE g.motivo IS NOT NULL;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_righe_documento(p_documento character varying, p_documento_id bigint)
IS 'Check (fn_check_*) di un''offerta (OFFERTA_COMMERCIALE) o di un contratto (CONTRATTO): un motivo per ogni riga ATTIVA che script.fn_check_riga_documento_su_contesto non ammette, in ordine di riga; ''[]'' = tutte ammesse. Altri documenti: E_DOC_TIPO_NON_GESTITO. Il motivo e'' del documento: codice E_DOC_RIGA_NON_AMMESSA, reason RIGA_NON_AMMESSA, reason_key common.azione_reason.riga_non_ammessa (debito verso il frontend), valori [etichetta del documento, codice dell''articolo], dettaglio {campo articolo_id, documento, documento_id, riga_id, articolo_id, motivo_riga = il primo motivo della riga}. Il contesto del documento si legge una volta (script.fn_articolo_riga_contesto). Lettori: vendite.trgfn_offerte_commerciali_guard_transizione e script.fn_available_actions_offerta (BOZZA->EMESSA; can_push_contratto da ACCETTATA), vendite.trgfn_contratti_guard_transizione_stato e script.fn_available_actions_contratto (->ATTIVO). Le righe gia'' scritte le intercetta il primo passo che le usa (R-6, A-5 di brief-db-articoli-ammessi-per-documento). STABLE, SECURITY INVOKER: sotto RLS. Nasce il 2026-10-21 (20261021-53), brief-db-offerta-emissione-ed-erogazione §I.2 (H-R1, H-R2, H-R4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
