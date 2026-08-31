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
        reset_policy, attivo, prefisso, lunghezza_numero, meta)
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
        -- ⭐ IL DEFAULT VIENE DAL CATALOGO DELLE FAMIGLIE, non piu' dal
        --   catalogo dei formati: quelle righe non ci sono piu' (20260831-53).
        --   ⛔ E' il nodo che ha aggiunto un passo al piano — derivare da una
        --   tabella che si stava per SVUOTARE avrebbe fatto nascere ogni
        --   emittente NUOVO con prefisso NULL e la commessa a 7 cifre invece
        --   di 9: in silenzio, e non oggi ma al primo emittente creato dopo il
        --   rilascio, cioe' quando nessuno guarda.
        -- ⭐ Ed e' la sede giusta a prescindere: prefisso e lunghezza sono
        --   proprieta' del TIPO DOCUMENTO, e `fd` E' il tipo documento. Il
        --   registro tiene l'EFFETTIVO, cioe' l'override del sezionale.
        fd.prefisso_default,
        fd.lunghezza_default,
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
IS 'Da'' a un emittente i registri di numerazione che gli mancano, uno per famiglia non fiscale, gia'' CONFIGURATI: prefisso e lunghezza compresi. ⭐ rev 2026-08-31 (P-12): i default non vengono piu'' da config.sistema_codici ma da vendite.famiglie_documento. ⛔ E'' il nodo che ha aggiunto un passo al piano: derivare da una tabella che si stava per SVUOTARE (il 20260831-53 toglie le quattro righe dei documenti traslocati) avrebbe fatto nascere ogni emittente NUOVO con prefisso NULL e la commessa a 7 cifre invece di 9 — in silenzio, e non subito ma al primo emittente creato dopo il rilascio, cioe'' quando nessuno guarda. ⭐ Ed e'' la sede giusta a prescindere dalla rimozione: prefisso e lunghezza sono proprieta'' del TIPO DOCUMENTO, e vendite.famiglie_documento E'' il tipo documento — mentre il registro tiene il valore EFFETTIVO, cioe'' l''override del sezionale. ⚠️ E'' un passo OBBLIGATO e non un abbellimento: dal 2026-08-31 i generatori leggono la forma SOLO dal registro, senza ripieghi, quindi un registro creato senza produce numeri nudi o piu'' corti, in silenzio. ⛔ Solo le famiglie non fiscali: la FATTURA non ha formato, il suo numero e'' il progressivo nudo. ⚠️ Il prefisso VUOTO resta legittimo: questa funzione non lo impone, gli da'' un default sensato — la differenza fra vietare un caso e non lasciarlo accadere per distrazione. Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, P-12.';
```

---
{% include-markdown "signature-core.md" %}
