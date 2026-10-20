# ⚙️ Funzione `fn_pgtap_crea_sorgente`

```sql
CREATE FUNCTION fn_pgtap_crea_sorgente(p_codice_interno character varying, p_target_table regclass)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_sorgente(p_codice_interno character varying, p_target_table regclass DEFAULT NULL::regclass)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: una sorgente di PROVA per un pgTAP, costruita e non
--   pescata: un tipo di documento che il catalogo non ha.
--   Serve dal 2026-10-20 a chi costruisce una famiglia di
--   numerazione di prova (la famiglia E' una sorgente, FK
--   fk_famiglie_documento_sorgenti, G-5) o un ambito di prova.
-- Parametri: p_codice_interno, il codice; p_target_table, la
--   tabella dei documenti (NULL = nessuna: e' il caso del
--   riferimento che manca).
-- Ritorna: l'id della sorgente.
-- ⚠️ config.sorgenti.id non ha default (gli id li dà il CSV di
--   80_data): qui il primo libero, dentro la transazione del test.
-- ⚠️ Spenta come documento: apribile falso, scope CATALOGO,
--   etichetta = codice. Il test la vede, nessuna lista sì.
-- Uso: PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP_FAM_X');
-- Brief: brief-db-grammatica-unica-documenti §13 (2c).
-- =========================================================
DECLARE
    v_id config.sorgenti.id%TYPE;
BEGIN
    SELECT COALESCE(max(s.id), 0) + 1 INTO v_id FROM config.sorgenti s;

    INSERT INTO config.sorgenti (
        id, codice_interno, codice, categoria, descrizione, attivo, meta,
        target_table, key_selector, scope, apribile, etichetta)
    VALUES (
        v_id, p_codice_interno, p_codice_interno, 'DOCUMENTO',
        'Sorgente di prova pgTAP', true, jsonb_build_object('pgtap', true),
        p_target_table, 'id', 'CATALOGO', false, p_codice_interno);

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_sorgente(p_codice_interno character varying, p_target_table regclass)
IS 'Builder pgTAP: una sorgente di PROVA (codice, tabella dei documenti opzionale), costruita e non pescata; ritorna l''id, il primo libero (config.sorgenti.id non ha default). Spenta come documento: apribile falso, scope CATALOGO. Serve a chi costruisce una famiglia di numerazione di prova, che dal 2026-10-20 e'' una sorgente (G-5). Brief: brief-db-grammatica-unica-documenti §13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
