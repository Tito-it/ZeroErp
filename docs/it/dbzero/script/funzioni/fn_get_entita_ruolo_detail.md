{% include-markdown "it/dbzero/script/manual/fn_get_entita_ruolo_detail.md" %}
# ⚙️ Funzione `fn_get_entita_ruolo_detail`

```sql
CREATE FUNCTION fn_get_entita_ruolo_detail(p_soggetto_ruolo_id bigint, p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_entita_ruolo_detail(p_soggetto_ruolo_id bigint, p_utility_id integer DEFAULT NULL::integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
  v_tipo_ruolo_codice  config.tipi_ruoli.codice_interno%TYPE;
  v_result             jsonb;
BEGIN
  -- Guard: parametro obbligatorio
  IF p_soggetto_ruolo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_get_entita_ruolo_detail',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object(
        'parametro', 'p_soggetto_ruolo_id',
        'valore', NULL
      ),
      NULL::uuid,
      'p_soggetto_ruolo_id obbligatorio'
    );
  END IF;

  -- Recupera codice_interno del tipo ruolo associato
  SELECT tr.codice_interno INTO v_tipo_ruolo_codice
  FROM anagrafiche.soggetti_ruoli sr
    JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
  WHERE sr.id = p_soggetto_ruolo_id;

  IF v_tipo_ruolo_codice IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_get_entita_ruolo_detail',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'soggetto_ruolo_id non trovato in anagrafiche.soggetti_ruoli',
        'p_soggetto_ruolo_id', p_soggetto_ruolo_id
      ),
      NULL::uuid,
      concat('soggetto_ruolo_id=', p_soggetto_ruolo_id, ' non trovato')
    );
  END IF;

  -- Dispatch per codice_interno (immutabile, protetto da trgfn_lock_columns)
  CASE v_tipo_ruolo_codice

  WHEN 'CL' THEN
    -- Cliente: N righe per soggetto_ruolo (una per istanza_utility).
    -- Codice da billing_account. Date ciclo vita e stato.
    -- p_utility_id filtra per utility specifica se fornito.
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail ORDER BY row_detail->>'billing_account_codice'), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',               cl.id,
        'billing_account_id',      cl.billing_account_id,
        'billing_account_codice',  ba.codice,
        'utility_id',              cl.utility_id,
        'stato_cliente_id',        cl.stato_cliente_id,
        'stato_codice',            sc.codice_interno,
        'stato_descrizione',       sc.descrizione_breve,
        'data_attivazione',        cl.data_attivazione,
        'data_sospensione',        cl.data_sospensione,
        'data_riattivazione',      cl.data_riattivazione,
        'data_chiusura',           cl.data_chiusura
      ) AS row_detail
      FROM anagrafiche.clienti cl
        JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
        LEFT JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
      WHERE cl.soggetto_ruolo_id = p_soggetto_ruolo_id
        AND (p_utility_id IS NULL OR cl.utility_id = p_utility_id)
    ) sub;

  WHEN 'FO' THEN
    -- Fornitore: 1 riga per soggetto_ruolo (UQ).
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',    f.id,
        'codice',       f.codice,
        'attivo',       f.attivo
      ) AS row_detail
      FROM anagrafiche.fornitori f
      WHERE f.soggetto_ruolo_id = p_soggetto_ruolo_id
    ) sub;

  WHEN 'EF' THEN
    -- Emittente fiscale: 1 riga per soggetto_ruolo (UQ).
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',    ef.id,
        'codice',       ef.codice,
        'descrizione',  ef.descrizione,
        'attivo',       ef.attivo
      ) AS row_detail
      FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.soggetto_ruolo_id = p_soggetto_ruolo_id
    ) sub;

  WHEN 'VT' THEN
    -- Vettore: 1 riga per soggetto_ruolo (UQ).
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',    v.id,
        'codice',       v.codice,
        'descrizione',  v.descrizione,
        'attivo',       v.attivo
      ) AS row_detail
      FROM anagrafiche.vettori v
      WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
    ) sub;

  WHEN 'GE' THEN
    -- Gestore: 1 riga (singleton).
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',    g.id,
        'descrizione',  g.descrizione
      ) AS row_detail
      FROM anagrafiche.gestori g
      WHERE g.soggetto_ruolo_id = p_soggetto_ruolo_id
    ) sub;

  WHEN 'BANK_B' THEN
    -- Istituto di credito: N filiali per soggetto_ruolo.
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail ORDER BY row_detail->>'bank_code', row_detail->>'branch_code'), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',    bb.id,
        'bank_code',    bb.bank_code,
        'branch_code',  bb.branch_code,
        'bic_swift',    bb.bic_swift,
        'name',         bb.name,
        'attivo',       bb.attivo
      ) AS row_detail
      FROM anagrafiche.bank_branches bb
      WHERE bb.soggetto_ruolo_id = p_soggetto_ruolo_id
    ) sub;

  WHEN 'RIS_UMANA' THEN
    -- Risorsa umana: 1 riga per soggetto_ruolo (UQ).
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'entita_id',    ru.id,
        'attivo',       ru.attivo,
        'valido_dal',   ru.valido_dal,
        'valido_al',    ru.valido_al
      ) AS row_detail
      FROM anagrafiche.risorse_umane ru
      WHERE ru.soggetto_ruolo_id = p_soggetto_ruolo_id
    ) sub;

  ELSE
    -- Ruoli senza tabella dedicata (VE, DI, RE, PSP):
    -- restituisce meta da soggetti_ruoli
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', jsonb_build_array(
        jsonb_build_object(
          'soggetto_ruolo_id', sr.id,
          'meta', COALESCE(sr.meta, '{}'::jsonb)
        )
      )
    ) INTO v_result
    FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.id = p_soggetto_ruolo_id;

  END CASE;

  RETURN COALESCE(v_result, jsonb_build_object('tipo_ruolo', v_tipo_ruolo_codice, 'righe', '[]'::jsonb));
END;
$function$

COMMENT ON FUNCTION script.fn_get_entita_ruolo_detail(p_soggetto_ruolo_id bigint, p_utility_id integer)
IS 'Dati entità specifici per tipo ruolo in JSONB. CL: billing_account+date+stato (filtro opzionale utility_id). FO: codice+attivo. EF: codice+descrizione+attivo. VT: codice+descrizione+attivo. GE: descrizione. BANK_B: bank_code+branch_code+bic_swift. RIS_UMANA: attivo+validità. ELSE: meta da soggetti_ruoli.';
```

---
{% include-markdown "signature-core.md" %}
