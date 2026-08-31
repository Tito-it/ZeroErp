{% include-markdown "it/dbzero/vendite/manual/fn_provision_registri_emittente.md" %}
# ⚙️ Funzione `fn_provision_registri_emittente`

```sql
CREATE FUNCTION fn_provision_registri_emittente(p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provision_registri_emittente(p_emittente_soggetto_ruolo_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_creati integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dare a un emittente i registri di numerazione delle
    --   famiglie NON fiscali che ancora non ha, e dire quanti
    --   ne ha creati.
    --
    -- Regole:
    --   - le famiglie si LEGGONO dal catalogo, non si elencano:
    --     una famiglia nuova entra da sola;
    --   - un registro per famiglia, valido per tutte le utility;
    --   - idempotente: guarda la COPPIA (emittente, famiglia),
    --     quindi un registro creato a mano con un altro codice
    --     vale lo stesso e non ne nasce un secondo.
    --
    -- ⛔ La FATTURA resta fuori: il suo registro dipende da
    --   (tipo documento, natura) e si configura in
    --   vendite.tipi_doc_fiscale_registri.
    -- =========================================================
    IF p_emittente_soggetto_ruolo_id IS NULL THEN
        RETURN 0;
    END IF;

    INSERT INTO vendite.registri_fatturazione (
        codice, descrizione, famiglia_documento,
        emittente_soggetto_ruolo_id, utility_id,
        reset_policy, attivo, meta)
    SELECT
        -- ⚠️ Prime tre lettere della famiglia + id dell'emittente:
        --   deterministico, unico per costruzione, e dentro i 16
        --   caratteri della colonna. ⛔ NON la sigla
        --   dell'emittente: e' varchar(32) contro 16, e troncarla
        --   su una UNIQUE trasformerebbe due sigle simili in una
        --   collisione. La parte parlante sta nella descrizione.
        left(fd.codice_interno, 3) || '-' || ef.soggetto_ruolo_id::text,
        'Registro ' || lower(fd.descrizione) || ' — ' || ef.codice,
        fd.codice_interno,
        ef.soggetto_ruolo_id,
        NULL,
        'ANNUALE',
        TRUE,
        jsonb_build_object('origine', 'C2-12', 'famiglia', fd.codice_interno)
      FROM anagrafiche.emittenti_fiscali ef
     CROSS JOIN vendite.famiglie_documento fd
     WHERE ef.soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
       AND fd.attivo IS TRUE
       AND fd.codice_interno <> 'FATTURA'
       AND NOT EXISTS (
             SELECT 1
               FROM vendite.registri_fatturazione r
              WHERE r.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
                AND r.famiglia_documento          = fd.codice_interno);

    GET DIAGNOSTICS v_creati = ROW_COUNT;
    RETURN v_creati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_provision_registri_emittente(p_emittente_soggetto_ruolo_id bigint)
IS 'Da a un emittente i registri di numerazione delle famiglie NON fiscali (DDT, ORDINE, COMMESSA, RESO) che ancora non ha, e ritorna quanti ne ha creati. ⭐ E'' la SEDE UNICA della composizione — codice, descrizione, meta — e per questo esiste come funzione invece di stare dentro il trigger: sono una regola, non tre righe di INSERT, e se il trigger se la riscrivesse il giorno in cui il formato cambia ci sarebbero due verita'', con quella che nessuno guarda rimasta indietro in silenzio. ℹ️ Il primo passo (changeSet 20260831-03) porta la stessa regola scritta in linea: era un''esecuzione una tantum, fatta prima che questa sede esistesse, e resta storia. ⭐ Le famiglie si LEGGONO dal catalogo vendite.famiglie_documento e non si elencano: una famiglia nuova entra da sola. ⚠️ Un registro per famiglia con utility_id NULL, cioe'' «vale per tutte»: chi vorra'' separare per utility aggiunge una riga piu'' specifica, e vendite.fn_lookup_registro_documento la preferisce da se''. ⚠️ Idempotente, e il predicato guarda la COPPIA (emittente, famiglia) e non il codice: un registro creato a mano con un altro nome vale lo stesso e non ne fa nascere un secondo. ⚠️ SECURITY DEFINER perche'' chi crea un emittente e'' un amministratore di ANAGRAFICA e non e'' detto abbia l''INSERT su vendite.registri_fatturazione: senza, la creazione dell''emittente fallirebbe su un permesso, cioe'' su un messaggio che non parla del problema. search_path fissato. ⛔ La FATTURA resta fuori: il suo registro dipende da (tipo documento, natura) e si configura in vendite.tipi_doc_fiscale_registri — fabbricarne uno «di famiglia» creerebbe un sezionale che nessuno risolve e che a video sembrerebbe configurazione buona. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-12.';
```

---
{% include-markdown "signature-core.md" %}
