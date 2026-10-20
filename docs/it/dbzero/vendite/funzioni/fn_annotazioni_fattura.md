{% include-markdown "it/dbzero/vendite/manual/fn_annotazioni_fattura.md" %}
# ⚙️ Funzione `fn_annotazioni_fattura`

```sql
CREATE FUNCTION fn_annotazioni_fattura(p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annotazioni_fattura(p_fattura_id bigint)
 RETURNS TABLE(codice text, testo text, ordine integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: le annotazioni di legge che la fattura p_fattura_id deve
--   stampare, una riga per voce, nell'ordine di stampa. Nessuna
--   voce = nessuna riga.
DECLARE
    v_regime  anagrafiche.emittenti_fiscali.regime_fiscale_rf%TYPE;
BEGIN
    -- Guard di parametro: un id nullo o non positivo lo produce solo
    -- un chiamante rotto (TECNICO).
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_annotazioni_fattura', 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id),
            NULL::uuid,
            'vendite.fn_annotazioni_fattura',
            'p_fattura_id obbligatorio e maggiore di zero');
    END IF;

    v_regime := vendite.fn_regime_fiscale_fattura(p_fattura_id);

    RETURN QUERY
    SELECT v.codice, v.testo, v.ordine
      FROM (
            -- ESIGIBILITA_DIFFERITA: regime per cassa e almeno una
            -- riga differita (sezione 8.7 del brief).
            SELECT 'ESIGIBILITA_DIFFERITA'::text AS codice,
                   rf.annotazione_documento     AS testo,
                   10                           AS ordine
              FROM config.regimi_fiscali rf
             WHERE rf.codice_interno = v_regime
               AND rf.iva_per_cassa
               AND EXISTS (SELECT 1
                             FROM vendite.fatture_righe r
                            WHERE r.fattura_id = p_fattura_id
                              AND r.esigibilita = 'D')
           ) v
     ORDER BY v.ordine, v.codice;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annotazioni_fattura(p_fattura_id bigint)
IS 'Le annotazioni di legge che una fattura deve stampare: una riga (codice, testo, ordine) per voce, nell''ordine di stampa; nessuna voce = nessuna riga. Oggi una voce, ESIGIBILITA_DIFFERITA: il regime della fattura (vendite.fn_regime_fiscale_fattura, lo stesso delle righe) e'' per cassa e almeno una riga e'' a esigibilita'' D; testo da config.regimi_fiscali.annotazione_documento. Le voci future sono righe nuove di questa funzione, senza forma nuova del contesto ne'' versione nuova del template. La legge il builder della fattura (forma 4). Solleva E_VENDITE_CHIAMATA_NON_VALIDA su un id nullo o non positivo. Brief: brief-db-esigibilita-iva-per-cassa-emittente (R-DB-3, AN-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
