{% include-markdown "it/dbzero/pratiche/manual/fn_fork_definizione.md" %}
# ⚙️ Funzione `fn_fork_definizione`

```sql
CREATE FUNCTION fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pratiche', 'script', 'config', 'dbops', 'pg_temp'
AS $function$
-- Scopo: creare l'edizione di un emittente da una definizione (di
--        solito il preset), in BOZZA, con provenance per il drift.
--        SECURITY DEFINER: la DML interna (via fn_copia) gira come owner.
DECLARE
  -- Il BERSAGLIO: le bozze che bloccano il fork. ⚠️ `jsonb` esplicito, e' un
  -- frammento del context.
  v_bersagli jsonb;
  v_tipo_id pratiche.workflow_definizioni.tipo_prestazione_id%TYPE;
BEGIN
  IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_fork_definizione', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','p_emittente_fiscale_id',
                         'valore',p_emittente_fiscale_id),
      NULL::uuid,
      'il fork richiede un emittente valido; per una nuova versione dello stesso scope usare fn_nuova_versione_definizione');
  END IF;

  -- Scope destinazione = tipo della sorgente + emittente. Se la
  -- sorgente non esiste, il guard bozza si salta e fn_copia solleva
  -- E_VALORE_MANCANTE.
  SELECT wd.tipo_prestazione_id INTO v_tipo_id
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;

  -- ⭐ IL CASO PIU' NETTO DEL ROLL-OUT, e vale la pena dirlo qui.
  --    La frase che legge l'operatore e' «esiste gia' una bozza di edizione
  --    workflow per lo scope (tipo prestazione X, emittente Y)»: nomina lo
  --    SCOPE, e la bozza che lo blocca **non la nomina affatto**. Non e' un
  --    difetto del messaggio — quel documento un nome utile non ce l'ha — ed e'
  --    esattamente il buco che il bersaglio riempie: qui non aggiunge comodita',
  --    aggiunge un'informazione che la frase, per come e' costruita, non puo'
  --    dare.
  --
  -- ⚠️ L'EXISTS diventa una raccolta, come nei guard dell'offerta: stessa
  --    scansione, in piu' gli id. ARRAY perche' se le bozze fossero piu' d'una
  --    — l'anomalia che questo guard esiste per fermare — l'operatore deve
  --    poterle vedere tutte.
  IF v_tipo_id IS NOT NULL THEN
    SELECT jsonb_agg(jsonb_build_object('tipo', 'DEFINIZIONE_WORKFLOW',
                                        'id',   wd.id::text) ORDER BY wd.id)
      INTO v_bersagli
      FROM pratiche.workflow_definizioni wd
     WHERE wd.tipo_prestazione_id  = v_tipo_id
       AND wd.emittente_fiscale_id IS NOT DISTINCT FROM p_emittente_fiscale_id
       AND wd.stato = 'BOZZA';
  END IF;

  IF v_bersagli IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_fork_definizione', 'E_DEFINIZIONE_BOZZA_ESISTENTE',
      jsonb_build_object('tipo_prestazione_id', v_tipo_id,
                         'emittente_fiscale_id', p_emittente_fiscale_id,
                         'bersaglio', v_bersagli),
      NULL::uuid,
      v_tipo_id::text,
      p_emittente_fiscale_id::text);
  END IF;

  RETURN pratiche.fn_copia_definizione(p_definizione_id, p_emittente_fiscale_id, true);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
IS 'Crea l''edizione di un emittente da una definizione (di solito il preset), in BOZZA, con provenance per il drift. Wrapper di fn_copia_definizione(..., true). Guard: emittente NOT NULL; scope destinazione senza BOZZA aperta (DEFINIZIONE_BOZZA_ESISTENTE 515, invariante ≤1 BOZZA per scope). SECURITY DEFINER (search_path fisso): DML interna senza grant diretto; autorizzazione al gate app-layer (AdminAPIView). ⭐ rev 2026-08-24: E_DEFINIZIONE_BOZZA_ESISTENTE porta il BERSAGLIO sulle bozze che bloccano il fork — ed e'' il caso piu'' netto del roll-out del bersaglio. La frase nomina lo SCOPE (tipo prestazione, emittente) e la bozza che blocca non la nomina affatto: quel documento un nome utile non ce l''ha. Qui il bersaglio non aggiunge comodita'', aggiunge un''informazione che la frase per come e'' costruita non puo'' dare. L''EXISTS e'' diventato una raccolta (stessa scansione, in piu'' gli id) ed e'' un array perche'' se le bozze fossero piu'' d''una l''operatore deve vederle tutte. Brief: brief-db-bersaglio-errore.md §6 L6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
