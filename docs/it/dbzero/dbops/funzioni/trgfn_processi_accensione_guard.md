# ⚙️ Funzione `trgfn_processi_accensione_guard`

```sql
CREATE FUNCTION trgfn_processi_accensione_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_processi_accensione_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice                    dbops.processi.codice%TYPE;
    v_canale                    dbops.processi.canale%TYPE;
    v_obsoleto_dal              dbops.processi.obsoleto_dal%TYPE;
    v_spegnibile                dbops.processi.spegnibile%TYPE;
    v_accendibile_in_produzione dbops.processi.accendibile_in_produzione%TYPE;
    -- La risposta del predicato: nessuna colonna di cui sia
    -- il riflesso.
    v_ammessa                   boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La scelta a mano vale solo dove c'e' una sveglia da
    --   accendere o spegnere, non spegne mai un processo
    --   non spegnibile (A-5) e non accende in PRODUZIONE un
    --   processo non accendibile (R-BE-5).
    --
    -- Ordine dei rifiuti (il primo che parla e' quello che
    -- l'operatore legge):
    --   1. senza sveglia: non c'e' niente da scegliere;
    --   2. non spegnibile: lo spegnimento e' vietato;
    --   3. non accendibile in PRODUZIONE: l'accensione e'
    --      vietata;
    --   4. motivo vuoto: la scelta e' incompleta.
    -- =========================================================
    SELECT p.codice, p.canale, p.obsoleto_dal, p.spegnibile,
           p.accendibile_in_produzione
      INTO v_codice, v_canale, v_obsoleto_dal, v_spegnibile,
           v_accendibile_in_produzione
      FROM dbops.processi p
     WHERE p.id = NEW.processo_id;

    -- Un processo inesistente lo rifiuta la FK: qui non si
    -- anticipa.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    -- 1. Senza sveglia: CODA (li avvia una persona) o ritirato.
    IF v_canale = 'CODA' OR v_obsoleto_dal IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'trgfn_processi_accensione_guard', 'E_PROCESSO_SENZA_SVEGLIA',
            jsonb_build_object('processo_codice', v_codice,
                               'canale',          v_canale,
                               'obsoleto_dal',    v_obsoleto_dal),
            NULL::uuid,
            v_codice);
    END IF;

    -- 2. Non spegnibile: si puo' solo confermare acceso.
    --    ⚠️ IS FALSE e non NOT: spegnibile NULL su un processo
    --    con sveglia e' un catalogo incompleto, e lo rifiuta
    --    chk_processi_accensione quando e' convalidato.
    IF NOT NEW.acceso AND v_spegnibile IS FALSE THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'trgfn_processi_accensione_guard', 'E_PROCESSO_NON_SPEGNIBILE',
            jsonb_build_object('processo_codice', v_codice,
                               'campo',           'acceso'),
            NULL::uuid,
            v_codice);
    END IF;

    -- 3. Non accendibile in PRODUZIONE. Il predicato e' quello
    --    della regola dello stato effettivo; NULL = ambiente non
    --    dichiarato, e lo dice il lettore che decide.
    v_ammessa := dbops.fn_accensione_a_mano_ammessa_su_valori(
                     NEW.acceso,
                     v_accendibile_in_produzione,
                     script.fn_ambiente_dichiarato());

    IF v_ammessa IS NOT TRUE THEN
        IF v_ammessa IS NULL THEN
            -- Solleva E_CONFIG_MANCANTE.
            PERFORM script.fn_ambiente_installazione();
        END IF;

        PERFORM script.fn_log_and_raise_error(
            'dbops', 'trgfn_processi_accensione_guard', 'E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE',
            jsonb_build_object('processo_codice', v_codice,
                               'campo',           'acceso'),
            NULL::uuid,
            v_codice);
    END IF;

    -- 4. Il motivo: chi viene dopo deve capire perche'.
    IF NEW.motivo IS NULL OR btrim(NEW.motivo) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'trgfn_processi_accensione_guard', 'E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO',
            jsonb_build_object('processo_codice', v_codice,
                               'campo',           'motivo'),
            NULL::uuid,
            v_codice);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_processi_accensione_guard()
IS 'Guard BEFORE INSERT OR UPDATE su dbops.processi_accensione. In ordine: un processo senza sveglia (canale CODA o ritirato) non ha scelta a mano (E_PROCESSO_SENZA_SVEGLIA); un processo non spegnibile non si spegne (E_PROCESSO_NON_SPEGNIBILE, A-5); in un''installazione PRODUZIONE un processo non accendibile (dbops.processi.accendibile_in_produzione = false) non si accende a mano (E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE, R-BE-5; predicato dbops.fn_accensione_a_mano_ammessa_su_valori, ambiente non dichiarato -> E_CONFIG_MANCANTE); il motivo e'' obbligatorio (E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO). La regola e'' del dato: il verbo dbops.fn_imposta_accensione_processo non la ripete. Se il catalogo cambia dopo che una riga e'' stata scritta (un non spegnibile spento, un non accendibile acceso), lo stato effettivo (dbops.fn_processo_acceso_su_valori) ignora la riga. Brief: brief-db-processi-accensione-per-ambiente.';
```

---
{% include-markdown "signature-core.md" %}
