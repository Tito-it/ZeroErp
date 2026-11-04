# ⚙️ Funzione `trgfn_emittenti_fiscali_guard_codice_forma`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_guard_codice_forma()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- text, non anagrafiche.emittenti_fiscali.codice%TYPE: la sigla
    -- normalizzata puo' superare la colonna, e va giudicata qui.
    v_codice text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La sigla dell'emittente e' fatta di MAIUSCOLE e CIFRE,
    --   da 2 a 10 caratteri. Qui si alza il maiuscolo e si
    --   solleva la frase; la rete e' il CHECK di tabella.
    --
    -- ⛔ Perche' serve: quella sigla sta DENTRO il codice
    --   commessa (CMM-<sigla>-<anno>-<9 cifre>), che si legge
    --   separando sul trattino. Una sigla col trattino dentro
    --   rompe la lettura, e il difetto e' MUTO — nessun
    --   duplicato, nessun errore, solo codici illeggibili.
    -- =========================================================

    -- ⭐ La FORMA CANONICA si applica, non si pretende: `acme`
    --   diventa `ACME`, con la forma di ogni codice
    --   (script.fn_codice_normalizzato, rev 2026-11-04).
    -- ⚠️ Si giudica PRIMA di assegnarla: in maiuscolo puo'
    --   allungarsi (ß -> SS), e NEW.codice e' varchar(10).
    v_codice := COALESCE(script.fn_codice_normalizzato(NEW.codice), '');

    -- ⛔ Il resto NON si aggiusta in silenzio. Togliere il
    --   trattino da `AC-ME` darebbe `ACME`, cioe' un
    --   identificatore che la persona non ha scritto — e un
    --   identificatore e' una scelta, non un campo da correggere
    --   di nascosto.
    IF v_codice !~ '^[A-Z0-9]{2,10}$' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_emittenti_fiscali_guard_codice_forma',
            'E_EMITTENTE_CODICE_FORMA_NON_VALIDA',
            jsonb_build_object(
                'campo',  'codice',
                'codice', v_codice),
            NULL::uuid,
            v_codice);
    END IF;

    NEW.codice := v_codice;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()
IS 'Guard BEFORE INSERT / UPDATE OF codice su anagrafiche.emittenti_fiscali: la sigla e'' fatta di MAIUSCOLE e CIFRE, da 2 a 10 caratteri. Alza il maiuscolo e solleva E_EMITTENTE_CODICE_FORMA_NON_VALIDA su tutto il resto. ⛔ PERCHE'' ESISTE: dal 2026-08-31 quella sigla sta DENTRO il codice commessa — CMM-<sigla>-<anno>-<9 cifre> — che si legge separando sul trattino, e una sigla che contiene un trattino produce cinque pezzi invece di quattro. Il difetto sarebbe MUTO: uq_commesse_codice regge, nessun duplicato e nessun errore — cambia solo che quell''emittente ha codici illeggibili PER SEMPRE, perche'' il codice e'' immutabile. ⭐ IL MAIUSCOLO SI ALZA, NON SI RIFIUTA: `acme` diventa `ACME`, perche'' il maiuscolo e'' una forma canonica e non un requisito che l''utente debba conoscere. ⛔ IL TRATTINO INVECE SI RIFIUTA e non si toglie in silenzio: `AC-ME` non diventa `ACME` da solo, perche'' sarebbe un identificatore che la persona non ha scritto — e una sigla e'' una SCELTA, non un campo da correggere di nascosto. ⚠️ DUE PRESIDI SULLA STESSA REGOLA, deliberatamente: chk_emittenti_fiscali_codice_forma e'' la RETE — nessuno la aggira, nemmeno uno script di manutenzione col bypass del lock — e questo guard e'' la FRASE. ⛔ Il guard va tenuto IDENTICO o piu'' stretto del CHECK: se dissentono vince il CHECK, e il guard diventa una promessa che il database non mantiene. ⚠️ Montato anche su UPDATE OF codice benche'' il codice sia immutabile (dbops.automation_lock_columns via script.trgfn_lock_columns): quel lock si aggira con il GUC zeroerp.allow_lock_columns_override, ed e'' esattamente la porta da cui e'' passata la bonifica — un guard sul solo INSERT lascerebbe senza controllo la via di servizio. ⛔ Il codice e'' DATO_ERRATO e non TECNICO: la sigla la scrive una persona in una maschera di configurazione, quindi nel contesto ci va la chiave `campo`. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §5.4. Rev 2026-11-04 (20261104-34, richiesta BE brief-be-codice-maiuscolo §6): la forma canonica e'' quella di script.fn_codice_normalizzato (mappatura Unicode completa, ß -> SS), la stessa del trigger CODICE_MAIUSCOLO: la copia di upper(btrim()) e'' ritirata. La sigla normalizzata si giudica PRIMA di assegnarla a NEW.codice, perche'' puo'' allungarsi oltre varchar(10): la frase parla, non il 22001.';
```

</div>

---
{% include-markdown "signature-core.md" %}
