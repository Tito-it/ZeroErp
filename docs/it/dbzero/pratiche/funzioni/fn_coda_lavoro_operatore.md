{% include-markdown "it/dbzero/pratiche/manual/fn_coda_lavoro_operatore.md" %}
# ⚙️ Funzione `fn_coda_lavoro_operatore`

```sql
CREATE FUNCTION fn_coda_lavoro_operatore(p_risorsa_umana_id bigint, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_coda_lavoro_operatore(p_risorsa_umana_id bigint, p_emittente_fiscale_id bigint)
 RETURNS TABLE(livello text, flusso_id bigint, pratica_id bigint, pratica_codice text, pratica_descrizione text, priorita_codice character varying, tipo_prestazione_codice character varying, template_flusso_codice character varying, template_flusso_desc text, stato_flusso_codice character varying, sequenza integer, data_scadenza date, risorsa_assegnata text)
 LANGUAGE sql
 STABLE
AS $function$
-- Coda di lavoro operatore su quattro livelli (policy reparto-first §2.2):
--   ASSEGNATO > COMPETENZA (A/D) > REPARTO (B) > LIBERO (C).
-- Ogni flusso appare in un solo livello (il piu' alto applicabile).
WITH stati_pendenti AS (
    SELECT id, codice_interno
      FROM config.stati_flussi_pratiche
     WHERE codice_interno IN ('DA_ESEGUIRE', 'IN_CORSO')
),
operatore AS (
    -- Reparto ANAGRAFICO dell'operatore (NON i reparti-da-competenza)
    SELECT unita_organizzativa_id AS reparto_anagrafico
      FROM anagrafiche.risorse_umane
     WHERE id = p_risorsa_umana_id
),
competenze_op AS (
    -- Template per cui l'operatore ha competenza attiva (casi A/D)
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
        sf.codice_interno AS stato_codice,
        p.risorsa_umana_id AS pratica_risorsa
    FROM pratiche.flussi f
    JOIN stati_pendenti sf ON sf.id = f.stato_id
    JOIN pratiche.pratiche p ON p.id = f.pratica_id
    WHERE p.emittente_fiscale_id = p_emittente_fiscale_id
      -- Escludi pratiche TERMINALI (nessuna transizione di stato in uscita attiva)
      AND EXISTS (
          SELECT 1 FROM config.transizioni_stati_pratiche t
           WHERE t.stato_da_id = p.stato_id AND t.attivo
      )
),
classificati AS (
    SELECT
        fb.*,
        CASE
            -- ASSEGNATO: assegnato direttamente all'operatore
            WHEN fb.risorsa_umana_id = p_risorsa_umana_id
                THEN 'ASSEGNATO'
            -- COMPETENZA (A/D): prendibile per skill
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice = 'DA_ESEGUIRE'
                 AND EXISTS (SELECT 1 FROM competenze_op co
                              WHERE co.template_flusso_id = fb.template_flusso_id)
                THEN 'COMPETENZA'
            -- REPARTO (B): reparto anagrafico match, nessuno skill-lock attivo
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice = 'DA_ESEGUIRE'
                 AND fb.unita_organizzativa_id IS NOT NULL
                 AND fb.unita_organizzativa_id = (SELECT reparto_anagrafico FROM operatore)
                 AND NOT EXISTS (SELECT 1 FROM pratiche.competenze_flussi cf
                                  WHERE cf.template_flusso_id = fb.template_flusso_id
                                    AND cf.attivo = true)
                THEN 'REPARTO'
            -- LIBERO (C): niente reparto, niente skill-lock, pratica dell'operatore
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice = 'DA_ESEGUIRE'
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
    c.stato_codice,
    c.sequenza,
    COALESCE(c.flusso_scadenza, p.data_scadenza),
    -- risorsa_assegnata: i livelli mostrati sono auto-assegnato o non
    -- assegnati -> nessun "altro" da mostrare (NULL).
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
IS 'Coda di lavoro operatore su quattro livelli: ASSEGNATO, COMPETENZA (A/D), REPARTO (B, reparto anagrafico + no skill-lock), LIBERO (C, all''operatore della pratica). Esclude pratiche terminali.';
```

---
{% include-markdown "signature-core.md" %}
