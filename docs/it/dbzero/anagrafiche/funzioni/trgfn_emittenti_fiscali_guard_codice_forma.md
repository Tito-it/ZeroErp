# ⚙️ Funzione `trgfn_emittenti_fiscali_guard_codice_forma`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_guard_codice_forma()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
    --   diventa `ACME`. E' la stessa trasformazione con cui il
    --   changeSet 20260831-22 ha bonificato il pregresso.
    -- ⚠️ btrim prima di upper: uno spazio in coda non e' una
    --   scelta di nessuno.
    NEW.codice := upper(btrim(COALESCE(NEW.codice, '')));

    -- ⛔ Il resto NON si aggiusta in silenzio. Togliere il
    --   trattino da `AC-ME` darebbe `ACME`, cioe' un
    --   identificatore che la persona non ha scritto — e un
    --   identificatore e' una scelta, non un campo da correggere
    --   di nascosto.
    IF NEW.codice !~ '^[A-Z0-9]{2,10}$' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_emittenti_fiscali_guard_codice_forma',
            'E_EMITTENTE_CODICE_FORMA_NON_VALIDA',
            jsonb_build_object(
                'campo',  'codice',
                'codice', NEW.codice),
            NULL::uuid,
            NEW.codice);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()
IS 'Guard BEFORE INSERT / UPDATE OF codice su anagrafiche.emittenti_fiscali: la sigla e'' fatta di MAIUSCOLE e CIFRE, da 2 a 10 caratteri. Alza il maiuscolo e solleva E_EMITTENTE_CODICE_FORMA_NON_VALIDA su tutto il resto. ⛔ PERCHE'' ESISTE: dal 2026-08-31 quella sigla sta DENTRO il codice commessa — CMM-<sigla>-<anno>-<9 cifre> — che si legge separando sul trattino, e una sigla che contiene un trattino produce cinque pezzi invece di quattro. Il difetto sarebbe MUTO: uq_commesse_codice regge, nessun duplicato e nessun errore — cambia solo che quell''emittente ha codici illeggibili PER SEMPRE, perche'' il codice e'' immutabile. ⭐ IL MAIUSCOLO SI ALZA, NON SI RIFIUTA: `acme` diventa `ACME`, perche'' il maiuscolo e'' una forma canonica e non un requisito che l''utente debba conoscere — ed e'' la STESSA trasformazione con cui il changeSet 20260831-22 ha bonificato il pregresso, quindi la regola di ieri e quella di domani sono una riga sola. ⛔ IL TRATTINO INVECE SI RIFIUTA e non si toglie in silenzio: `AC-ME` non diventa `ACME` da solo, perche'' sarebbe un identificatore che la persona non ha scritto — e una sigla e'' una SCELTA, non un campo da correggere di nascosto. ⚠️ La bonifica lo ha fatto, ma li'' l''alternativa era lasciare in giro codici illeggibili per sempre. ⚠️ DUE PRESIDI SULLA STESSA REGOLA, deliberatamente: chk_emittenti_fiscali_codice_forma e'' la RETE — nessuno la aggira, nemmeno uno script di manutenzione col bypass del lock — e questo guard e'' la FRASE. ⛔ Il guard va tenuto IDENTICO o piu'' stretto del CHECK: se dissentono vince il CHECK, e il guard diventa una promessa che il database non mantiene. ⚠️ Montato anche su UPDATE OF codice benche'' il codice sia immutabile (dbops.automation_lock_columns via script.trgfn_lock_columns): quel lock si aggira con il GUC zeroerp.allow_lock_columns_override, ed e'' esattamente la porta da cui e'' passata la bonifica — un guard sul solo INSERT lascerebbe senza controllo la via di servizio. ⛔ Il codice e'' DATO_ERRATO e non TECNICO: la sigla la scrive una persona in una maschera di configurazione, quindi nel contesto ci va la chiave `campo`. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §5.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
