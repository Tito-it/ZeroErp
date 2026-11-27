{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_guard_codice_forma.md" %}
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
    --
    -- ⭐ Il maiuscolo lo alza anche trg_emittenti_fiscali_a15_codice_maiuscolo_ins_upd
    --   (script.trgfn_codice_maiuscolo, dell'automazione
    --   CODICE_MAIUSCOLO), e va bene cosi': tutti e due usano
    --   script.fn_codice_normalizzato, quindi la regola e' una.
    --   Questo trigger deve giudicare il valore GIA' normalizzato,
    --   prima del CHECK; l'a15 copre ogni colonna codice della
    --   tabella, e su un valore canonico non cambia niente.
    -- =========================================================

    -- ⭐ La FORMA CANONICA si applica, non si pretende: `acme`
    --   diventa `ACME`, con la forma di ogni codice
    --   (script.fn_codice_normalizzato).
    -- ⚠️ Si giudica PRIMA di assegnarla: in maiuscolo puo'
    --   allungarsi (ß -> SS). Assegnata prima, una sigla oltre i
    --   dieci caratteri la rifiuterebbe il CHECK (23514), e una
    --   oltre la colonna (varchar(32)) il 22001: nessuno dei due
    --   dice la frase.
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
IS 'Guard BEFORE INSERT / UPDATE OF codice su anagrafiche.emittenti_fiscali: la sigla e'' fatta di MAIUSCOLE e CIFRE, da 2 a 10 caratteri. Alza il maiuscolo e solleva E_EMITTENTE_CODICE_FORMA_NON_VALIDA su tutto il resto. ⛔ PERCHE'' ESISTE: la sigla sta DENTRO il codice commessa — CMM-<sigla>-<anno>-<9 cifre> — che si legge separando sul trattino, e una sigla che contiene un trattino produce cinque pezzi invece di quattro. Il difetto sarebbe MUTO: uq_commesse_codice regge, nessun duplicato e nessun errore — cambia solo che quell''emittente ha codici illeggibili PER SEMPRE, perche'' il codice e'' immutabile. ⭐ IL MAIUSCOLO SI ALZA, NON SI RIFIUTA: `acme` diventa `ACME`, con la forma canonica di script.fn_codice_normalizzato (mappatura Unicode completa, ß -> SS). ⛔ IL TRATTINO INVECE SI RIFIUTA e non si toglie in silenzio: una sigla e'' una SCELTA, non un campo da correggere di nascosto. ⚠️ La sigla normalizzata si giudica PRIMA di assegnarla a NEW.codice, perche'' in maiuscolo puo'' allungarsi: assegnata prima parlerebbe il CHECK, o oltre la colonna (varchar(32)) il 22001, e nessuno dei due dice la frase. ⚠️ DUE PRESIDI SULLA STESSA REGOLA, deliberatamente: chk_emittenti_fiscali_codice_forma e'' la RETE — nessuno la aggira, nemmeno uno script di manutenzione col bypass del lock — e questo guard e'' la FRASE. ⛔ Il guard va tenuto IDENTICO o piu'' stretto del CHECK: se dissentono vince il CHECK, e il guard diventa una promessa che il database non mantiene. ⭐ Il maiuscolo lo alza anche trg_emittenti_fiscali_a15_codice_maiuscolo_ins_upd (script.trgfn_codice_maiuscolo, automazione CODICE_MAIUSCOLO), con la stessa script.fn_codice_normalizzato: la regola e'' una, questo trigger la applica prima del giudizio, l''a15 copre ogni colonna codice. ⚠️ Montato anche su UPDATE OF codice benche'' il codice sia immutabile (dbops.automation_lock_columns via script.trgfn_lock_columns): quel lock si aggira con il GUC zeroerp.allow_lock_columns_override, e un guard sul solo INSERT lascerebbe senza controllo la via di servizio. ⛔ Il codice e'' DATO_ERRATO e non TECNICO: la sigla la scrive una persona in una maschera di configurazione, quindi nel contesto ci va la chiave `campo`.';
```

</div>

---
{% include-markdown "signature-core.md" %}
