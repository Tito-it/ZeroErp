{% include-markdown "it/dbzero/pratiche/manual/fn_lista_pratiche_per_contesto.md" %}
# ⚙️ Funzione `fn_lista_pratiche_per_contesto`

```sql
CREATE FUNCTION fn_lista_pratiche_per_contesto(p_emittente_fiscale_id bigint, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_solo_interne boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_lista_pratiche_per_contesto(p_emittente_fiscale_id bigint, p_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_solo_interne boolean DEFAULT false)
 RETURNS TABLE(pratica_id bigint, codice text, descrizione text, contesto text, tipo_prestazione_codice character varying, stato_codice character varying, priorita_codice character varying, soggetto_id uuid, soggetto_ragione_sociale text, soggetto_ruolo_id bigint, istanza_utility_id bigint, risorsa_umana_id bigint, unita_organizzativa_id integer, data_apertura date, data_scadenza date)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Lista pratiche per contesto anagrafico — lente canonica
  --   D1. Tre lenti mutuamente alternative (ruolo / istanza /
  --   interne); nessuna lente = tutte le pratiche
  --   dell'emittente. Bucket "contesto" calcolato per il
  --   raggruppamento FE: RUOLO / ISTANZA / SOGGETTO / INTERNA.
  -- =========================================================

  -- Guard: emittente obbligatorio (segregazione multi-company).
  IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.fn_lista_pratiche_per_contesto',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_emittente_fiscale_id',
                         'valore', p_emittente_fiscale_id),
      NULL::uuid,
      'p_emittente_fiscale_id obbligatorio e > 0'
    );
  END IF;

  -- Guard: lenti mutuamente alternative (al massimo una).
  IF (p_soggetto_ruolo_id IS NOT NULL)::int
     + (p_istanza_utility_id IS NOT NULL)::int
     + p_solo_interne::int > 1 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.fn_lista_pratiche_per_contesto',
      'E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI',
      jsonb_build_object(
        'soggetto_ruolo_id', p_soggetto_ruolo_id,
        'istanza_utility_id', p_istanza_utility_id,
        'solo_interne', p_solo_interne
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN QUERY
  SELECT
    p.id,
    p.codice,
    p.descrizione,
    -- Bucket canonico del contesto (D1): un solo valore per pratica.
    CASE
      WHEN p.soggetto_ruolo_id IS NOT NULL THEN 'RUOLO'
      WHEN p.istanza_utility_id IS NOT NULL THEN 'ISTANZA'
      WHEN p.soggetto_id IS NOT NULL THEN 'SOGGETTO'
      ELSE 'INTERNA'
    END,
    tp.codice,
    sp.codice_interno,
    pp.codice_interno,
    p.soggetto_id,
    sog.ragione_sociale_completa,
    p.soggetto_ruolo_id,
    p.istanza_utility_id,
    p.risorsa_umana_id,
    p.unita_organizzativa_id,
    p.data_apertura,
    p.data_scadenza
  FROM pratiche.pratiche p
  JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
  JOIN config.stati_pratiche sp     ON sp.id = p.stato_id
  JOIN config.priorita_pratiche pp  ON pp.id = p.priorita_id
  LEFT JOIN anagrafiche.soggetti sog ON sog.id = p.soggetto_id
  WHERE p.emittente_fiscale_id = p_emittente_fiscale_id
    -- Lente ruolo: pratiche del ruolo soggetto indicato.
    AND (p_soggetto_ruolo_id IS NULL
         OR p.soggetto_ruolo_id = p_soggetto_ruolo_id)
    -- Lente istanza: pratiche dell'istanza utility indicata.
    AND (p_istanza_utility_id IS NULL
         OR p.istanza_utility_id = p_istanza_utility_id)
    -- Lente interne: nessun contesto cliente (soggetto NULL;
    -- il guard contesto garantisce ruolo/istanza NULL a cascata).
    AND (NOT p_solo_interne OR p.soggetto_id IS NULL)
  ORDER BY
    pp.sequenza DESC,
    p.data_scadenza NULLS LAST,
    p.id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_lista_pratiche_per_contesto(p_emittente_fiscale_id bigint, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_solo_interne boolean)
IS 'Lente canonica D1: lista pratiche per contesto (ruolo soggetto / istanza utility / interne / tutte), lenti mutuamente alternative. Bucket contesto calcolato: RUOLO/ISTANZA/SOGGETTO/INTERNA. Ogni vista "pratiche di X" passa da qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
