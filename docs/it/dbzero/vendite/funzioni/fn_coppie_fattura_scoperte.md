{% include-markdown "it/dbzero/vendite/manual/fn_coppie_fattura_scoperte.md" %}
# ⚙️ Funzione `fn_coppie_fattura_scoperte`

```sql
CREATE FUNCTION fn_coppie_fattura_scoperte(p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_coppie_fattura_scoperte(p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(emittente_soggetto_ruolo_id bigint, tipo_doc_fiscale_id bigint, natura_doc_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
#variable_conflict use_column
BEGIN
    -- =========================================================
    -- Scopo:
    --   Le coppie (tipo documento, natura) per cui un emittente
    --   non ha un registro delle fatture: quelle su cui
    --   vendite.fn_get_registro_id solleverebbe
    --   «registro non risolto».
    --
    -- Regole:
    --   - p_emittente_soggetto_ruolo_id NULL = tutti gli
    --     emittenti attivi;
    --   - solo tipi documento e nature attivi;
    --   - «coperta» = fn_lookup_registro_id risponde con
    --     utility NULL: si chiama il lookup, non lo si riscrive.
    -- =========================================================
    RETURN QUERY
    SELECT ef.soggetto_ruolo_id, t.id, n.id
      FROM anagrafiche.emittenti_fiscali ef
     CROSS JOIN config.tipi_doc_fiscale t
     CROSS JOIN config.nature_doc_fiscale n
     WHERE (p_emittente_soggetto_ruolo_id IS NULL
            OR ef.soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
       AND ef.attivo IS TRUE
       AND t.attivo IS TRUE
       AND n.attivo IS TRUE
       AND NOT EXISTS (
             SELECT 1
               FROM vendite.fn_lookup_registro_id(
                        p_tipo_doc_fiscale_id         => t.id,
                        p_natura_doc_id               => n.id,
                        p_utility_id                  => NULL,
                        p_emittente_soggetto_ruolo_id => ef.soggetto_ruolo_id) k
              WHERE k.registro_id IS NOT NULL)
     ORDER BY ef.soggetto_ruolo_id, t.id, n.id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_coppie_fattura_scoperte(p_emittente_soggetto_ruolo_id bigint)
IS 'LETTORE (2026-10-18): per ogni emittente ATTIVO (o per quello indicato), le coppie (tipo documento attivo, natura attiva) che vendite.fn_lookup_registro_id non sa risolvere con utility NULL, cioe'' i documenti per cui vendite.fn_get_registro_id solleverebbe «registro non risolto». ⭐ La copertura la decide il lookup, CHIAMATO e non riscritto: non puo'' dire una cosa diversa da quella che vede chi emette. Un registro legato a UNA utility non copre le altre. Un emittente spento non e'' un buco: lo provisiona il trigger su anagrafiche.emittenti_fiscali quando si riaccende. Lettori: vendite.fn_provision_registri (registro standard delle fatture e suoi collegamenti, 20261019-08), il pgTAP vendite/test-registro-fattura-nasce-con-emittente-v1. R-BE-14, D-14a … D-14d di Tid, brief-db-processi-accensione-per-ambiente §6.14.';
```

---
{% include-markdown "signature-core.md" %}
