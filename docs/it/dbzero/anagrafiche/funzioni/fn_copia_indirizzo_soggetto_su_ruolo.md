# ⚙️ Funzione `fn_copia_indirizzo_soggetto_su_ruolo`

```sql
CREATE FUNCTION fn_copia_indirizzo_soggetto_su_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[], p_istanza_utility_id_destinazione bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[], p_istanza_utility_id_destinazione bigint)
 RETURNS bigint[]
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi      CONSTANT text := 'anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo';
    v_soggetto anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_src      record;  -- la riga sorgente, da una SELECT statica
BEGIN
    -- =========================================================
    -- Scopo:
    --   Copiare un indirizzo del soggetto del ruolo in uno o piu'
    --   tipi sulla chiave di destinazione del ruolo: il ruolo
    --   (istanza NULL) o una sua istanza. Ritorna gli id nuovi,
    --   nell'ordine dei tipi. Tutto o niente.
    --
    -- Regole:
    --   - la sorgente dev'essere del soggetto del ruolo;
    --   - il tipo lo giudica la singolare del ruolo sulla
    --     destinazione; l'istanza di un altro soggetto il guard.
    -- =========================================================
    SELECT sr.soggetto_id
      INTO v_soggetto
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            COALESCE(p_soggetto_ruolo_id::text, '-'));
    END IF;
    IF p_indirizzo_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_indirizzo_soggetto_id'),
            NULL::uuid,
            c_chi,
            'manca l''indirizzo da copiare');
    END IF;
    IF COALESCE(cardinality(p_tipi_indirizzo_codice_interno), 0) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_tipi_indirizzo_codice_interno'),
            NULL::uuid,
            c_chi,
            'manca il tipo di destinazione');
    END IF;

    -- 1. La sorgente, del soggetto del ruolo.
    SELECT isg.indirizzo_dettaglio_id, isg.indirizzo_libero, isg.stato_id,
           isg.comune_id, isg.codice_postale_id, isg.administrative_area,
           isg.locality, isg.sublocality, isg.postal_code
      INTO v_src
      FROM anagrafiche.indirizzi_soggetti isg
     WHERE isg.id = p_indirizzo_soggetto_id
       AND isg.soggetto_id = v_soggetto;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_INDIRIZZO_SOGGETTO_NON_TROVATO',
            jsonb_build_object('soggetto_id', v_soggetto,
                               'soggetto_ruolo_id', p_soggetto_ruolo_id,
                               'indirizzo_soggetto_id', p_indirizzo_soggetto_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Una riga per tipo sulla chiave di destinazione, dal BB.
    RETURN anagrafiche.fn_crea_copie_indirizzo_ruolo(
               p_soggetto_ruolo_id,
               anagrafiche.fn_indirizzo_elemento_da_riga(
                   v_src.indirizzo_dettaglio_id, v_src.indirizzo_libero, v_src.stato_id,
                   v_src.comune_id, v_src.codice_postale_id, v_src.administrative_area,
                   v_src.locality, v_src.sublocality, v_src.postal_code),
               p_istanza_utility_id_destinazione,
               p_tipi_indirizzo_codice_interno);
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[], p_istanza_utility_id_destinazione bigint)
IS 'Verbo: copia un indirizzo del soggetto del ruolo (una riga di anagrafiche.indirizzi_soggetti) in uno o piu'' tipi (codici interni, nell''ordine dato) su una chiave del ruolo: il ruolo (p_istanza_utility_id_destinazione NULL, obbligatorio e senza default) o una sua istanza. E'' il gesto «Copia come…» sulle righe del soggetto nella cascata del drawer in contesto ruolo; in contesto soggetto la copia e'' di anagrafiche.fn_copia_indirizzo_soggetto. Tutto o niente; ritorna gli id delle righe nuove (anagrafiche.indirizzi) nello stesso ordine. Ruolo inesistente E_SOGGETTO_RUOLO_NON_TROVATO; la sorgente dev''essere del soggetto del ruolo (E_INDIRIZZO_SOGGETTO_NON_TROVATO); indirizzo o elenco mancanti o vuoti E_SCRIPT_CHIAMATA_NON_VALIDA. Le righe le scrive il building block anagrafiche.fn_crea_copie_indirizzo_ruolo con l''elemento di anagrafiche.fn_indirizzo_elemento_da_riga: il tipo lo giudica la singolare anagrafiche.fn_crea_indirizzo_ruolo sulla chiave di destinazione (E_TIPO_INDIRIZZO_NON_TROVATO, E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE anche per un tipo ripetuto, E_TIPO_INDIRIZZO_NON_PERMESSO, E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO), l''istanza di un altro soggetto il guard della tabella (E_ISTANZA_ALTRO_SOGGETTO). I tipi proponibili sulla destinazione li dice anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(ruolo, istanza). Il permesso lo controlla il backend. SECURITY INVOKER. Gemello di anagrafiche.fn_copia_indirizzo_ruolo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
