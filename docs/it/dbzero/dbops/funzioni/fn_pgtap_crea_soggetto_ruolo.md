# ⚙️ Funzione `fn_pgtap_crea_soggetto_ruolo`

```sql
CREATE FUNCTION fn_pgtap_crea_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying, p_stato_id integer)
```

**Definizione completa:**

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

    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
        indirizzo_libero, stato_id, locality, postal_box, administrative_area
    )
    SELECT v_ruolo_id, trti.tipo_indirizzo_id, NULL,
           'Via pgTAP ruolo 1', p_stato_id, 'Roma', '00100', 'RM'
      FROM config.tipi_ruolo_tipi_indirizzo trti
      JOIN config.tipi_ruoli tr ON tr.id = trti.tipo_ruolo_id
     WHERE tr.codice_interno = p_cd_int_ruolo
       AND trti.obbligatorio
       -- Il ruolo puo' gia' esistere (fn_get_or_create): non si
       -- duplicano gli indirizzi che ha gia'.
       AND NOT EXISTS (
             SELECT 1 FROM anagrafiche.indirizzi i
              WHERE i.soggetto_ruolo_id = v_ruolo_id
                AND i.tipo_indirizzo_id = trti.tipo_indirizzo_id);

    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN v_ruolo_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying, p_stato_id integer)
IS 'Assegna a un soggetto un ruolo gia'' completo dei suoi indirizzi OBBLIGATORI, letti da config.tipi_ruolo_tipi_indirizzo. ⚠️ Gli indirizzi di RUOLO sono un layer separato da quelli di SOGGETTO: hanno una matrice propria e un guard proprio, e un indirizzo di soggetto non soddisfa il guard del ruolo — il suo fallback porta a un altro TIPO, non all''altro LAYER. Come la sorella, apre e RICHIUDE la finestra dei vincoli differiti. Idempotente sugli indirizzi: il ruolo puo'' gia'' esistere (fn_get_or_create_soggetto_ruolo) e non si duplica cio'' che ha gia''. Ritorna il soggetto_ruolo_id. Brief: work-in-progress/brief-db-bonifica-baseline-pgtap-vendite.md';
```

---
{% include-markdown "signature-core.md" %}
