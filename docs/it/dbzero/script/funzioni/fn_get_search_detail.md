{% include-markdown "it/dbzero/script/manual/fn_get_search_detail.md" %}
# ⚙️ Funzione `fn_get_search_detail`

```sql
CREATE FUNCTION fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer DEFAULT NULL::integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_tipo_ruolo_codice  config.tipi_ruoli.codice_interno%TYPE;
  -- Predicato SQL della regola unica: nessuna colonna di cui sia il riflesso.
  v_predicato          text;
  -- Esito della verifica d'esistenza: nessuna colonna.
  v_visibile           boolean;
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

  -- =========================================================
  -- Il tipo ruolo e «chi si vede» (rev 2026-10-10, R-6, Q-2).
  --
  -- Il BB valida il tipo ruolo (NULL o <= 0, inesistente, non
  -- ricercabile) e rende il predicato della regola unica, lo
  -- stesso che filtra la lista. Qui non si ripete nessuna delle
  -- due cose.
  -- =========================================================
  v_predicato := script.fn_predicato_soggetto_ruolo_visibile(p_tipo_ruolo_id, 'sr');

  SELECT tr.codice_interno INTO v_tipo_ruolo_codice
  FROM config.tipi_ruoli tr
  WHERE tr.id = p_tipo_ruolo_id;

  -- =========================================================
  -- «Non c'e'» (R-4, regola unica dal 2026-10-10).
  --
  -- Il soggetto, con quel ruolo, risulta a chi guarda? Stesso
  -- predicato della lista, SENZA il filtro utility. Altrimenti
  -- NULL: il backend risponde 404 E_SEARCH_NOT_FOUND.
  -- ⚠️ Inesistente e fuori perimetro escono uguali, di
  --   proposito: il 404 non rivela un cliente di un altro
  --   emittente.
  -- ⚠️ Il filtro utility resta FUORI: «c'e', ma l'utility non
  --   ne trova» e' un risultato vero, righe = [].
  -- =========================================================
  EXECUTE format(
    'SELECT EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                     WHERE sr.soggetto_id = $1
                       AND sr.tipo_ruolo_id = $2
                       AND %s)',
    v_predicato)
  INTO v_visibile
  USING p_soggetto_id, p_tipo_ruolo_id;

  IF NOT v_visibile THEN
    RETURN NULL;
  END IF;

  -- Dettaglio per codice_interno del tipo ruolo (immutabile): la
  -- forma delle righe di ciascun ruolo, non la regola di chi si vede.
  CASE v_tipo_ruolo_codice

  WHEN 'CL' THEN
    -- ⚠️ Il perimetro dei clienti lo applica la RLS di
    --   anagrafiche.clienti, la stessa tabella che il catalogo da'
    --   come entita_esistenza di CL.
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
    -- anagrafiche.fornitori: la stessa tabella che il catalogo da'
    -- come entita_esistenza di FO.
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

COMMENT ON FUNCTION script.fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer)
IS 'Dettaglio della ricerca universale per tipo_ruolo (CASE su codice_interno: la forma delle righe di ciascun ruolo). ⭐ NULL = «non c''e''» (R-4): il soggetto non esiste, non ha quel ruolo, o non risulta a chi guarda secondo la regola unica script.fn_predicato_soggetto_ruolo_visibile (rev 2026-10-10, R-6) — la stessa della lista, senza il filtro utility: almeno una riga visibile della entita_esistenza del ruolo (CL clienti, sotto la RLS; FO fornitori; VT vettori; BANK_B bank_branches), o il solo soggetto-ruolo per i ruoli che non ne hanno. Lo stato dell''entita'' non conta: cliente chiuso e fornitore disattivato si aprono. Il backend risponde 404 E_SEARCH_NOT_FOUND; inesistente e fuori perimetro escono uguali, di proposito. NULL e non un raise: una lettura non scrive nel diario errori a ogni id sbagliato. La struttura {tipo_ruolo, righe} (righe anche vuota) solo quando il soggetto c''e'': righe = [] vuol dire che il filtro p_utility_id non ne trova. Tipo ruolo validato dal BB: NULL o <= 0 E_PARAMETRO_INVALIDO, inesistente E_TIPO_RUOLO_NON_TROVATO, non ricercabile (ricerca_visibile = false) E_TIPO_RUOLO_NON_RICERCABILE (Q-2). p_emittente_ids ritirato il 2026-10-10 (R-5): superato dal 2026-10-08, il perimetro lo fa la RLS. Ramo CL: utility_codice_interno (logica) + utility_codice (display), stato_codice_interno; stato_macro = stati_cliente.codice. SECURITY INVOKER: la RLS vale con l''identita'' di chi chiama.';
```

</div>

---
{% include-markdown "signature-core.md" %}
