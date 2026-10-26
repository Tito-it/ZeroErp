{% include-markdown "it/dbzero/vendite/manual/trgfn_famiglie_documento_guard_struttura.md" %}
# ⚙️ Funzione `trgfn_famiglie_documento_guard_struttura`

```sql
CREATE FUNCTION trgfn_famiglie_documento_guard_struttura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_famiglie_documento_guard_struttura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   schema_tabella e nome_tabella ritirate (20261020-33): la tabella
--   e' quella della sorgente; il guard protegge colonna_numero,
--   colonna_billing_account, colonna_serie.
DECLARE
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro), e `v_campo` e' il NOME di una
    --   colonna e non il suo valore — la stessa ragione per cui
    --   script.fn_log_and_raise_error dichiara `v_campo text` e lo difende
    --   con un commento. Non c'e' niente da ancorare.
    v_motivi jsonb;
    v_campo  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare il cambio delle colonne che dicono DOVE VIVE
    --   IL DOCUMENTO — colonna_numero, colonna_billing_account,
    --   colonna_serie (la tabella, dal 2026-10-20, e' quella della
    --   sorgente: l'identita' della famiglia, che non si cambia) —
    --   su una famiglia che ha gia' dei registri.
    --
    -- ⛔ Perche': quelle colonne non descrivono la famiglia, la
    --   fanno funzionare. Il caso peggiore e' colonna_serie
    --   portata a NULL: da quel momento i registri che una serie
    --   ce l'hanno restano con un secchio del contatore che il
    --   documento non sa piu' distinguere, e nessun vincolo se
    --   ne accorge.
    --
    -- ⭐ §12.5.2: QUI NON C'E' IL PREDICATO. Si chiama
    --   script.fn_check_famiglia_documento_struttura_modificabile
    --   e si solleva il codice del primo motivo.
    -- =========================================================

    -- ⭐ IL NO-OP PASSA, ed e' la riga che tiene in piedi il
    --   migrate: i due mirror CSV riscrivono queste colonne a
    --   OGNI migrate con gli stessi valori, e `UPDATE OF` scatta
    --   comunque perche' e' lo statement a nominarle.
    IF NEW.colonna_numero          IS NOT DISTINCT FROM OLD.colonna_numero
       AND NEW.colonna_billing_account IS NOT DISTINCT FROM OLD.colonna_billing_account
       AND NEW.colonna_serie           IS NOT DISTINCT FROM OLD.colonna_serie THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_famiglia_documento_struttura_modificabile(OLD.id);

    -- Nessun motivo: la famiglia non ha ancora registri, la
    -- struttura si cambia liberamente.
    IF v_motivi IS NULL OR jsonb_array_length(v_motivi) = 0 THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Il campo da accendere nel form e' il PRIMO che e'
    --   cambiato davvero, non uno fisso: l'operatore ne ha
    --   toccato uno, e mandarlo a correggerne un altro e' peggio
    --   che non dirglielo.
    v_campo := CASE
        WHEN NEW.colonna_numero          IS DISTINCT FROM OLD.colonna_numero          THEN 'colonna_numero'
        WHEN NEW.colonna_billing_account IS DISTINCT FROM OLD.colonna_billing_account THEN 'colonna_billing_account'
        ELSE 'colonna_serie'
    END;

    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⚠️ `NULL::uuid` e non NEW.tx_id: questo guard sta su un trigger `_a10_`
    --   che, confrontato per NOME INTERO, precede `..._gen_tx_id_ins_upd`
    --   ('a10' < 'gen'), quindi la transazione non e' ancora assegnata.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'trgfn_famiglie_documento_guard_struttura',
        v_motivi,
        v_campo,
        NULL::uuid);

    -- ⭐ Ora RAGGIUNGIBILE, ed e' il ramo «passa»: l'helper tace quando la
    --   check non ha trovato nessun motivo.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_guard_struttura()
IS 'Guard `_a10_` su vendite.famiglie_documento: rifiuta il cambio delle cinque colonne che dicono DOVE VIVE IL DOCUMENTO (schema_tabella, nome_tabella, colonna_numero, colonna_billing_account, colonna_serie) su una famiglia che ha gia'' dei registri. ⛔ PERCHE'': quelle colonne non descrivono la famiglia, la fanno funzionare — il caso peggiore e'' colonna_serie portata a NULL, che lascia i registri con una serie dentro un secchio del contatore che il documento non sa piu'' distinguere, senza che nessun vincolo se ne accorga. ⭐ §12.5.2 — QUI NON C''E'' IL PREDICATO: si chiama script.fn_check_famiglia_documento_struttura_modificabile e si solleva il codice del primo motivo, cosi'' il rifiuto e i campi in sola lettura della maschera non possono divergere. ⚠️ Il `campo` del contesto e'' la PRIMA colonna cambiata DAVVERO e non una fissa: l''operatore ne ha toccato una, e mandarlo a correggerne un''altra e'' peggio che non dirglielo. ⭐ L''USCITA SUL NO-OP E'' OBBLIGATORIA: i mirror 20260830-14 e 20260901-12 riscrivono queste colonne a ogni migrate e `UPDATE OF` scatta comunque, quindi senza il confronto sui VALORI ogni migrate fallirebbe. ⛔ codice_interno NON e'' fra le colonne: lo presidia il lock automatico con E_CODICE_NON_MODIFICABILE, e metterlo anche qui darebbe due rifiuti diversi per la stessa colonna a seconda di quale trigger scatta prima — cioe'' dell''ordine alfabetico, che nessuno ha scelto. ⚠️ tx_id NULL e non NEW.tx_id: `_a10_` scatta prima del trigger che lo genera. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.5 (DB-3). Rev 2026-10-20 (20261020-36, brief-db-grammatica-unica-documenti 2c, G-5): schema_tabella e nome_tabella ritirate; la tabella e'' quella della sorgente, cioe'' l''identita'' della famiglia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
