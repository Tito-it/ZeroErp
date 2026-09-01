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
    --   oggetti che ESISTONO: la tabella, la colonna del numero,
    --   quella del billing account e - dal 2026-09-01 - quella
    --   della serie, che in piu' deve DISCRIMINARE il numero.
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

    -- ⭐ La serie e' OPZIONALE: il vuoto e' la dichiarazione che
    --   questa famiglia una serie non ce l'ha (resi, commesse).
    --   Si guarda il VALORE e non solo il NULL, perche' un form
    --   che non compila il campo manda la stringa vuota.
    ELSIF COALESCE(btrim(NEW.colonna_serie), '') <> ''
          AND NOT EXISTS (
              SELECT 1 FROM pg_attribute a
               WHERE a.attrelid = v_relid
                 AND a.attname  = NEW.colonna_serie
                 AND a.attnum   > 0
                 AND NOT a.attisdropped
          ) THEN
        v_mancante := format('%I.%I.%I',
            NEW.schema_tabella, NEW.nome_tabella, NEW.colonna_serie);
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
                'colonna_serie',           NEW.colonna_serie,
                'riferimento_mancante',    v_mancante),
            NULL::uuid,
            NEW.codice_interno::text,
            v_mancante);
    END IF;

    -- ---------------------------------------------------------
    -- ⭐ LA SERIE DEVE ANCHE DISCRIMINARE IL NUMERO
    --   Qui la colonna ESISTE: il difetto e' un altro, e ha un
    --   codice suo. La serie entra nella chiave del contatore,
    --   quindi apre un secchio che riparte da 1; se il documento
    --   non la porta anche nel proprio vincolo di unicita', quel
    --   numero collide con uno gia' emesso e il documento non si
    --   numera piu'.
    --
    -- ⛔ Il confronto e' sul TESTO della definizione dell'indice,
    --   non sugli attnum di indkey: uq_fatture_numero porta la
    --   serie come COALESCE(serie, ''), cioe' un'espressione, e
    --   un'espressione ha attnum 0. Il predicato «preciso»
    --   rifiuterebbe la FATTURA — verificato.
    -- ⭐ E' lo stesso predicato del test 5 di
    --   db/pgtap/vendite/test-chiave-contatore-assi-dichiarati-v1.sql.
    -- ---------------------------------------------------------
    IF COALESCE(btrim(NEW.colonna_serie), '') <> ''
       AND NOT EXISTS (
           SELECT 1
             FROM pg_index x
            WHERE x.indrelid = v_relid
              AND x.indisunique
              AND pg_get_indexdef(x.indexrelid) ~ ('\m' || NEW.colonna_numero || '\M')
              AND pg_get_indexdef(x.indexrelid) ~ ('\m' || NEW.colonna_serie  || '\M')
       ) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_famiglie_documento_guard_riferimenti',
            'E_FAMIGLIA_DOCUMENTO_SERIE_NON_DISCRIMINA',
            jsonb_build_object(
                'codice_interno', NEW.codice_interno,
                'schema_tabella', NEW.schema_tabella,
                'nome_tabella',   NEW.nome_tabella,
                'colonna_numero', NEW.colonna_numero,
                'colonna_serie',  NEW.colonna_serie,
                -- ⚠️ Il campo che il form deve accendere: la
                --   serie e' il valore che l'operatore ha scelto,
                --   il numero e' un fatto della tabella.
                'campo',          'colonna_serie'),
            NULL::uuid,
            NEW.codice_interno::text,
            NEW.colonna_serie::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_guard_riferimenti()
IS 'Guard `_a10_` su vendite.famiglie_documento: una famiglia ATTIVA deve nominare oggetti che esistono — la tabella del documento, la colonna del numero, quella del billing account e, se dichiarata, quella della serie. ⛔ PERCHE'': quei nomi finiscono in SQL dinamico dentro il presidio sul cambio emittente del billing account, e un refuso resterebbe muto fino al primo spostamento, dove uscirebbe come undefined_table in un movimento che con le famiglie non c''entra. ⭐ SULLA SERIE CI SONO DUE CONTROLLI E DUE CODICI: se la colonna non esiste e'' un refuso come gli altri tre (E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE); se esiste ma NON compare in un vincolo di unicita'' insieme alla colonna del numero e'' il caso peggiore — il nome e'' giusto e si legge — e ha il suo codice E_FAMIGLIA_DOCUMENTO_SERIE_NON_DISCRIMINA, perche'' la serie entra nella chiave del contatore e apre un secchio che riparte da 1: senza il vincolo allargato quel numero collide con uno gia'' emesso. ⛔ IL PREDICATO E'' TESTUALE su pg_get_indexdef e non per attnum, ed e'' verificato: uq_fatture_numero porta la serie come COALESCE(serie, '''''''') — un''espressione, che in pg_index.indkey ha attnum 0 — quindi la versione «precisa» rifiuterebbe la FATTURA e farebbe fallire il migrate sul mirror delle famiglie. E'' lo stesso predicato del test 5 di test-chiave-contatore-assi-dichiarati-v1: due predicati sulla stessa invariante, prima o poi, dissentono. ⚠️ Solo sulle famiglie ATTIVE: una famiglia ritirata puo'' nominare una tabella che non c''e'' piu'', ed e'' storia. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.3 (DB-1).';
```

---
{% include-markdown "signature-core.md" %}
