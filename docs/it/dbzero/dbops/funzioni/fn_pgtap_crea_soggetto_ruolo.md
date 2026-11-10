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
    v_ruolo_id bigint;
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

    -- ⭐ Rev 2026-10-17: gli indirizzi li scrive il verbo di dominio
    --   anagrafiche.fn_crea_indirizzi_ruolo, come l'applicazione (regola
    --   del 2, brief-db-processi-accensione-per-ambiente 2b-1 lotto 2). Si
    --   passa il PRIMO tipo obbligatorio: gli altri li clona il verbo
    --   (auto-clone), e i tipi che il ruolo ha gia' li salta (il ruolo puo'
    --   gia' esistere). Nessun tipo obbligatorio: elenco vuoto, niente.
    PERFORM anagrafiche.fn_crea_indirizzi_ruolo(
        v_ruolo_id,
        COALESCE(
            -- Rev 2026-10-18: i campi della forma dallo stato (catalogo:
            --   comune e CAP; estera: localita'), come li vuole il guard.
            (SELECT jsonb_build_array(jsonb_build_object(
                        'tipo_indirizzo_id',   trti.tipo_indirizzo_id,
                        'indirizzo_libero',    'Via pgTAP ruolo 1',
                        'stato_id',            p_stato_id)
                    || jsonb_strip_nulls(to_jsonb(f)))
               FROM config.tipi_ruolo_tipi_indirizzo trti
               JOIN config.tipi_ruoli tr ON tr.id = trti.tipo_ruolo_id
              CROSS JOIN dbops.fn_pgtap_indirizzo_libero_forma(p_stato_id) f
              WHERE tr.codice_interno = p_cd_int_ruolo
                AND trti.attivo
                AND trti.obbligatorio
              ORDER BY trti.tipo_indirizzo_id
              LIMIT 1),
            '[]'::jsonb));

    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN v_ruolo_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying, p_stato_id integer)
IS 'Fixture pgTAP: assegna a un soggetto un ruolo gia'' completo dei suoi indirizzi OBBLIGATORI, letti da config.tipi_ruolo_tipi_indirizzo. ⚠️ Gli indirizzi di RUOLO sono un layer separato da quelli di SOGGETTO: hanno una matrice propria e un guard proprio, e un indirizzo di soggetto non soddisfa il guard del ruolo (il suo ripiego porta a un altro TIPO, non all''altro LAYER). Il ruolo lo crea o lo ritrova anagrafiche.fn_get_or_create_soggetto_ruolo; gli indirizzi li scrive il verbo anagrafiche.fn_crea_indirizzi_ruolo (copia sui tipi obbligatori, salta quelli gia'' presenti), da un indirizzo libero nella forma che il guard pretende per lo stato (dbops.fn_pgtap_indirizzo_libero_forma: comune e CAP del catalogo, oppure localita''). Come la sorella dbops.fn_pgtap_crea_soggetto_pg, apre e RICHIUDE la finestra dei vincoli differiti. Ritorna il soggetto_ruolo_id. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
