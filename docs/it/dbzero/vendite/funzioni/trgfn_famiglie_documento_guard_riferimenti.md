{% include-markdown "it/dbzero/vendite/manual/trgfn_famiglie_documento_guard_riferimenti.md" %}
# ⚙️ Funzione `trgfn_famiglie_documento_guard_riferimenti`

```sql
CREATE FUNCTION trgfn_famiglie_documento_guard_riferimenti()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_famiglie_documento_guard_riferimenti()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_relid     oid;
    v_mancante  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una riga di vendite.famiglie_documento deve nominare
    --   oggetti che ESISTONO: la tabella, la colonna del numero
    --   e la colonna del billing account.
    --
    -- ⛔ Perche' serve: il presidio sul cambio emittente del BA
    --   compone quei nomi in SQL dinamico. Senza questo guard un
    --   refuso resterebbe muto fino al primo spostamento di un
    --   billing account, dove uscirebbe come undefined_table —
    --   un errore che non nomina la sua causa e arriva in un
    --   movimento che con le famiglie non c'entra.
    --
    -- ⚠️ Solo sulle famiglie ATTIVE: una famiglia ritirata puo'
    --   nominare una tabella che non c'e' piu'. E' storia.
    -- =========================================================
    IF NOT NEW.attivo THEN
        RETURN NEW;
    END IF;

    -- ⚠️ to_regclass torna NULL invece di sollevare, anche se lo
    --   schema non esiste: e' proprio cio' che serve a un guard
    --   che vuole comporre la propria frase.
    v_relid := to_regclass(format('%I.%I', NEW.schema_tabella, NEW.nome_tabella));

    IF v_relid IS NULL THEN
        v_mancante := format('%I.%I', NEW.schema_tabella, NEW.nome_tabella);

    ELSIF NOT EXISTS (
        SELECT 1 FROM pg_attribute a
         WHERE a.attrelid = v_relid
           AND a.attname  = NEW.colonna_numero
           AND a.attnum   > 0
           AND NOT a.attisdropped
    ) THEN
        v_mancante := format('%I.%I.%I',
            NEW.schema_tabella, NEW.nome_tabella, NEW.colonna_numero);

    ELSIF NOT EXISTS (
        SELECT 1 FROM pg_attribute a
         WHERE a.attrelid = v_relid
           AND a.attname  = NEW.colonna_billing_account
           AND a.attnum   > 0
           AND NOT a.attisdropped
    ) THEN
        v_mancante := format('%I.%I.%I',
            NEW.schema_tabella, NEW.nome_tabella, NEW.colonna_billing_account);
    END IF;

    IF v_mancante IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_famiglie_documento_guard_riferimenti',
            'E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE',
            jsonb_build_object(
                'codice_interno',          NEW.codice_interno,
                'schema_tabella',          NEW.schema_tabella,
                'nome_tabella',            NEW.nome_tabella,
                'colonna_numero',          NEW.colonna_numero,
                'colonna_billing_account', NEW.colonna_billing_account,
                'riferimento_mancante',    v_mancante),
            NULL::uuid,
            NEW.codice_interno::text,
            v_mancante);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_guard_riferimenti()
IS 'Guard BEFORE INSERT / UPDATE OF su vendite.famiglie_documento: una riga ATTIVA deve nominare oggetti che esistono davvero — la tabella, la colonna del numero e la colonna del billing account, verificate su to_regclass e pg_attribute. Solleva E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE. ⛔ E'' il prezzo dell''SQL dinamico, e si paga qui: dal 2026-08-31 anagrafiche.fn_ba_ha_storia_emittente e anagrafiche.fn_get_storia_emittente_ba non elencano piu'' le tabelle dei documenti — le LEGGONO da questo catalogo e le compongono con %I. E'' il modo giusto, perche'' toglie di mezzo l''elenco parallelo che resta indietro, ma sposta un rischio: una riga che nomina una tabella o una colonna inesistente non da'' fastidio a nessuno finche'' qualcuno non prova a spostare un billing account, e li'' fallisce con un undefined_table NUDO — dentro un guard, in un movimento che con le famiglie di documento non c''entra niente, e senza nominare la propria causa. Questo trigger sposta l''errore dal runtime al momento in cui la riga si scrive. ⭐ Non e'' un meccanismo inventato: script.trgfn_config_sistema_codici_sync_gen_codice fa gia'' esattamente questo controllo sulla tabella gemella config.sistema_codici, che dichiara dove vive un codice con la stessa terna schema/tabella/colonna. ⚠️ Solo sulle famiglie ATTIVE, ed e'' una scelta: una famiglia ritirata puo'' legittimamente nominare una tabella che non c''e'' piu'' — e'' storia, non configurazione — e pretendere che resti valida obbligherebbe a cancellare la riga, cioe'' a perdere il fatto che quella famiglia e'' esistita. ⛔ Ma `attivo` sta fra le colonne di UPDATE OF: RIACCENDERE una famiglia ri-attraversa il controllo. ⚠️ UPDATE OF e non UPDATE nudo: con un UPDATE generico ogni ritocco alla descrizione o al meta rivaliderebbe i riferimenti, e una famiglia ritirata male diventerebbe non piu'' modificabile con un errore che parla di colonne che nessuno stava toccando — stessa ragione del guard sulle fatture (20260830-10). ⚠️ SECURITY INVOKER (il default): pg_attribute e'' leggibile da chiunque, e un DEFINER sarebbe privilegio in piu'' senza contropartita. ⛔ Il codice e'' TECNICO: una riga di questo catalogo non la scrive un operatore in un dialog, la scrive una migrazione — quindi niente chiave `campo` nel contesto. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-18.';
```

---
{% include-markdown "signature-core.md" %}
