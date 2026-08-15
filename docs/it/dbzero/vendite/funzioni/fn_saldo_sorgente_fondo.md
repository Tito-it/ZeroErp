{% include-markdown "it/dbzero/vendite/manual/fn_saldo_sorgente_fondo.md" %}
# ⚙️ Funzione `fn_saldo_sorgente_fondo`

```sql
CREATE FUNCTION fn_saldo_sorgente_fondo(p_fattura_sorgente_id bigint, p_source_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_saldo_sorgente_fondo(p_fattura_sorgente_id bigint, p_source_id bigint DEFAULT NULL::bigint)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_saldo               NUMERIC;
    v_saldo_contabile_tot NUMERIC;
    v_saldo_contabile_own NUMERIC;
BEGIN
    -- Guard di parametro: id nullo o non positivo e' un errore
    -- del chiamante, non un caso da normalizzare in silenzio.
    IF p_fattura_sorgente_id IS NULL OR p_fattura_sorgente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_saldo_sorgente_fondo', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_sorgente_id', 'valore', p_fattura_sorgente_id),
            NULL::uuid, 'p_fattura_sorgente_id obbligatorio e > 0');
    END IF;

    IF p_source_id IS NOT NULL AND p_source_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_saldo_sorgente_fondo', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_source_id', 'valore', p_source_id),
            NULL::uuid, 'p_source_id se fornito deve essere > 0');
    END IF;

    -- Primo termine: il residuo per MOVIMENTI.
    -- ⚠️ Oggi nessuna funzione del database scrive
    --    pagamenti.vendite_movimenti, quindi questo termine vale
    --    per costruzione totale_a_pagare. Diventera' vero con il
    --    posting (slice 1 del cantiere incassi): la formula e'
    --    scritta per quel giorno, non per oggi.
    SELECT sf.saldo INTO v_saldo
      FROM pagamenti.fn_get_saldo_fattura(p_fattura_sorgente_id) sf;

    -- Secondo termine: quanto e' gia' in lavorazione sulla sorgente.
    SELECT sc.saldo_contabile INTO v_saldo_contabile_tot
      FROM pagamenti.fn_get_saldo_fattura_contabili(p_fattura_sorgente_id) sc;

    -- Quota del secondo termine che appartiene a QUESTO fondo, e
    -- che va restituita: e' cio' che il fondo ha gia' scritto sulla
    -- sorgente, non un'altra copertura di cui tenere conto.
    -- Senza p_source_id la somma e' su zero righe, cioe' zero.
    SELECT COALESCE(SUM(cr.importo), 0)::NUMERIC INTO v_saldo_contabile_own
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
     WHERE cr.attivo IS TRUE
       AND st.is_postabile IS TRUE
       AND cr.fattura_id = p_fattura_sorgente_id
       AND p_source_id IS NOT NULL
       AND COALESCE(cr.meta ->> 'origine', '') = 'FONDO_FATTURA'
       AND COALESCE(cr.meta ->> 'fondo_source_id', '') = p_source_id::TEXT;

    RETURN COALESCE(v_saldo, 0)
         - (COALESCE(v_saldo_contabile_tot, 0) - COALESCE(v_saldo_contabile_own, 0));
END;
$function$

COMMENT ON FUNCTION vendite.fn_saldo_sorgente_fondo(p_fattura_sorgente_id bigint, p_source_id bigint)
IS 'Residuo della fattura sorgente al netto del contributo gia'' dato dal fondo indicato: saldo(movimenti) - (saldo contabile postabile - quota di questo fondo). Lo scorporo dell''ultimo termine e'' il punto: se il fondo e'' gia'' passato di li'', la riga contabile che ha creato sulla sorgente e'' dentro il saldo contabile, e confrontarci il fondo stesso significherebbe chiedergli di coprire cio'' che copre lui. p_source_id assente = nessun contributo proprio (prima applicazione). ⚠️ Deliberatamente NON STABLE: chiama due funzioni pagamenti.* dichiarate VOLATILE, e promettere stabilita'' su un valore che non lo e'' autorizza il planner a cache/inline sbagliati. Estratta il 2026-08-15 dalla copia inline di fn_sync_contabili_fondo_fattura (regola del 2, tre chiamanti previsti). D-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

---
{% include-markdown "signature-core.md" %}
