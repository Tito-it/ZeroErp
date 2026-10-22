{% include-markdown "it/dbzero/script/manual/fn_check_fattura_emettibile.md" %}
# ⚙️ Funzione `fn_check_fattura_emettibile`

```sql
CREATE FUNCTION fn_check_fattura_emettibile(p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_fattura_emettibile(p_fattura_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'EMISSIONE di una
--   fattura. Funzione PURA (fn_check_*): non solleva, non scrive.
--   Consumatore: vendite.trgfn_fatture_guard_stato, che solleva
--   il primo motivo entrando in EMESSA.
--   Gemella di script.fn_check_preventivo_emettibile.
-- Ritorna: [] se emettibile; altrimenti array ORDINATO di
--   {codice, reason, dettaglio, valori}.
DECLARE
    v_motivi    jsonb := '[]'::jsonb;
    v_numero    vendite.fatture.numero%TYPE;
    v_trovata   boolean;
    v_riga_id   vendite.fatture_righe.id%TYPE;
    v_riga_nr   vendite.fatture_righe.riga_nr%TYPE;
    v_riga_des  vendite.fatture_righe.descrizione%TYPE;
    v_articolo  vendite.fatture_righe.articolo_id%TYPE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_fattura_emettibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'fattura_id', 'valore', p_fattura_id),
            NULL::uuid, 'fattura_id obbligatorio (>0)');
    END IF;

    SELECT true, f.numero INTO v_trovata, v_numero
      FROM vendite.fatture f
     WHERE f.id = p_fattura_id;

    IF v_trovata IS NULL THEN
        RETURN v_motivi;   -- fattura inesistente: decide il chiamante
    END IF;

    -- MOTIVO 1 — ALIQUOTA DELLA RIGA: ogni riga entra nel
    --   riepilogo IVA (vendite.fn_ricalcola_riepilogo_iva_fattura
    --   aggrega tutte le righe, senza filtri) e nella fattura
    --   elettronica, che vuole l'aliquota su ogni linea.
    -- ⚠️ ORDER BY prima del LIMIT: il messaggio nomina sempre la
    --   stessa riga, la prima per numero.
    SELECT r.id, r.riga_nr, r.descrizione, r.articolo_id
      INTO v_riga_id, v_riga_nr, v_riga_des, v_articolo
      FROM vendite.fatture_righe r
     WHERE r.fattura_id = p_fattura_id
       AND r.iva_id IS NULL
     ORDER BY r.riga_nr, r.id
     LIMIT 1;

    IF v_riga_id IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_FATTURA_RIGA_IVA_MANCANTE',
            'reason',     'RIGA_SENZA_ALIQUOTA',
            'dettaglio',  jsonb_build_object(
                              'riga_id',     v_riga_id,
                              'riga_nr',     v_riga_nr,
                              'articolo_id', v_articolo,
                              'descrizione', v_riga_des),
            'valori',     jsonb_build_array(
                              COALESCE(v_numero::text, p_fattura_id::text),
                              v_riga_nr::text,
                              COALESCE(v_riga_des::text, 'senza descrizione')));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_fattura_emettibile(p_fattura_id bigint)
IS 'Check PURA: i motivi che impediscono l''EMISSIONE di una fattura; [] = emettibile, altrimenti l''array ordinato {codice, reason, dettaglio, valori}. Motivo 1: E_FATTURA_RIGA_IVA_MANCANTE, una riga senza aliquota IVA (iva_id NULL) — ogni riga, perche'' il riepilogo IVA le aggrega tutte e la fattura elettronica vuole l''aliquota su ogni linea; valori: numero (o id) della fattura, riga_nr, descrizione; dettaglio: riga_id, riga_nr, articolo_id, descrizione. Consumatore: vendite.trgfn_fatture_guard_stato, entrando in EMESSA. Gemella di script.fn_check_preventivo_emettibile: chiude per la fattura la decisione di Tid del 2026-08-29 (bozza libera, cancello all''emissione, guardia nel riepilogo; D-3 del 2026-10-22). Richiesta BE §9.9 di brief-be-utenti-di-sviluppo. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
