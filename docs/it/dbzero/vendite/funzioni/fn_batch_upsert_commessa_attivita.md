{% include-markdown "it/dbzero/vendite/manual/fn_batch_upsert_commessa_attivita.md" %}
# ⚙️ Funzione `fn_batch_upsert_commessa_attivita`

```sql
CREATE FUNCTION fn_batch_upsert_commessa_attivita(p_rows jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_batch_upsert_commessa_attivita(p_rows jsonb)
 RETURNS TABLE(total_rows integer, inserted integer, updated integer, errors jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_total    integer := 0;
  v_inserted integer := 0;
  v_updated  integer := 0;
  v_errors   jsonb   := '[]'::jsonb;
  v_len      integer;
  v_row      jsonb;
  v_result   record;
  i          integer;
  -- La diagnostica dell'errore di una riga (GET STACKED DIAGNOSTICS):
  --   valori dell'eccezione, nessuna colonna li rispecchia.
  v_sqlstate text;
  v_vincolo  text;
  v_colonna  text;
  v_codice   text;
BEGIN
  -- =========================================================
  -- Batch wrapper su fn_upsert_commessa_attivita.
  -- 1 round-trip Python->DB; errori raccolti collect-all.
  -- Payload atteso per ogni elemento: oggetto con le chiavi
  -- equivalenti ai parametri p_* del single-upsert. Le 8
  -- chiavi snapshot pricing v5 (sotto) sono parte della
  -- firma OBBLIGATORIA (il caller deve includerle, anche
  -- come NULL JSON, per garantire che la riga snapshot sia
  -- coerente).
  -- rev 2026-10-09 (brief-db-riga-listino-propagata-dalla-commessa,
  -- R-1): la chiave listino_riga_id arriva alla madre. FACOLTATIVA,
  -- come listino_versione_id: assente o null = nessuna riga di
  -- listino (prezzo manuale, onere, rettifica, stadio BUNDLE).
  -- =========================================================

  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RETURN QUERY SELECT 0, 0, 0, '[]'::jsonb;
    RETURN;
  END IF;

  v_len := jsonb_array_length(p_rows);
  IF v_len = 0 THEN
    RETURN QUERY SELECT 0, 0, 0, '[]'::jsonb;
    RETURN;
  END IF;

  FOR i IN 0 .. v_len - 1 LOOP
    v_row   := p_rows -> i;
    v_total := v_total + 1;

    BEGIN
      SELECT r.attivita_id, r.is_new
      INTO v_result
      FROM vendite.fn_upsert_commessa_attivita(
        p_commessa_id                   => (v_row ->> 'commessa_id')::bigint,
        p_segment_key                   => (v_row ->> 'segment_key')::varchar,
        p_articolo_id                   => (v_row ->> 'articolo_id')::uuid,
        p_istanza_utility_id            => (v_row ->> 'istanza_utility_id')::bigint,
        p_data_attivita                 => (v_row ->> 'data_attivita')::date,
        p_uom_id                        => (v_row ->> 'uom_id')::bigint,
        p_quantita                      => (v_row ->> 'quantita')::numeric,
        p_competenza_mese               => (v_row ->> 'competenza_mese')::date,
        p_competenza_dal                => (v_row ->> 'competenza_dal')::date,
        p_competenza_al                 => (v_row ->> 'competenza_al')::date,
        p_prezzo_snapshot               => (v_row ->> 'prezzo_snapshot')::numeric,
        -- Snapshot pricing v5 (chiavi obbligatorie nel payload;
        -- passare null esplicito quando la dimensione non si applica).
        p_prezzo_base_snapshot          => (v_row ->> 'prezzo_base_snapshot')::numeric,
        p_origine_prezzo                => (v_row ->> 'origine_prezzo')::varchar,
        p_tipo_variazione_applicata     => (v_row ->> 'tipo_variazione_applicata')::varchar,
        p_valore_variazione_applicata   => (v_row ->> 'valore_variazione_applicata')::numeric,
        p_promo_id                      => (v_row ->> 'promo_id')::bigint,
        p_contratto_id                  => (v_row ->> 'contratto_id')::bigint,
        p_categoria_cliente_id_snapshot => (v_row ->> 'categoria_cliente_id_snapshot')::smallint,
        p_classe_utenza_id_snapshot     => (v_row ->> 'classe_utenza_id_snapshot')::integer,
        -- Resto firma (opzionale lato single-upsert grazie ai DEFAULT).
        p_qta_operativa                 => (v_row ->> 'qta_operativa')::numeric,
        p_uom_operativa_id              => (v_row ->> 'uom_operativa_id')::bigint,
        p_factor_to_base                => (v_row ->> 'factor_to_base')::numeric,
        p_posticipa_al                  => (v_row ->> 'posticipa_al')::date,
        p_tipo_doc_fiscale_id           => (v_row ->> 'tipo_doc_fiscale_id')::bigint,
        p_valuta_id                     => (v_row ->> 'valuta_id')::integer,
        p_area_geografica_id            => (v_row ->> 'area_geografica_id')::bigint,
        p_listino_versione_id           => (v_row ->> 'listino_versione_id')::bigint,
        p_listino_riga_id               => (v_row ->> 'listino_riga_id')::bigint,
        p_prezzo_bloccato               => (v_row ->> 'prezzo_bloccato')::boolean,
        p_pricing_mode                  => (v_row ->> 'pricing_mode')::varchar,
        p_prezzo_da_riallineare         => (v_row ->> 'prezzo_da_riallineare')::boolean,
        p_stato_approvazione            => (v_row ->> 'stato_approvazione')::varchar,
        p_stato_emissione               => (v_row ->> 'stato_emissione')::varchar,
        p_sorgente_tipo_id              => (v_row ->> 'sorgente_tipo_id')::bigint,
        p_sorgente_chiave               => (v_row ->> 'sorgente_chiave')::text,
        -- La riga del documento (la riga_id del lister): NULL se il documento non ha
        --   righe o la provenienza e' il documento intero.
        p_sorgente_riga                 => (v_row ->> 'sorgente_riga')::bigint,
        p_tipo_movimento                => (v_row ->> 'tipo_movimento')::varchar,
        -- rev 2026-11-03 (20261103-49): la causale dell'onere (giro 1: gli
        --   oneri di ordine e bolla arrivano dal push come ONERE).
        p_causale_onere_id              => (v_row ->> 'causale_onere_id')::bigint,
        p_meta                          => CASE WHEN v_row ? 'meta' THEN (v_row -> 'meta') ELSE '{}'::jsonb END
      ) r;

      IF v_result.is_new THEN
        v_inserted := v_inserted + 1;
      ELSE
        v_updated := v_updated + 1;
      END IF;

    EXCEPTION WHEN others THEN
      -- ⭐ Il codice di dominio viaggia nel canale CONSTRAINT, il campo da
      --   correggere nel canale COLUMN (script.fn_log_and_raise_error): qui
      --   l'eccezione non arriva al backend, che non puo' leggerli dal driver.
      GET STACKED DIAGNOSTICS
        v_sqlstate = RETURNED_SQLSTATE,
        v_vincolo  = CONSTRAINT_NAME,
        v_colonna  = COLUMN_NAME;
      -- ⚠️ Per un 23505 o un 23514 il CONSTRAINT e' il nome di un vincolo:
      --   codice e campo ci sono solo per un errore di dominio.
      v_codice := script.fn_codice_dominio(v_sqlstate, v_vincolo);

      -- Le tre chiavi di prima restano identiche (una segment_key null resta
      --   una chiave null); le nuove non compaiono quando non hanno valore.
      v_errors := v_errors || jsonb_build_array(
        jsonb_build_object(
          'index',       i,
          'segment_key', v_row ->> 'segment_key',
          'error',       SQLERRM
        )
        || jsonb_strip_nulls(jsonb_build_object(
          'sqlstate',    v_sqlstate,
          'codice',      v_codice,
          'campo',       CASE WHEN v_codice IS NOT NULL THEN NULLIF(v_colonna, '') END
        ))
      );
    END;
  END LOOP;

  RETURN QUERY SELECT v_total, v_inserted, v_updated, v_errors;
END
$function$

COMMENT ON FUNCTION vendite.fn_batch_upsert_commessa_attivita(p_rows jsonb)
IS 'Il batch del push: un array jsonb di righe, ognuna passata a vendite.fn_upsert_commessa_attivita con le chiavi dei suoi parametri (senza il prefisso p_), e i contatori total_rows, inserted, updated con gli errori raccolti tutti (collect-all: una riga che fallisce non ferma le altre, qualunque errore sia). Ogni errore di errors porta index (la posizione della riga nell''array), segment_key, error (il messaggio) e sqlstate; quando l''errore e'' di dominio (script.fn_codice_dominio: P0001 col codice nel canale CONSTRAINT) porta anche codice, il codice del catalogo dei messaggi, e campo, il campo da correggere quando l''errore lo nomina. Per un errore che non e'' di dominio (un cast del payload, un vincolo) codice e campo non ci sono. Le chiavi dello snapshot di prezzo (prezzo_base_snapshot, origine_prezzo, tipo_variazione_applicata, valore_variazione_applicata, promo_id, contratto_id, categoria_cliente_id_snapshot, classe_utenza_id_snapshot) sono obbligatorie come nella madre. La provenienza: sorgente_tipo_id, sorgente_chiave (la chiave del documento come la ha il chiamante, id o uid) e sorgente_riga (la riga del documento, dalla riga_id dei lister del push).';
```

</div>

---
{% include-markdown "signature-core.md" %}
