{% include-markdown "it/dbzero/pratiche/manual/fn_coda_lavoro_operatore.md" %}
# ⚙️ Funzione `fn_coda_lavoro_operatore`

```sql
CREATE FUNCTION fn_coda_lavoro_operatore(p_risorsa_umana_id bigint, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_coda_lavoro_operatore(p_risorsa_umana_id bigint, p_emittente_fiscale_id bigint)
 RETURNS TABLE(livello text, flusso_id bigint, pratica_id bigint, pratica_codice text, pratica_descrizione text, priorita_codice character varying, tipo_prestazione_codice character varying, template_flusso_codice character varying, template_flusso_desc text, stato_flusso_codice_interno character varying, stato_flusso_codice character varying, stato_flusso_descrizione text, sequenza integer, data_scadenza date, risorsa_assegnata text)
 LANGUAGE sql
 STABLE
AS $function$
-- Coda di lavoro operatore su quattro livelli (policy reparto-first §2.2):
--   ASSEGNATO > COMPETENZA (A/D) > REPARTO (B) > LIBERO (C).
-- Ogni flusso appare in un solo livello (il piu' alto applicabile).
-- stato_codice_interno (interno alla query) = codice_interno per la LOGICA;
-- in output: stato_flusso_codice_interno (logica), stato_flusso_codice
-- (display = codice), stato_flusso_descrizione (display umano = descrizione).
WITH stati_pendenti AS (
    SELECT id, codice_interno, codice, descrizione
      FROM config.stati_flussi_pratiche
     WHERE codice_interno IN ('DA_ESEGUIRE', 'IN_CORSO')
),
operatore AS (
    SELECT unita_organizzativa_id AS reparto_anagrafico
      FROM anagrafiche.risorse_umane
     WHERE id = p_risorsa_umana_id
),
competenze_op AS (
    SELECT cf.template_flusso_id
      FROM pratiche.competenze_flussi cf
     WHERE cf.risorsa_umana_id = p_risorsa_umana_id
       AND cf.attivo = true
),
flussi_base AS (
    SELECT
        f.id AS flusso_id,
        f.pratica_id,
        f.template_flusso_id,
        f.risorsa_umana_id,
        f.unita_organizzativa_id,
        f.sequenza,
        f.data_scadenza AS flusso_scadenza,
        sf.codice_interno AS stato_codice_interno,
        sf.codice         AS stato_codice,
        sf.descrizione    AS stato_descrizione,
        p.risorsa_umana_id AS pratica_risorsa
    FROM pratiche.flussi f
    JOIN stati_pendenti sf ON sf.id = f.stato_id
    JOIN pratiche.pratiche p ON p.id = f.pratica_id
    WHERE p.emittente_fiscale_id = p_emittente_fiscale_id
      AND EXISTS (
          SELECT 1 FROM config.transizioni_stati_pratiche t
           WHERE t.stato_da_id = p.stato_id AND t.attivo
      )
),
classificati AS (
    SELECT
        fb.*,
        CASE
            WHEN fb.risorsa_umana_id = p_risorsa_umana_id
                THEN 'ASSEGNATO'
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice_interno = 'DA_ESEGUIRE'
                 AND EXISTS (SELECT 1 FROM competenze_op co
                              WHERE co.template_flusso_id = fb.template_flusso_id)
                THEN 'COMPETENZA'
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice_interno = 'DA_ESEGUIRE'
                 AND fb.unita_organizzativa_id IS NOT NULL
                 AND fb.unita_organizzativa_id = (SELECT reparto_anagrafico FROM operatore)
                 AND NOT EXISTS (SELECT 1 FROM pratiche.competenze_flussi cf
                                  WHERE cf.template_flusso_id = fb.template_flusso_id
                                    AND cf.attivo = true)
                THEN 'REPARTO'
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice_interno = 'DA_ESEGUIRE'
                 AND fb.unita_organizzativa_id IS NULL
                 AND fb.pratica_risorsa = p_risorsa_umana_id
                 AND NOT EXISTS (SELECT 1 FROM pratiche.competenze_flussi cf
                                  WHERE cf.template_flusso_id = fb.template_flusso_id
                                    AND cf.attivo = true)
                THEN 'LIBERO'
        END AS livello
    FROM flussi_base fb
)
SELECT
    c.livello,
    c.flusso_id,
    p.id,
    p.codice,
    p.descrizione,
    pp.codice_interno,
    tp.codice,
    tf.codice,
    tf.descrizione,
    c.stato_codice_interno,  -- -> stato_flusso_codice_interno (codice_interno)
    c.stato_codice,          -- -> stato_flusso_codice (codice, display)
    c.stato_descrizione,     -- -> stato_flusso_descrizione (descrizione, display umano)
    c.sequenza,
    COALESCE(c.flusso_scadenza, p.data_scadenza),
    NULL::text
FROM classificati c
JOIN pratiche.pratiche p ON p.id = c.pratica_id
JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
LEFT JOIN pratiche.template_flussi tf ON tf.id = c.template_flusso_id
WHERE c.livello IS NOT NULL
ORDER BY
    CASE c.livello
        WHEN 'ASSEGNATO'  THEN 1
        WHEN 'COMPETENZA' THEN 2
        WHEN 'REPARTO'    THEN 3
        WHEN 'LIBERO'     THEN 4
    END,
    pp.codice_interno DESC,
    COALESCE(c.flusso_scadenza, p.data_scadenza) NULLS LAST,
    c.sequenza;
$function$

COMMENT ON FUNCTION pratiche.fn_coda_lavoro_operatore(p_risorsa_umana_id bigint, p_emittente_fiscale_id bigint)
IS 'Coda di lavoro operatore su quattro livelli: ASSEGNATO, COMPETENZA (A/D), REPARTO (B, reparto anagrafico + no skill-lock), LIBERO (C, all''operatore della pratica). Esclude pratiche terminali. Espone stato_flusso_codice_interno (codice_interno, logica), stato_flusso_codice (codice, display) e stato_flusso_descrizione (descrizione, display umano). rev 2026-07-01 (display descrizione stato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
