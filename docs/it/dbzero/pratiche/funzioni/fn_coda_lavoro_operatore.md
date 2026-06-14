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
-- Scopo: restituire la coda di lavoro di un operatore in tre livelli
--        di priorita': flussi assegnati, flussi per competenza, flussi del reparto.
-- Parametri:
--   p_risorsa_umana_id: operatore per cui costruire la coda
--   p_emittente_fiscale_id: filtro emittente fiscale (segregazione multi-company)
-- Livelli (mutualmente esclusivi, priorita' decrescente):
--   ASSEGNATO   — flussi DA_ESEGUIRE/IN_CORSO assegnati direttamente
--   COMPETENZA  — flussi DA_ESEGUIRE non assegnati, operatore ha competenza attiva
--   REPARTO     — flussi DA_ESEGUIRE/IN_CORSO del reparto (esclusi i precedenti)
-- Ogni flusso appare in un solo livello (quello piu' alto applicabile).
-- Ordinamento: livello → priorita' (DESC) → scadenza (NULLS LAST) → sequenza
-- Implementazione: singola scansione flussi_base + classificazione CASE WHEN

-- Strategia: CTE base con i flussi pendenti dell'emittente,
-- poi classificazione in un singolo passaggio con CASE WHEN.
-- Evita 3 scansioni separate e elimina il rischio di duplicati
-- tra livelli COMPETENZA e REPARTO.

WITH stati_pendenti AS (
    -- Risolvi id degli stati pendenti da codice_interno (una sola volta)
    SELECT id, codice_interno
      FROM config.stati_flussi_pratiche
     WHERE codice_interno IN ('DA_ESEGUIRE', 'IN_CORSO')
),
competenze_op AS (
    -- Competenze attive dell'operatore (template + reparto)
    SELECT cf.template_flusso_id, cf.unita_organizzativa_id
      FROM pratiche.competenze_flussi cf
     WHERE cf.risorsa_umana_id = p_risorsa_umana_id
       AND cf.attivo = true
),
flussi_base AS (
    -- Singola scansione: tutti i flussi pendenti dell'emittente
    SELECT
        f.id AS flusso_id,
        f.pratica_id,
        f.template_flusso_id,
        f.risorsa_umana_id,
        f.unita_organizzativa_id,
        f.sequenza,
        f.data_scadenza AS flusso_scadenza,
        sf.codice_interno AS stato_codice
    FROM pratiche.flussi f
    JOIN stati_pendenti sf ON sf.id = f.stato_id
    JOIN pratiche.pratiche p ON p.id = f.pratica_id
    WHERE p.emittente_fiscale_id = p_emittente_fiscale_id
      -- Escludi pratiche TERMINALI (concluse): i loro flussi sono
      -- congelati dal guard trgfn_flussi_guard_pratica_terminale e
      -- non sono lavoro da fare. "Terminale" = stato senza alcuna
      -- transizione di stato in uscita attiva (stessa definizione
      -- del guard: nessun id/codice hardcodato).
      AND EXISTS (
          SELECT 1
            FROM config.transizioni_stati_pratiche t
           WHERE t.stato_da_id = p.stato_id
             AND t.attivo
      )
),
classificati AS (
    -- Classifica ogni flusso nel livello piu' alto applicabile
    SELECT
        fb.*,
        CASE
            -- Livello 1: assegnato direttamente all'operatore
            WHEN fb.risorsa_umana_id = p_risorsa_umana_id
                THEN 'ASSEGNATO'
            -- Livello 2: non assegnato, DA_ESEGUIRE, operatore ha competenza
            WHEN fb.risorsa_umana_id IS NULL
                 AND fb.stato_codice = 'DA_ESEGUIRE'
                 AND EXISTS (SELECT 1 FROM competenze_op co
                              WHERE co.template_flusso_id = fb.template_flusso_id)
                THEN 'COMPETENZA'
            -- Livello 3: nel reparto dell'operatore (visibilita')
            WHEN fb.unita_organizzativa_id IN
                 (SELECT co.unita_organizzativa_id FROM competenze_op co)
                THEN 'REPARTO'
        END AS livello
    FROM flussi_base fb
)
-- Risultato finale: JOIN display fields una sola volta
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
    -- risorsa_assegnata: solo per REPARTO (mostra chi ha il flusso)
    CASE WHEN c.livello = 'REPARTO'
         THEN sog.ragione_sociale_completa
         ELSE NULL
    END
FROM classificati c
JOIN pratiche.pratiche p ON p.id = c.pratica_id
JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
LEFT JOIN pratiche.template_flussi tf ON tf.id = c.template_flusso_id
LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = c.risorsa_umana_id
LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
LEFT JOIN anagrafiche.soggetti sog ON sog.id = sr.soggetto_id
WHERE c.livello IS NOT NULL
ORDER BY
    CASE c.livello
        WHEN 'ASSEGNATO'  THEN 1
        WHEN 'COMPETENZA'  THEN 2
        WHEN 'REPARTO'     THEN 3
    END,
    pp.codice_interno DESC,
    COALESCE(c.flusso_scadenza, p.data_scadenza) NULLS LAST,
    c.sequenza;
$function$

COMMENT ON FUNCTION pratiche.fn_coda_lavoro_operatore(p_risorsa_umana_id bigint, p_emittente_fiscale_id bigint)
IS 'Coda di lavoro operatore su tre livelli: ASSEGNATO, COMPETENZA, REPARTO. Esclude i flussi di pratiche terminali (stato senza transizioni in uscita attive).';
```

---
{% include-markdown "signature-core.md" %}
