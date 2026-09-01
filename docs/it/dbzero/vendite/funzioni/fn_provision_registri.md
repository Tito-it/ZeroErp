# ⚙️ Funzione `fn_provision_registri`

```sql
CREATE FUNCTION fn_provision_registri(p_emittente_soggetto_ruolo_id bigint, p_famiglia_documento character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provision_registri(p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_famiglia_documento character varying DEFAULT NULL::character varying)
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
    --   Creare i registri di numerazione MANCANTI per le
    --   combinazioni (emittente, famiglia non fiscale) che il
    --   filtro seleziona, e dire quanti ne ha creati.
    --
    -- Filtri, entrambi opzionali:
    --   - p_emittente_soggetto_ruolo_id NULL = tutti gli
    --     emittenti;
    --   - p_famiglia_documento NULL = tutte le famiglie attive.
    --   ⭐ I due involucri passano uno dei due e lasciano NULL
    --   l'altro: e' l'unica differenza fra le due porte.
    --
    -- Regole (erano gia' queste, e restano):
    --   - le famiglie si LEGGONO dal catalogo, non si elencano:
    --     una famiglia nuova entra da sola;
    --   - un registro per famiglia, valido per tutte le utility;
    --   - idempotente sulla COPPIA (emittente, famiglia), quindi
    --     un registro creato a mano con un altro codice vale lo
    --     stesso e non ne nasce un secondo.
    --
    -- ⛔ La FATTURA resta fuori: il suo registro dipende da
    --   (tipo documento, natura) e si configura in
    --   vendite.tipi_doc_fiscale_registri.
    -- =========================================================
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
        -- ⭐ IL DEFAULT VIENE DAL CATALOGO DELLE FAMIGLIE: prefisso
        --   e lunghezza sono proprieta' del TIPO DOCUMENTO, e `fd`
        --   E' il tipo documento. Il registro tiene l'EFFETTIVO,
        --   cioe' l'override del sezionale.
        -- ⚠️ Prima del 2026-08-31 si leggevano da
        --   config.sistema_codici, che stava per essere svuotata:
        --   ogni emittente NUOVO sarebbe nato con prefisso NULL e
        --   la commessa a 7 cifre invece di 9, in silenzio e non
        --   subito.
        fd.prefisso_default,
        fd.lunghezza_default,
        -- ⚠️ `origine` non dice CHI ha chiamato ma QUALE
        --   meccanismo ha creato la riga: le righe nate dalle due
        --   porte sono la stessa cosa, e distinguerle inviterebbe
        --   a trattarle diversamente.
        jsonb_build_object('origine', 'C2-12', 'famiglia', fd.codice_interno)
      FROM anagrafiche.emittenti_fiscali ef
     CROSS JOIN vendite.famiglie_documento fd
     WHERE (p_emittente_soggetto_ruolo_id IS NULL
            OR ef.soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
       AND (p_famiglia_documento IS NULL
            OR fd.codice_interno = p_famiglia_documento)
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

COMMENT ON FUNCTION vendite.fn_provision_registri(p_emittente_soggetto_ruolo_id bigint, p_famiglia_documento character varying)
IS 'PRIMITIVA del provisioning: crea i registri di numerazione MANCANTI per le combinazioni (emittente, famiglia non fiscale) selezionate dai due filtri — entrambi opzionali, NULL = tutti — e torna quanti ne ha creati. ⛔ ESISTE PER NON AVERE DUE COPIE della regola di come nasce un registro: il codice (`left(codice_interno,3) || - || soggetto_ruolo_id`), la descrizione, il reset ANNUALE e i default di forma presi dalla famiglia sono un CONTRATTO, e copiato in due funzioni la prima correzione che ne tocca una sola produce due registri diversi per la stessa coppia — visibile sei mesi dopo, su un emittente solo. Sopra ci stanno due involucri sottili: fn_provision_registri_emittente (chiamata da un trigger su anagrafiche.emittenti_fiscali) e fn_provision_registri_famiglia (chiamata dalla madre che crea una famiglia). ⭐ IDEMPOTENTE sulla COPPIA (emittente, famiglia) e non sul codice: un registro creato a mano con un altro codice vale lo stesso e non ne fa nascere un secondo. ⭐ I DEFAULT DI FORMA VENGONO DAL CATALOGO DELLE FAMIGLIE: prefisso e lunghezza sono proprieta'' del TIPO DOCUMENTO, il registro ne tiene l''EFFETTIVO. ⚠️ La FATTURA resta fuori con un letterale, ed e'' un debito DICHIARATO (§11.11 del piano): il suo registro dipende da (tipo documento, natura) e si configura in vendite.tipi_doc_fiscale_registri. ⚠️ SECURITY DEFINER come l''originale: scrive sui registri leggendo gli emittenti, e la puo'' chiamare un trigger nel contesto di chi crea l''emittente. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.6 (DB-4).';
```

---
{% include-markdown "signature-core.md" %}
