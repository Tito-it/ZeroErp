{% include-markdown "it/dbzero/vendite/manual/fn_get_registro_id.md" %}
# ⚙️ Funzione `fn_get_registro_id`

```sql
CREATE FUNCTION fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(registro_id bigint, serie character varying)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dato un tipo documento E UNA NATURA, il registro di
--   numerazione e la serie su cui il documento va scritto.
-- rev 2026-08-18 (brief-design-note-credito-resi N2): la natura
--   entra nella chiave del mapping e la serie esce insieme al
--   registro. Prima rispondeva al solo «su quale registro va
--   questo tipo di documento?», che smette di bastare nel
--   momento in cui due nature devono numerare separate.
DECLARE
    v_natura_doc_id config.nature_doc_fiscale.id%TYPE;
    v_registro_id   vendite.registri_fatturazione.id%TYPE;
    v_serie         vendite.tipi_doc_fiscale_registri.serie%TYPE;
BEGIN
    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_registro_id', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id),
            NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0');
    END IF;

    -- Default risolto per chiave naturale, mai un id cablato:
    -- l'id e' dettaglio implementativo, il codice_interno e' il
    -- contratto (linee-guida-sql §6b).
    v_natura_doc_id := COALESCE(
        p_natura_doc_id,
        config.fn_get_natura_doc_fiscale_id('FATTURA'));

    IF v_natura_doc_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_registro_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('parametro', 'p_natura_doc_id', 'valore', p_natura_doc_id),
            NULL::uuid, 'natura documento non risolta (config.nature_doc_fiscale)');
    END IF;

    -- Risoluzione con fallback: tipo_doc+utility+emittente → tipo_doc+utility → tipo_doc+emittente → tipo_doc
    -- ⚠️ Il fallback e' la gerarchia di specificita' del REGISTRO
    --    (utility/emittente) e resta identica. La NATURA invece e'
    --    un filtro esatto: non esiste un «registro della natura
    --    piu' vicina», e ripiegare sulla fattura emetterebbe una
    --    nota di credito nel registro sbagliato, in silenzio.
    SELECT r.id, m.serie
      INTO v_registro_id, v_serie
      FROM vendite.tipi_doc_fiscale_registri m
      JOIN vendite.registri_fatturazione r ON r.id = m.registro_id
     WHERE m.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
       AND m.natura_doc_id = v_natura_doc_id
       AND (r.utility_id IS NULL OR r.utility_id = p_utility_id)
       AND (r.emittente_soggetto_ruolo_id IS NULL OR r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
     ORDER BY
         CASE
             WHEN r.utility_id = p_utility_id AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id THEN 1
             WHEN r.utility_id = p_utility_id AND r.emittente_soggetto_ruolo_id IS NULL THEN 2
             WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id THEN 3
             WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id IS NULL THEN 4
             ELSE 9
         END, r.id
     LIMIT 1;

    IF v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_registro_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('tipo_doc_fiscale_id', p_tipo_doc_fiscale_id,
                               'natura_doc_id', v_natura_doc_id,
                               'utility_id', p_utility_id,
                               'emittente', p_emittente_soggetto_ruolo_id),
            NULL::uuid, concat('registro non risolto per tipo_doc ', p_tipo_doc_fiscale_id,
                               ' e natura ', v_natura_doc_id));
    END IF;

    -- ⚠️ `serie` esce GREZZA (l'override del mapping), non
    --    COALESCE-ata sul serie_default del registro: scrivere il
    --    default dentro vendite.fatture.serie cambierebbe il
    --    valore di una colonna su documenti gia' emessi, dove
    --    oggi c'e' NULL. NULL qui continua a voler dire «vale il
    --    default del registro», che fn_assign_numero_fattura
    --    risolve gia' da se'.
    RETURN QUERY SELECT v_registro_id, v_serie;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'Dato un tipo documento fiscale E UNA NATURA (piu'', opzionalmente, utility ed emittente), il registro di numerazione e la SERIE su cui il documento va scritto. rev 2026-08-18 (brief-design-note-credito-resi N2): prima rispondeva al solo «su quale registro va questo tipo di documento?» e restituiva un bigint — cambiare tipo di ritorno ha richiesto DROP + CREATE. ⚠️ Il fallback a quattro livelli (utility+emittente, utility, emittente, nessuno) e'' la gerarchia di specificita'' del REGISTRO e resta invariato; la NATURA invece e'' un filtro ESATTO: se il mapping per quella natura non esiste la risposta e'' E_CONFIG_MANCANTE, perche'' ripiegare sulla fattura emetterebbe una nota di credito nel registro delle fatture senza dirlo. ⚠️ La serie esce grezza (l''override del mapping): NULL significa «vale il serie_default del registro», e fn_assign_numero_fattura lo risolve gia''. COALESCE-arla qui scriverebbe il default dentro fatture.serie, cambiando una colonna su documenti gia'' emessi.';
```

---
{% include-markdown "signature-core.md" %}
