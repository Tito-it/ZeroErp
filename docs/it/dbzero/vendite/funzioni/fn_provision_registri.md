{% include-markdown "it/dbzero/vendite/manual/fn_provision_registri.md" %}
# ⚙️ Funzione `fn_provision_registri`

```sql
CREATE FUNCTION fn_provision_registri(p_emittente_soggetto_ruolo_id bigint, p_famiglia_documento character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provision_registri(p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_famiglia_documento character varying DEFAULT NULL::character varying)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    -- un conteggio: niente colonna da ancorare
    v_creati integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare i registri di numerazione MANCANTI per le
    --   combinazioni (emittente, famiglia) che il filtro
    --   seleziona, e dire quanti ne ha creati. Per la FATTURA
    --   (dal 2026-10-18, R-BE-14) anche i COLLEGAMENTI delle
    --   coppie (tipo documento, natura) scoperte.
    --
    -- Filtri, entrambi opzionali:
    --   - p_emittente_soggetto_ruolo_id NULL = tutti gli
    --     emittenti;
    --   - p_famiglia_documento NULL = tutte le famiglie attive.
    --   ⭐ I due involucri passano uno dei due e lasciano NULL
    --   l'altro: e' l'unica differenza fra le due porte.
    --
    -- Regole:
    --   - le famiglie si LEGGONO dal catalogo, non si elencano:
    --     una famiglia nuova entra da sola;
    --   - un registro per famiglia, valido per tutte le utility;
    --   - idempotente sulla COPPIA (emittente, famiglia), quindi
    --     un registro creato a mano con un altro codice vale lo
    --     stesso e non ne nasce un secondo;
    --   - la FATTURA non ha UN registro ma uno per coppia
    --     (tipo documento, natura): nasce il registro STANDARD
    --     solo per l'emittente che ha coppie scoperte, e le
    --     coppie scoperte si collegano a lui. Il codice e'
    --     sempre quello di fn_codice_registro_provisionato.
    -- =========================================================

    -- 1) I registri. ⭐ UN solo INSERT per tutte le famiglie,
    --    FATTURA compresa: la regola di come nasce un registro
    --    (codice, descrizione, reset, default di forma) e' una,
    --    e cambiano solo le condizioni nel WHERE.
    INSERT INTO vendite.registri_fatturazione (
        codice, descrizione, famiglia_documento,
        emittente_soggetto_ruolo_id, utility_id,
        reset_policy, attivo, prefisso, lunghezza_numero, meta)
    SELECT
        vendite.fn_codice_registro_provisionato(fd.codice_interno, ef.soggetto_ruolo_id),
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
       AND (
             -- a) una famiglia a registro unico: manca il suo
             --    registro (idempotente sulla coppia emittente,
             --    famiglia, qualunque sia il codice).
             (fd.codice_interno <> 'FATTURA'
              AND NOT EXISTS (
                    SELECT 1
                      FROM vendite.registri_fatturazione r
                     WHERE r.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
                       AND r.famiglia_documento          = fd.codice_interno))
             OR
             -- b) la FATTURA: l'emittente ha coppie scoperte e
             --    non ha ancora il registro STANDARD. ⚠️ Lo
             --    standard si ritrova dal CODICE: se esiste ma
             --    e' spento non se ne fa un altro (la UNIQUE sul
             --    codice lo vieterebbe, ed e' giusto: spegnerlo
             --    e' una scelta).
             (fd.codice_interno = 'FATTURA'
              AND ef.soggetto_ruolo_id IN (
                    SELECT c.emittente_soggetto_ruolo_id
                      FROM vendite.fn_coppie_fattura_scoperte(p_emittente_soggetto_ruolo_id) c)
              AND NOT EXISTS (
                    SELECT 1
                      FROM vendite.registri_fatturazione r
                     WHERE r.codice = vendite.fn_codice_registro_provisionato(
                                          fd.codice_interno, ef.soggetto_ruolo_id))));

    GET DIAGNOSTICS v_creati = ROW_COUNT;

    IF p_famiglia_documento IS NOT NULL AND p_famiglia_documento <> 'FATTURA' THEN
        RETURN v_creati;
    END IF;

    -- 2) Le coppie scoperte si collegano al registro standard
    --    del loro emittente, se e' acceso. ⭐ Le coppie le dice
    --    lo STESSO lettore del passo 1: nessuna seconda regola.
    INSERT INTO vendite.tipi_doc_fiscale_registri (
        tipo_doc_fiscale_id, natura_doc_id, registro_id, meta)
    SELECT c.tipo_doc_fiscale_id,
           c.natura_doc_id,
           r.id,
           jsonb_build_object('origine', 'C2-12')
      FROM vendite.fn_coppie_fattura_scoperte(p_emittente_soggetto_ruolo_id) c
      JOIN vendite.registri_fatturazione r
        ON r.codice = vendite.fn_codice_registro_provisionato(
                          'FATTURA', c.emittente_soggetto_ruolo_id)
       AND r.emittente_soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
       AND r.famiglia_documento = 'FATTURA'
       AND r.utility_id IS NULL
       AND r.attivo IS TRUE;

    RETURN v_creati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_provision_registri(p_emittente_soggetto_ruolo_id bigint, p_famiglia_documento character varying)
IS 'PRIMITIVA del provisioning: crea i registri di numerazione MANCANTI per le combinazioni (emittente, famiglia) selezionate dai due filtri — entrambi opzionali, NULL = tutti — e torna quanti REGISTRI ha creato. ⛔ ESISTE PER NON AVERE DUE COPIE della regola di come nasce un registro: il codice (vendite.fn_codice_registro_provisionato), la descrizione, il reset ANNUALE e i default di forma presi dalla famiglia sono un CONTRATTO. Sopra ci stanno due involucri sottili: fn_provision_registri_emittente (trigger su anagrafiche.emittenti_fiscali) e fn_provision_registri_famiglia (la madre che crea una famiglia, e dal 2026-10-18 i trigger su config.tipi_doc_fiscale e config.nature_doc_fiscale per la FATTURA). ⭐ IDEMPOTENTE: sulla COPPIA (emittente, famiglia) per le famiglie a registro unico; sulle coppie (tipo documento, natura) scoperte per la FATTURA. ⭐ I DEFAULT DI FORMA VENGONO DAL CATALOGO DELLE FAMIGLIE. ⭐ Rev 2026-10-18 (20261019-08, R-BE-14, D-14a … D-14d di Tid): la FATTURA non e'' piu'' esclusa. Per ogni emittente con coppie (tipo documento attivo, natura attiva) scoperte — vendite.fn_coppie_fattura_scoperte, che chiama fn_lookup_registro_id — nasce UN registro delle fatture STANDARD (codice FAT-<emittente>, utility NULL) e le coppie scoperte si collegano a lui in vendite.tipi_doc_fiscale_registri. Un emittente configurato a mano lo riceve solo per le coppie che non ha; il CRUD dei registri divide lo standard quando serve. Un registro standard SPENTO non si ricollega ne'' si rifa'': spegnerlo e'' una scelta, e la coppia resta scoperta. I collegamenti non entrano nel numero restituito. Prima di allora nessun emittente nasceva col registro delle fatture e il primo documento fiscale si fermava su fn_get_registro_id. ⚠️ SECURITY DEFINER come l''originale: scrive sui registri leggendo gli emittenti, e la puo'' chiamare un trigger nel contesto di chi crea l''emittente. Piano: brief-be-fe-crud-registri-di-numerazione 11.6 (DB-4); brief-db-processi-accensione-per-ambiente §6.14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
