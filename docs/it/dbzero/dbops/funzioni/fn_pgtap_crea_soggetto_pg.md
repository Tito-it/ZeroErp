{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_soggetto_pg.md" %}
# ⚙️ Funzione `fn_pgtap_crea_soggetto_pg`

```sql
CREATE FUNCTION fn_pgtap_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id integer, p_stato_id integer, p_piva text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id integer DEFAULT 3, p_stato_id integer DEFAULT 1, p_piva text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo: creare per una fixture pgTAP un soggetto PERSONA
--   GIURIDICA gia' valido — testata, dati societari, contatto,
--   indirizzi obbligatori — in un colpo solo, dalle madri del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_s AS
--   SELECT dbops.fn_pgtap_crea_soggetto_pg('Banca Zero pgTAP') AS id;
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_piva        anagrafiche.soggetti.partita_iva%TYPE;
    v_iso2        config.stati.codice_iso2%TYPE;
    v_prov_id     config.province.id%TYPE;
    v_tipo_cont   config.tipi_contatti.id%TYPE;
    v_tipo_ind    config.tipi_soggetto_dettaglio_tipi_indirizzo.tipo_indirizzo_id%TYPE;
    v_forma_id    anagrafiche.dati_societari.forma_giuridica_id%TYPE;
    v_rea_policy  config.forme_giuridiche.rea_policy%TYPE;
    v_cap_policy  config.forme_giuridiche.capitale_sociale_policy%TYPE;
    v_ds_policy   config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
    v_ds          boolean;  -- la natura ammette i dati societari
BEGIN
    v_piva := COALESCE(p_piva, dbops.fn_pgtap_piva_libera());

    -- La madre riceve lo stato per codice ISO2: si legge da quello del
    -- test. Un codice che indica piu' stati lo rifiuta la madre
    -- (E_STATO_ISO2_AMBIGUO), come per l'applicazione.
    SELECT s.codice_iso2 INTO v_iso2 FROM config.stati s WHERE s.id = p_stato_id;
    IF v_iso2 IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_soggetto_pg: nessuno stato con id = %', p_stato_id;
    END IF;

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

    -- I valori dei dati societari li decide la configurazione, non la
    --   fixture: la forma e' la prima AMMESSA dalla natura, REA e
    --   capitale ci sono solo se la forma li prevede, e niente dati
    --   societari se la natura li vieta (dati_societari_policy NONE).
    SELECT tsd.dati_societari_policy INTO v_ds_policy
      FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = p_tipo_soggetto_dettaglio_id;
    v_ds := v_ds_policy IS DISTINCT FROM 'NONE';

    SELECT m.forma_giuridica_id, fg.rea_policy, fg.capitale_sociale_policy
      INTO v_forma_id, v_rea_policy, v_cap_policy
      FROM config.forme_giuridiche_tipi_soggetto_dettaglio m
      JOIN config.forme_giuridiche fg ON fg.id = m.forma_giuridica_id
     WHERE m.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
       AND fg.attivo
       AND fg.stato_id = p_stato_id
       AND anagrafiche.fn_forma_giuridica_ammessa(m.forma_giuridica_id, m.tipo_soggetto_dettaglio_id,
                                                  script.fn_giorno_operativo(now()))
     ORDER BY m.forma_giuridica_id
     LIMIT 1;

    -- La madre del dominio: testata, contatto di default e dati
    -- societari (quando scriverli lo decide lei). Per una persona
    -- giuridica italiana il codice fiscale coincide con la partita IVA.
    -- ⚠️ uq_ds_prov_cea e' UNIQUE su (provincia, numero REA): il numero si
    --   deriva dalla partita IVA, che e' gia' unica per costruzione.
    v_soggetto_id := anagrafiche.fn_crea_soggetto_pg(
        p_ragione_sociale            => p_ragione_sociale,
        p_tipo_soggetto_dettaglio_id => p_tipo_soggetto_dettaglio_id,
        p_email                      => 'pgtap@example.com',
        p_codice_fiscale             => v_piva,
        p_partita_iva                => v_piva,
        p_stato_iso2                 => v_iso2,
        p_forma_giuridica_id         => CASE WHEN v_ds THEN v_forma_id END,
        p_id_prov_iscri_rea          => CASE WHEN v_ds AND v_rea_policy <> 'NONE' THEN v_prov_id END,
        p_iscrizione_rea             => CASE WHEN v_ds AND v_rea_policy <> 'NONE' THEN ('REA-' || v_piva)::varchar END,
        p_capitale_sociale           => CASE WHEN v_ds AND v_cap_policy <> 'NONE' THEN 10000.00 END,
        p_socio_unico                => CASE WHEN v_ds THEN 'SM'::anagrafiche.socio_unico_enum END,
        p_liquidazione               => CASE WHEN v_ds THEN 'LN'::anagrafiche.liquidazione_enum END,
        p_tipo_contatto_id           => v_tipo_cont);

    -- Gli indirizzi dalla madre plurale: un indirizzo del primo tipo
    -- obbligatorio della matrice del tipo di soggetto, e la madre lo
    -- copia sugli altri obbligatori. Una natura senza tipi obbligatori
    -- nasce senza indirizzi: il guard non ne pretende nessuno.
    SELECT m.tipo_indirizzo_id INTO v_tipo_ind
      FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
     WHERE m.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
       AND m.attivo
       AND m.obbligatorio
     ORDER BY m.tipo_indirizzo_id
     LIMIT 1;

    IF v_tipo_ind IS NOT NULL THEN
        -- I campi della forma dallo stato (catalogo: comune e CAP;
        -- estera: localita'), come li vuole il guard della forma.
        PERFORM anagrafiche.fn_crea_indirizzi_soggetto(
            v_soggetto_id,
            (SELECT jsonb_build_array(jsonb_strip_nulls(jsonb_build_object(
                        'tipo_indirizzo_id', v_tipo_ind,
                        'indirizzo_libero',  'Via pgTAP 1',
                        'stato_id',          p_stato_id,
                        'comune_id',         f.comune_id,
                        'codice_postale_id', f.codice_postale_id,
                        'locality',          f.locality,
                        'postal_code',       f.postal_code)))
               FROM dbops.fn_pgtap_indirizzo_libero_forma(p_stato_id) f),
            true);
    END IF;

    -- Saga completa: i tre guard differiti scattano QUI, su un
    -- soggetto finito. E' esattamente la verifica che il modello vuole.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id integer, p_stato_id integer, p_piva text)
IS 'Fixture pgTAP: crea un soggetto PERSONA GIURIDICA gia'' valido, dalle madri del dominio: testata, contatto di default e dati societari da anagrafiche.fn_crea_soggetto_pg, indirizzi da anagrafiche.fn_crea_indirizzi_soggetto. I valori li decide la configurazione: forma giuridica la prima ammessa dalla natura, REA e capitale solo se la forma li prevede, niente dati societari se la natura li vieta; partita IVA libera (dbops.fn_pgtap_piva_libera) o quella del test, che e'' anche il codice fiscale; lo stato per id, passato alla madre col suo codice ISO2 (un codice ambiguo lo rifiuta la madre). Indirizzi: uno del primo tipo obbligatorio della matrice del tipo di soggetto (config.tipi_soggetto_dettaglio_tipi_indirizzo), nella forma dello stato (dbops.fn_pgtap_indirizzo_libero_forma), copiato dalla madre sugli altri obbligatori; una natura senza tipi obbligatori nasce senza indirizzi. Apre e RICHIUDE la finestra dei tre guard DEFERRABLE INITIALLY DEFERRED di anagrafiche.soggetti, che il SET CONSTRAINTS ALL IMMEDIATE del preambolo farebbe scattare prima che la saga esista: al ritorno i vincoli sono IMMEDIATE, e un chiamante che dopo costruisce a mano un''altra saga deve aprirsi la sua finestra. Una natura PF la rifiuta la madre (E_SOGGETTO_CREAZIONE_NATURA_ERRATA): la persona fisica ha la sua porta. Ritorna l''id del soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
