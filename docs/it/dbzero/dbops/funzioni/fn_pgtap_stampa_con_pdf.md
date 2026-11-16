{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_stampa_con_pdf.md" %}
# ⚙️ Funzione `fn_pgtap_stampa_con_pdf`

```sql
CREATE FUNCTION fn_pgtap_stampa_con_pdf(p_insert_stampa text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_stampa_con_pdf(p_insert_stampa text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, una stampa col suo PDF principale. Solo per i pgTAP.
-- Uso:
--   SELECT dbops.fn_pgtap_stampa_con_pdf($$INSERT INTO documenti.documenti_generati (…) SELECT …$$);
--   SELECT is(dbops.fn_pgtap_codice_errore(
--            $$SELECT dbops.fn_pgtap_stampa_con_pdf($i$INSERT …$i$)$$), NULL, 'passa');
DECLARE
    v_id documenti.documenti_generati.id%TYPE;
BEGIN
    SET CONSTRAINTS documenti.trg_documenti_generati_a10_guard_file_principale_ins DEFERRED;

    EXECUTE p_insert_stampa || ' RETURNING id' INTO STRICT v_id;

    INSERT INTO documenti.documenti_generati_file (
        documento_generato_id, file_tipo_id, mime_type, file_name,
        file_size_bytes, storage_key, sha256, ordinamento, is_principale)
    SELECT g.id, t.id, 'application/pdf', g.nome_file,
           1024, 'pgtap/stampe/' || g.uid::text || '.pdf', repeat('f', 64), 1, true
      FROM documenti.documenti_generati g
      CROSS JOIN documenti.tipi_file_documento t
     WHERE g.id = v_id
       AND t.codice_interno = 'PDF_FINALE';

    -- IMMEDIATE fa scattare adesso il guard rimasto in sospeso: la stampa
    -- si giudica qui, non al ROLLBACK del test (che non giudica niente).
    SET CONSTRAINTS documenti.trg_documenti_generati_a10_guard_file_principale_ins IMMEDIATE;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_stampa_con_pdf(p_insert_stampa text)
IS 'Fixture pgTAP (building block): esegue l''INSERT di una stampa ricevuto come testo (senza RETURNING), scrive il suo PDF principale (tipo PDF_FINALE) e rende l''id della stampa. Due istruzioni, come il servizio: in una CTE sola la policy del file non vedrebbe la stampa. Apre la finestra differita del solo trg_documenti_generati_a10_guard_file_principale_ins e la richiude con IMMEDIATE, che fa giudicare subito il guard; gli altri vincoli restano come il test li ha messi. SECURITY INVOKER: scrive sotto le policy di chi chiama. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
