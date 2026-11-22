{% include-markdown "it/dbzero/anagrafiche/manual/fn_soggetto_primo_documento.md" %}
# ⚙️ Funzione `fn_soggetto_primo_documento`

```sql
CREATE FUNCTION fn_soggetto_primo_documento(p_soggetto_id uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_soggetto_primo_documento(p_soggetto_id uuid)
 RETURNS character varying
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    -- gli id del soggetto in ciascuna tabella ponte
    v_ruoli    bigint[];  -- anagrafiche.soggetti_ruoli.id
    v_ba       bigint[];  -- anagrafiche.billing_account.id
    v_ef       bigint[];  -- anagrafiche.emittenti_fiscali.id
    v_ru       bigint[];  -- anagrafiche.risorse_umane.id
    v_ids      bigint[];
    v_doc      record;
    v_trovato  boolean;   -- l'esito di un EXISTS: nessuna colonna dietro
BEGIN
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_soggetto_primo_documento', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
            NULL::uuid,
            'il soggetto e'' obbligatorio');
    END IF;

    v_ruoli := ARRAY(SELECT r.id FROM anagrafiche.soggetti_ruoli r
                      WHERE r.soggetto_id = p_soggetto_id);
    v_ba    := ARRAY(SELECT b.id FROM anagrafiche.billing_account b
                      WHERE b.soggetto_ruolo_id = ANY (v_ruoli));
    v_ef    := ARRAY(SELECT e.id FROM anagrafiche.emittenti_fiscali e
                      WHERE e.soggetto_ruolo_id = ANY (v_ruoli));
    v_ru    := ARRAY(SELECT h.id FROM anagrafiche.risorse_umane h
                      WHERE h.soggetto_id = p_soggetto_id
                         OR h.soggetto_ruolo_id = ANY (v_ruoli));

    -- ⭐ Le colonne dal catalogo: FK a una colonna, sulla PK del ponte.
    FOR v_doc IN
        SELECT s.codice_interno, t.schema_tabella, t.nome_tabella,
               a.attname AS colonna, c.confrelid AS ponte
          FROM config.sorgenti s
          CROSS JOIN LATERAL config.fn_sorgente_tabella(s.codice_interno) t
          JOIN pg_catalog.pg_constraint c
            ON c.conrelid = t.relid
           AND c.contype = 'f'
           AND cardinality(c.conkey) = 1
          JOIN pg_catalog.pg_attribute a
            ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
          JOIN pg_catalog.pg_attribute pk
            ON pk.attrelid = c.confrelid AND pk.attnum = c.confkey[1]
           AND pk.attname = 'id'
         WHERE s.categoria = 'DOCUMENTO'
           AND c.confrelid IN ('anagrafiche.soggetti'::regclass,
                               'anagrafiche.soggetti_ruoli'::regclass,
                               'anagrafiche.billing_account'::regclass,
                               'anagrafiche.emittenti_fiscali'::regclass,
                               'anagrafiche.risorse_umane'::regclass)
         ORDER BY s.id, a.attnum
    LOOP
        IF v_doc.ponte = 'anagrafiche.soggetti'::regclass THEN
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.%I d WHERE d.%I = $1)',
                           v_doc.schema_tabella, v_doc.nome_tabella, v_doc.colonna)
               INTO v_trovato
              USING p_soggetto_id;
        ELSE
            v_ids := CASE v_doc.ponte
                         WHEN 'anagrafiche.soggetti_ruoli'::regclass    THEN v_ruoli
                         WHEN 'anagrafiche.billing_account'::regclass   THEN v_ba
                         WHEN 'anagrafiche.emittenti_fiscali'::regclass THEN v_ef
                         WHEN 'anagrafiche.risorse_umane'::regclass     THEN v_ru
                     END;
            CONTINUE WHEN cardinality(v_ids) = 0;
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.%I d WHERE d.%I = ANY ($1))',
                           v_doc.schema_tabella, v_doc.nome_tabella, v_doc.colonna)
               INTO v_trovato
              USING v_ids;
        END IF;

        IF v_trovato THEN
            RETURN v_doc.codice_interno;
        END IF;
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_soggetto_primo_documento(p_soggetto_id uuid)
IS 'Il codice (config.sorgenti.codice_interno) del primo tipo di documento in cui il soggetto compare, in qualunque ruolo, o NULL se non compare in nessuno. I documenti sono le testate di config.sorgenti con categoria DOCUMENTO (anche spente), con la tabella di config.fn_sorgente_tabella; le colonne sono le FK a una colonna della testata verso la PK di una delle tabelle che arrivano al soggetto: anagrafiche.soggetti, soggetti_ruoli, billing_account, emittenti_fiscali, risorse_umane. Ordine stabile: id della sorgente, poi posizione della colonna. SECURITY DEFINER, sopra la RLS dei documenti: riceve solo il soggetto e risponde solo il codice di un tipo, mai un id. Soggetto NULL: E_PARAMETRO_INVALIDO. La legge anagrafiche.fn_check_cambio_natura_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
