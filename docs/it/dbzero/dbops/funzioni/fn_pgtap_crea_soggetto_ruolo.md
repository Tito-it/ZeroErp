{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_soggetto_ruolo.md" %}
# ⚙️ Funzione `fn_pgtap_crea_soggetto_ruolo`

```sql
CREATE FUNCTION fn_pgtap_crea_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying, p_stato_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying, p_stato_id integer DEFAULT 1)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: assegnare a un soggetto un ruolo GIA' completo dei suoi
--   indirizzi obbligatori, che sono un layer SEPARATO da quelli
--   del soggetto.
-- Uso:
--   SELECT dbops.fn_pgtap_crea_soggetto_ruolo(<soggetto_id>, 'GE');
DECLARE
    v_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- Vedi la nota sulla finestra differita in
    -- fn_pgtap_crea_soggetto_pg: qui vale per il layer RUOLO, che
    -- ha una matrice SUA (config.tipi_ruolo_tipi_indirizzo) e un
    -- guard suo. ⚠️ Un indirizzo di SOGGETTO, per quanto presente,
    -- non lo soddisfa: sono due layer distinti, e il fallback del
    -- guard porta a un altro TIPO, non all'altro LAYER.
    SET CONSTRAINTS ALL DEFERRED;
    v_ruolo_id := script.fn_get_or_create_soggetto_ruolo(
                      p_soggetto_id  := p_soggetto_id,
                      p_cd_int_ruolo := p_cd_int_ruolo
                  );
    -- Gli indirizzi li scrive il verbo di dominio
    --   anagrafiche.fn_crea_indirizzi_ruolo, come l'applicazione. Si
    --   passa il PRIMO tipo che il requisito del ruolo chiede sulla
    --   natura del soggetto (anagrafiche.fn_indirizzi_obbligatori_ruolo:
    --   il tipo della riga, o il suo ripiego se la natura vieta il
    --   tipo): gli altri li clona il verbo (auto-clone), e i tipi che
    --   il ruolo ha gia' li salta (il ruolo puo' gia' esistere).
    --   Nessun obbligatorio: elenco vuoto, niente.
    PERFORM anagrafiche.fn_crea_indirizzi_ruolo(
        v_ruolo_id,
        COALESCE(
            -- I campi della forma dallo stato (catalogo: comune e CAP;
            --   estera: localita'), come li vuole il guard.
            (SELECT jsonb_build_array(jsonb_build_object(
                        'tipo_indirizzo_id',   o.tipo_indirizzo_id,
                        'indirizzo_libero',    'Via pgTAP ruolo 1',
                        'stato_id',            p_stato_id)
                    || jsonb_strip_nulls(to_jsonb(f)))
               FROM anagrafiche.soggetti_ruoli sr
               JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
              CROSS JOIN LATERAL anagrafiche.fn_indirizzi_obbligatori_ruolo(
                        sr.tipo_ruolo_id, s.tipo_soggetto_dettaglio_id,
                        script.fn_data_operativa()) o
              CROSS JOIN dbops.fn_pgtap_indirizzo_libero_forma(p_stato_id) f
              WHERE sr.id = v_ruolo_id
              ORDER BY o.tipo_indirizzo_id
              LIMIT 1),
            '[]'::jsonb));
    SET CONSTRAINTS ALL IMMEDIATE;
    RETURN v_ruolo_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying, p_stato_id integer)
IS 'Fixture pgTAP: assegna a un soggetto un ruolo gia'' completo dei suoi indirizzi OBBLIGATORI, quelli che il requisito del ruolo chiede sulla natura del soggetto (anagrafiche.fn_indirizzi_obbligatori_ruolo: il tipo della riga obbligatoria, o il suo ripiego se la natura vieta il tipo), lo stesso che pretendono i guard. ⚠️ Gli indirizzi di RUOLO sono un layer separato da quelli di SOGGETTO: hanno una matrice propria e un guard proprio, e un indirizzo di soggetto non soddisfa il guard del ruolo (il suo ripiego porta a un altro TIPO, non all''altro LAYER). Il ruolo lo crea o lo ritrova anagrafiche.fn_get_or_create_soggetto_ruolo; gli indirizzi li scrive il verbo anagrafiche.fn_crea_indirizzi_ruolo dal primo tipo richiesto (copia sugli altri obbligatori, salta quelli gia'' presenti), da un indirizzo libero nella forma che il guard pretende per lo stato (dbops.fn_pgtap_indirizzo_libero_forma: comune e CAP del catalogo, oppure localita''). Come la sorella dbops.fn_pgtap_crea_soggetto_pg, apre e RICHIUDE la finestra dei vincoli differiti. Ritorna il soggetto_ruolo_id. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
