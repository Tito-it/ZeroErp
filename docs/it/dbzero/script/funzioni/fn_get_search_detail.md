{% include-markdown "it/dbzero/script/manual/fn_get_search_detail.md" %}
# ⚙️ Funzione `fn_get_search_detail`

```sql
CREATE FUNCTION fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer, p_emittente_ids bigint[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer DEFAULT NULL::integer, p_emittente_ids bigint[] DEFAULT NULL::bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_tipo_ruolo_codice  config.tipi_ruoli.codice_interno%TYPE;
  -- Il dettaglio composto: nessuna colonna di cui sia il riflesso.
  v_result             jsonb;
BEGIN
  IF p_soggetto_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'script.fn_get_search_detail', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
      NULL::uuid, 'p_soggetto_id obbligatorio'
    );
  END IF;

  IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'script.fn_get_search_detail', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_tipo_ruolo_id', 'valore', p_tipo_ruolo_id),
      NULL::uuid, 'p_tipo_ruolo_id obbligatorio e > 0'
    );
  END IF;

  SELECT tr.codice_interno INTO v_tipo_ruolo_codice
  FROM config.tipi_ruoli tr
  WHERE tr.id = p_tipo_ruolo_id;

  IF v_tipo_ruolo_codice IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'script.fn_get_search_detail', 'E_TIPO_RUOLO_NON_TROVATO',
      jsonb_build_object('detail', 'tipo_ruolo_id non trovato in config.tipi_ruoli', 'p_tipo_ruolo_id', p_tipo_ruolo_id),
      NULL::uuid, p_tipo_ruolo_id::text
    );
  END IF;

  -- =========================================================
  -- «Non c'e'» (rev 2026-10-08, R-4).
  --
  -- Il soggetto, con quel ruolo, risulta a chi guarda? Stesso
  -- perimetro delle righe ma SENZA il filtro utility, con la
  -- stessa check della lista (fn_search_soggetti_universale):
  --   * il soggetto-ruolo esiste;
  --   * per CL, almeno un suo cliente e' restituito dalla RLS.
  -- Altrimenti NULL: il backend risponde 404 E_SEARCH_NOT_FOUND.
  -- ⚠️ Inesistente e fuori perimetro escono uguali, di
  --   proposito: il 404 non rivela un cliente di un altro
  --   emittente.
  -- ⚠️ Il filtro utility resta FUORI: «c'e', ma l'utility non
  --   ne trova» e' un risultato vero, righe = [].
  -- =========================================================
  IF NOT EXISTS (
    SELECT 1
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.soggetto_id = p_soggetto_id
       AND sr.tipo_ruolo_id = p_tipo_ruolo_id
       AND script.fn_check_soggetto_ruolo_visibile(sr.id)
  ) THEN
    RETURN NULL;
  END IF;

  -- Dettaglio per codice_interno del tipo ruolo (immutabile).
  CASE v_tipo_ruolo_codice

  WHEN 'CL' THEN
    -- ⚠️ Il perimetro dei clienti lo applica la RLS di
    --   anagrafiche.clienti (rev 2026-10-08): fino a quel giorno
    --   qui c'era un filtro a mano che ne era una seconda copia.
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail ORDER BY row_detail->>'utility_codice_interno', row_detail->>'stato_descrizione'), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'cliente_id',             cl.id,
        'soggetto_ruolo_id',      cl.soggetto_ruolo_id,
        'codice',                 ba.codice,
        'istanza_codice',         iu.codice,
        'istanza_id',             iu.id,
        'utility_id',             u.id,
        'utility_codice_interno', u.codice_interno,
        'utility_codice',         u.codice,
        'utility_descrizione',    u.descrizione,
        'stato_cliente_id',       sc.id,
        'stato_codice_interno',   sc.codice_interno,
        'stato_descrizione',      sc.descrizione_breve,
        'stato_macro',            sc.codice,
        'indirizzo',              COALESCE(idv.indirizzo_normalizzato, fb_ind.indirizzo_completo, ''),
        'comune',                 COALESCE(idv.descrizione_comune, fb_ind.comune_descrizione, ''),
        'data_attivazione',       cl.data_attivazione,
        'data_sospensione',       cl.data_sospensione,
        'data_riattivazione',     cl.data_riattivazione,
        'data_chiusura',          cl.data_chiusura
      ) AS row_detail
      FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.clienti cl ON cl.soggetto_ruolo_id = sr.id
        JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
        LEFT JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
        LEFT JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
        LEFT JOIN config.utilities u ON u.id = cl.utility_id
        LEFT JOIN anagrafiche.vw_indirizzi_dettaglio idv ON idv.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
        LEFT JOIN LATERAL (
          SELECT gi.indirizzo_completo, gi.comune_descrizione
          FROM script.fn_get_indirizzo(sr.id, 'RES') gi
          LIMIT 1
        ) fb_ind ON iu.indirizzo_dettaglio_id IS NULL
      WHERE sr.soggetto_id = p_soggetto_id
        AND sr.tipo_ruolo_id = p_tipo_ruolo_id
        AND (p_utility_id IS NULL OR cl.utility_id = p_utility_id)
    ) sub;

  WHEN 'FO' THEN
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'fornitore_id',        f.id,
        'soggetto_ruolo_id',   f.soggetto_ruolo_id,
        'codice',              f.codice,
        'attivo',              f.attivo,
        'stato_descrizione',   CASE WHEN f.attivo THEN 'ATTIVO' ELSE 'INATTIVO' END,
        'indirizzo',           COALESCE(fb_ind.indirizzo_completo, ''),
        'comune',              COALESCE(fb_ind.comune_descrizione, '')
      ) AS row_detail
      FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.fornitori f ON f.soggetto_ruolo_id = sr.id
        LEFT JOIN LATERAL (
          SELECT gi.indirizzo_completo, gi.comune_descrizione
          FROM script.fn_get_indirizzo(sr.id, 'SEDEOP') gi
          LIMIT 1
        ) fb_ind ON true
      WHERE sr.soggetto_id = p_soggetto_id
        AND sr.tipo_ruolo_id = p_tipo_ruolo_id
    ) sub;

  ELSE
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'entita_detail', script.fn_get_entita_ruolo_detail(sr.id, p_utility_id),
      'righe', jsonb_build_array(
        jsonb_build_object(
          'soggetto_ruolo_id', sr.id,
          'soggetto_id',       sr.soggetto_id,
          'indirizzo',         COALESCE(fb_ind.indirizzo_completo, ''),
          'comune',            COALESCE(fb_ind.comune_descrizione, '')
        )
      )
    ) INTO v_result
    FROM anagrafiche.soggetti_ruoli sr
      LEFT JOIN LATERAL (
        SELECT gi.indirizzo_completo, gi.comune_descrizione
        FROM script.fn_get_indirizzo(sr.id, 'RES') gi
        LIMIT 1
      ) fb_ind ON true
    WHERE sr.soggetto_id = p_soggetto_id
      AND sr.tipo_ruolo_id = p_tipo_ruolo_id;

  END CASE;

  -- Arrivati qui il soggetto-ruolo c'e' (verifica sopra): niente
  -- COALESCE, v_result e' sempre valorizzato.
  RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer, p_emittente_ids bigint[])
IS 'Dettaglio della ricerca universale per tipo_ruolo (CASE su codice_interno). ⭐ NULL = «non c''e''» (rev 2026-10-08, brief-db-codici-non-trovato-email-e-permessi R-4, decisione di Tid): il soggetto non esiste, non ha quel ruolo, o per CL nessuno dei suoi clienti e'' visibile a chi guarda — la verifica e'' script.fn_check_soggetto_ruolo_visibile, la stessa della lista, sullo stesso perimetro delle righe ma senza il filtro utility. Il backend risponde 404 E_SEARCH_NOT_FOUND. Inesistente e fuori perimetro escono uguali, di proposito. NULL e non un raise: una lettura non scrive nel diario errori a ogni id sbagliato. La struttura {tipo_ruolo, righe} (righe anche vuota) solo quando il soggetto c''e'': righe = [] vuol dire che il filtro p_utility_id non ne trova. Perimetro: per CL lo fa la RLS di anagrafiche.clienti (dal 2026-10-08; prima un filtro a mano che ne era una seconda copia); FO e altri ruoli non portano un emittente nel modello, quindi non si filtrano per emittente (scelta di modello). ⚠️ p_emittente_ids SUPERATO dal 2026-10-08: resta in firma e non e'' letto, il ritiro lo decide Tid col backend. Ramo CL: utility_codice_interno (logica) + utility_codice (display), stato_codice_interno; stato_macro = stati_cliente.codice. SECURITY INVOKER: la RLS vale con l''identita'' di chi chiama.';
```

---
{% include-markdown "signature-core.md" %}
