{% include-markdown "it/dbzero/vendite/manual/trgfn_famiglie_documento_guard_struttura.md" %}
# ⚙️ Funzione `trgfn_famiglie_documento_guard_struttura`

```sql
CREATE FUNCTION trgfn_famiglie_documento_guard_struttura()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_famiglie_documento_guard_struttura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
    v_campo  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare il cambio delle colonne che dicono DOVE VIVE
    --   IL DOCUMENTO — schema_tabella, nome_tabella,
    --   colonna_numero, colonna_billing_account, colonna_serie —
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
    IF NEW.schema_tabella          IS NOT DISTINCT FROM OLD.schema_tabella
       AND NEW.nome_tabella            IS NOT DISTINCT FROM OLD.nome_tabella
       AND NEW.colonna_numero          IS NOT DISTINCT FROM OLD.colonna_numero
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

    v_primo := v_motivi -> 0;

    -- ⚠️ Il campo da accendere nel form e' il PRIMO che e'
    --   cambiato davvero, non uno fisso: l'operatore ne ha
    --   toccato uno, e mandarlo a correggerne un altro e' peggio
    --   che non dirglielo.
    v_campo := CASE
        WHEN NEW.schema_tabella          IS DISTINCT FROM OLD.schema_tabella          THEN 'schema_tabella'
        WHEN NEW.nome_tabella            IS DISTINCT FROM OLD.nome_tabella            THEN 'nome_tabella'
        WHEN NEW.colonna_numero          IS DISTINCT FROM OLD.colonna_numero          THEN 'colonna_numero'
        WHEN NEW.colonna_billing_account IS DISTINCT FROM OLD.colonna_billing_account THEN 'colonna_billing_account'
        ELSE 'colonna_serie'
    END;

    -- ⚠️ tx_id NULL e non NEW.tx_id: questo guard e' `_a10_` e
    --   scatta PRIMA di trg_famiglie_documento_gen_tx_id_ins_upd
    --   (ordine alfabetico: 'a10' < 'gen'), quindi NEW.tx_id qui
    --   porta ancora il valore vecchio.
    PERFORM script.fn_log_and_raise_error(
        'vendite',
        'trgfn_famiglie_documento_guard_struttura',
        v_primo ->> 'codice',
        COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
            || jsonb_build_object('campo', v_campo),
        NULL::uuid,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));

    -- Irraggiungibile: la riga sopra solleva sempre.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_guard_struttura()
IS 'Guard `_a10_` su vendite.famiglie_documento: rifiuta il cambio delle cinque colonne che dicono DOVE VIVE IL DOCUMENTO (schema_tabella, nome_tabella, colonna_numero, colonna_billing_account, colonna_serie) su una famiglia che ha gia'' dei registri. ⛔ PERCHE'': quelle colonne non descrivono la famiglia, la fanno funzionare — il caso peggiore e'' colonna_serie portata a NULL, che lascia i registri con una serie dentro un secchio del contatore che il documento non sa piu'' distinguere, senza che nessun vincolo se ne accorga. ⭐ §12.5.2 — QUI NON C''E'' IL PREDICATO: si chiama script.fn_check_famiglia_documento_struttura_modificabile e si solleva il codice del primo motivo, cosi'' il rifiuto e i campi in sola lettura della maschera non possono divergere. ⚠️ Il `campo` del contesto e'' la PRIMA colonna cambiata DAVVERO e non una fissa: l''operatore ne ha toccato una, e mandarlo a correggerne un''altra e'' peggio che non dirglielo. ⭐ L''USCITA SUL NO-OP E'' OBBLIGATORIA: i mirror 20260830-14 e 20260901-12 riscrivono queste colonne a ogni migrate e `UPDATE OF` scatta comunque, quindi senza il confronto sui VALORI ogni migrate fallirebbe. ⛔ codice_interno NON e'' fra le colonne: lo presidia il lock automatico con E_CODICE_NON_MODIFICABILE, e metterlo anche qui darebbe due rifiuti diversi per la stessa colonna a seconda di quale trigger scatta prima — cioe'' dell''ordine alfabetico, che nessuno ha scelto. ⚠️ tx_id NULL e non NEW.tx_id: `_a10_` scatta prima del trigger che lo genera. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.5 (DB-3).';
```

---
{% include-markdown "signature-core.md" %}
