# ⚙️ Funzione `fn_pgtap_crea_soggetto_pg`

```sql
CREATE FUNCTION fn_pgtap_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id integer, p_stato_id integer, p_piva text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id integer DEFAULT 3, p_stato_id integer DEFAULT 1, p_piva text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo: creare per una fixture pgTAP un soggetto PERSONA
--   GIURIDICA gia' valido — testata, dati societari, indirizzi
--   obbligatori, contatto — in un colpo solo.
-- Uso:
--   CREATE TEMP TABLE tmp_s AS
--   SELECT dbops.fn_pgtap_crea_soggetto_pg('Banca Zero pgTAP') AS id;
DECLARE
    v_soggetto_id uuid;
    v_piva        text;
    v_prov_id     integer;
    v_tipo_cont   integer;
    v_n_ind       integer;
BEGIN
    v_piva := COALESCE(p_piva, dbops.fn_pgtap_piva_libera());

    SELECT p.id INTO v_prov_id FROM config.province p ORDER BY p.id LIMIT 1;
    SELECT t.id INTO v_tipo_cont FROM config.tipi_contatti t ORDER BY t.id LIMIT 1;

    -- ⭐ FINESTRA DIFFERITA. I tre guard di completezza su
    --   anagrafiche.soggetti (dati societari, indirizzi, contatti)
    --   sono DEFERRABLE INITIALLY DEFERRED apposta, perche' un
    --   soggetto e' una SAGA e la completezza ha senso verificarla
    --   quando la saga e' finita, non dopo il primo INSERT.
    --   Si costruisce con i guard aperti e si RICHIUDE in fondo.
    --   ⚠️ La richiusura non e' facoltativa: senza, la chiusura in
    --   ROLLBACK del file di test se li porterebbe via NON
    --   verificati, e il test sarebbe verde per sottrazione.
    SET CONSTRAINTS ALL DEFERRED;

    INSERT INTO anagrafiche.soggetti (
        ragione_sociale, cognome, nome, sesso, stato_id,
        partita_iva, codice_fiscale, tipo_soggetto_dettaglio_id,
        storicizza, attivo
    )
    VALUES (
        p_ragione_sociale, NULL, NULL, 'S', p_stato_id,
        -- Per una persona giuridica italiana il codice fiscale
        -- coincide con la partita IVA, e il guard cf/piva lo esige.
        v_piva, v_piva, p_tipo_soggetto_dettaglio_id,
        TRUE, TRUE
    )
    RETURNING id INTO v_soggetto_id;

    INSERT INTO anagrafiche.dati_societari (
        soggetto_id, capitale_sociale, id_prov_iscri_rea, iscrizione_rea,
        socio_unico, liquidazione, destinatario_fe
    )
    -- ⚠️ uq_ds_prov_cea e' UNIQUE su (id_prov_iscri_rea,
    --   iscrizione_rea): il numero REA si deriva dalla partita IVA,
    --   che e' gia' unica per costruzione.
    VALUES (v_soggetto_id, 10000.00, v_prov_id, 'REA-' || v_piva,
            'SM', 'LN', '0000000');

    -- Gli indirizzi ammessi li decide la matrice per il
    -- TIPO SOGGETTO DETTAGLIO, non quella dei ruoli: si legge la
    -- configurazione invece di elencare i codici a mano.
    INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id,
        indirizzo_libero, stato_id, locality, postal_box, administrative_area
    )
    SELECT v_soggetto_id, m.tipo_indirizzo_id,
           'Via pgTAP 1', p_stato_id, 'Roma', '00100', 'RM'
      FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
     WHERE m.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
       AND m.attivo
       AND m.obbligatorio;
    GET DIAGNOSTICS v_n_ind = ROW_COUNT;

    -- Nessun tipo obbligatorio per questo tipo soggetto: ne serve
    -- comunque almeno uno, perche' il guard indirizzi pretende una
    -- riga, non un tipo preciso.
    IF v_n_ind = 0 THEN
        INSERT INTO anagrafiche.indirizzi_soggetti (
            soggetto_id, tipo_indirizzo_id,
            indirizzo_libero, stato_id, locality, postal_box, administrative_area
        )
        SELECT v_soggetto_id, m.tipo_indirizzo_id,
               'Via pgTAP 1', p_stato_id, 'Roma', '00100', 'RM'
          FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
         WHERE m.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
           AND m.attivo
         ORDER BY m.tipo_indirizzo_id
         LIMIT 1;
    END IF;

    INSERT INTO anagrafiche.contatti (
        tipo_contatto_id, soggetto_id, nominativo, email,
        is_default, default_context
    )
    VALUES (v_tipo_cont, v_soggetto_id,
            'Referente ' || p_ragione_sociale,
            'pgtap@example.com', TRUE, 'soggetto');

    -- Saga completa: i tre guard differiti scattano QUI, su un
    -- soggetto finito. E' esattamente la verifica che il modello vuole.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id integer, p_stato_id integer, p_piva text)
IS 'Crea per una fixture pgTAP un soggetto PERSONA GIURIDICA gia'' valido: testata, dati societari, indirizzi obbligatori letti da config.tipi_soggetto_dettaglio_tipi_indirizzo, contatto. ⭐ Apre e RICHIUDE la finestra dei tre guard DEFERRABLE INITIALLY DEFERRED di anagrafiche.soggetti: e'' il punto che nessun test indovinava, perche'' il SET CONSTRAINTS ALL IMMEDIATE del preambolo obbligatorio li fa scattare prima che la saga possa esistere. Al ritorno i vincoli sono IMMEDIATE: un chiamante che dopo costruisce a mano un''altra saga deve aprirsi la sua finestra. Ritorna l''id del soggetto. Brief: work-in-progress/brief-db-bonifica-baseline-pgtap-vendite.md';
```

---
{% include-markdown "signature-core.md" %}
