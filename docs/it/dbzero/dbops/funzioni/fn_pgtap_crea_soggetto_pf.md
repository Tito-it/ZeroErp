{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_soggetto_pf.md" %}
# ⚙️ Funzione `fn_pgtap_crea_soggetto_pf`

```sql
CREATE FUNCTION fn_pgtap_crea_soggetto_pf(p_cognome text, p_nome text, p_tipo_soggetto_dettaglio_id bigint, p_stato_id integer, p_piva text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_soggetto_pf(p_cognome text, p_nome text DEFAULT 'pgTAP'::text, p_tipo_soggetto_dettaglio_id bigint DEFAULT NULL::bigint, p_stato_id integer DEFAULT 1, p_piva text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo: creare per una fixture pgTAP un soggetto PERSONA FISICA
--   gia' valido — testata, contatto, indirizzi obbligatori — in un
--   colpo solo, dalle madri del dominio. Gemello di
--   dbops.fn_pgtap_crea_soggetto_pg.
-- Uso:
--   CREATE TEMP TABLE tmp_s AS
--   SELECT dbops.fn_pgtap_crea_soggetto_pf('Rossi') AS id;
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_natura_id   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_iso2        config.stati.codice_iso2%TYPE;
    v_sesso_pol   config.tipi_soggetto_dettaglio.sesso_policy%TYPE;
    v_piva_obbl   config.tipi_soggetto_dettaglio.piva_obbligatoria%TYPE;
    v_ds_policy   config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
    v_ds          boolean;  -- la natura pretende i dati societari
    v_piva        anagrafiche.soggetti.partita_iva%TYPE;
    v_prov_id     config.province.id%TYPE;
    v_forma_id    anagrafiche.dati_societari.forma_giuridica_id%TYPE;
    v_rea_policy  config.forme_giuridiche.rea_policy%TYPE;
    v_cap_policy  config.forme_giuridiche.capitale_sociale_policy%TYPE;
    v_tipo_ind    config.tipi_soggetto_dettaglio_tipi_indirizzo.tipo_indirizzo_id%TYPE;
BEGIN
    -- La madre riceve lo stato per codice ISO2: si legge da quello del
    -- test. Un codice che indica piu' stati lo rifiuta la madre
    -- (E_STATO_ISO2_AMBIGUO), come per l'applicazione.
    SELECT s.codice_iso2 INTO v_iso2 FROM config.stati s WHERE s.id = p_stato_id;
    IF v_iso2 IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_soggetto_pf: nessuno stato con id = %', p_stato_id;
    END IF;

    v_natura_id := COALESCE(
        p_tipo_soggetto_dettaglio_id,
        (SELECT d.id FROM config.tipi_soggetto_dettaglio d
          WHERE d.codice_interno = 'PR' AND d.stato_id = p_stato_id));
    IF v_natura_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_soggetto_pf: nessun privato (PR) per lo stato id = %', p_stato_id;
    END IF;

    -- I valori li decide la natura, non la fixture. Una natura che non
    -- esiste lascia tutto NULL e la rifiuta la madre.
    SELECT d.sesso_policy, d.piva_obbligatoria, d.dati_societari_policy
      INTO v_sesso_pol, v_piva_obbl, v_ds_policy
      FROM config.tipi_soggetto_dettaglio d WHERE d.id = v_natura_id;
    v_ds   := v_ds_policy = 'REQUIRED';
    v_piva := CASE WHEN p_piva IS NOT NULL THEN p_piva
                   WHEN v_piva_obbl THEN dbops.fn_pgtap_piva_libera() END;

    IF v_ds THEN
        SELECT p.id INTO v_prov_id FROM config.province p ORDER BY p.id LIMIT 1;

        SELECT m.forma_giuridica_id, fg.rea_policy, fg.capitale_sociale_policy
          INTO v_forma_id, v_rea_policy, v_cap_policy
          FROM config.forme_giuridiche_tipi_soggetto_dettaglio m
          JOIN config.forme_giuridiche fg ON fg.id = m.forma_giuridica_id
         WHERE m.tipo_soggetto_dettaglio_id = v_natura_id
           AND fg.attivo
           AND fg.stato_id = p_stato_id
           AND anagrafiche.fn_forma_giuridica_ammessa(m.forma_giuridica_id, m.tipo_soggetto_dettaglio_id,
                                                      script.fn_giorno_operativo(now()))
         ORDER BY m.forma_giuridica_id
         LIMIT 1;
    END IF;

    -- ⭐ FINESTRA DIFFERITA, come il gemello: i tre guard di
    --   completezza su anagrafiche.soggetti (dati societari,
    --   indirizzi, contatti) sono DEFERRABLE INITIALLY DEFERRED
    --   perche' un soggetto e' una SAGA. Si costruisce con i guard
    --   aperti e si RICHIUDE in fondo: senza la richiusura il
    --   ROLLBACK del test se li porterebbe via NON verificati.
    SET CONSTRAINTS ALL DEFERRED;

    -- La madre del dominio: testata, contatto di default e, se la
    -- natura li pretende, i dati societari.
    -- ⚠️ uq_ds_prov_cea e' UNIQUE su (provincia, numero REA): il numero
    --   si deriva dalla partita IVA, che e' unica per costruzione.
    v_soggetto_id := anagrafiche.fn_crea_soggetto_pf(
        p_cognome                    => p_cognome,
        p_nome                       => p_nome,
        p_codice_fiscale             => dbops.fn_pgtap_cf_libero(),
        p_email                      => 'pgtap@example.com',
        p_sesso                      => CASE WHEN v_sesso_pol IS DISTINCT FROM 'NONE' THEN 'M' END,
        p_stato_iso2                 => v_iso2,
        p_tipo_soggetto_dettaglio_id => v_natura_id,
        p_partita_iva                => v_piva,
        p_forma_giuridica_id         => CASE WHEN v_ds THEN v_forma_id END,
        p_id_prov_iscri_rea          => CASE WHEN v_ds AND v_rea_policy <> 'NONE' THEN v_prov_id END,
        p_iscrizione_rea             => CASE WHEN v_ds AND v_rea_policy <> 'NONE' THEN ('REA-' || v_piva)::varchar END,
        p_capitale_sociale           => CASE WHEN v_ds AND v_cap_policy <> 'NONE' THEN 10000.00 END,
        p_socio_unico                => CASE WHEN v_ds THEN 'SM'::anagrafiche.socio_unico_enum END,
        p_liquidazione               => CASE WHEN v_ds THEN 'LN'::anagrafiche.liquidazione_enum END);

    -- Gli indirizzi dalla madre plurale: un indirizzo del primo tipo
    -- obbligatorio della matrice della natura, e la madre lo copia
    -- sugli altri obbligatori. Una natura senza tipi obbligatori
    -- nasce senza indirizzi: il guard non ne pretende nessuno.
    SELECT m.tipo_indirizzo_id INTO v_tipo_ind
      FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
     WHERE m.tipo_soggetto_dettaglio_id = v_natura_id
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
    -- soggetto finito.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_soggetto_pf(p_cognome text, p_nome text, p_tipo_soggetto_dettaglio_id bigint, p_stato_id integer, p_piva text)
IS 'Fixture pgTAP: crea un soggetto PERSONA FISICA gia'' valido, dalle madri del dominio: testata e contatto di default da anagrafiche.fn_crea_soggetto_pf, indirizzi da anagrafiche.fn_crea_indirizzi_soggetto. Gemello di dbops.fn_pgtap_crea_soggetto_pg. La natura e'' quella del test o, se NULL, il privato (PR) dello stato. I valori li decide la natura: codice fiscale libero (dbops.fn_pgtap_cf_libero); sesso solo se la natura lo prevede (sesso_policy); partita IVA quella del test o, se la natura la pretende, una libera (dbops.fn_pgtap_piva_libera); dati societari solo se la natura li pretende (REQUIRED), con la prima forma giuridica ammessa e REA e capitale se la forma li prevede. Lo stato per id, passato alla madre col suo codice ISO2 (un codice ambiguo lo rifiuta la madre). Indirizzi: uno del primo tipo obbligatorio della matrice della natura (config.tipi_soggetto_dettaglio_tipi_indirizzo), nella forma dello stato (dbops.fn_pgtap_indirizzo_libero_forma), copiato dalla madre sugli altri obbligatori; una natura senza tipi obbligatori nasce senza indirizzi. ⭐ Apre e RICHIUDE la finestra dei tre guard DEFERRABLE INITIALLY DEFERRED di anagrafiche.soggetti: al ritorno i vincoli sono IMMEDIATE, e un chiamante che dopo costruisce a mano un''altra saga deve aprirsi la sua finestra. Una natura PG la rifiuta la madre (E_SOGGETTO_CREAZIONE_NATURA_ERRATA). Ritorna l''id del soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
