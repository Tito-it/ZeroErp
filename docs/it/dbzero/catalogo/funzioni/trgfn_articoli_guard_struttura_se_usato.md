{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_struttura_se_usato.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_struttura_se_usato`

```sql
CREATE FUNCTION trgfn_articoli_guard_struttura_se_usato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_struttura_se_usato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Il nome di una colonna di catalogo.articoli: nessuna colonna ne
    -- e' il riflesso, quindi text.
    v_colonna   text;
    v_campo     text;
    v_nuovo     jsonb := to_jsonb(NEW);
    v_vecchio   jsonb := to_jsonb(OLD);
    v_porta     text := COALESCE(current_setting('zeroerp.articolo_correggi_struttura', true), '');
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un articolo usato (catalogo.fn_articolo_usato) non cambia
    --   le colonne strutturali (catalogo.fn_articolo_colonne_struttura).
    --   BEFORE UPDATE OF le stesse colonne.
    -- =========================================================
    -- La prima colonna cambiata, nell'ordine della dichiarazione.
    FOREACH v_colonna IN ARRAY catalogo.fn_articolo_colonne_struttura() LOOP
        IF v_nuovo -> v_colonna IS DISTINCT FROM v_vecchio -> v_colonna THEN
            v_campo := v_colonna;
            EXIT;
        END IF;
    END LOOP;

    IF v_campo IS NULL THEN
        RETURN NEW;
    END IF;

    -- La porta amministratore: solo dal verbo (GUC + proprietario).
    IF v_porta = OLD.id::text
       AND script.fn_is_proprietario_tabella('catalogo.articoli'::regclass) THEN
        RETURN NEW;
    END IF;

    IF catalogo.fn_articolo_usato(OLD.id) THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME::text, 'E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE',
            jsonb_build_object(
                'campo',       v_campo,
                'articolo_id', OLD.id),
            NEW.tx_id,
            OLD.codice,
            catalogo.fn_articolo_flag_etichetta(v_campo));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_struttura_se_usato()
IS 'Guard BEFORE UPDATE OF le colonne strutturali su catalogo.articoli: un articolo USATO (catalogo.fn_articolo_usato: documenti, listini, commesse, magazzino, in qualunque stato e di qualunque azienda) non cambia le colonne di catalogo.fn_articolo_colonne_struttura -> E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE (campo: la prima cambiata nell''ordine della dichiarazione; valori: codice dell''articolo e nome leggibile della colonna, da catalogo.fn_articolo_flag_etichetta). Il messaggio non dice dove l''articolo e'' usato: puo'' essere un documento di un''altra azienda. Liberi iva_id e le colonne descrittive; codice e uom_id li tiene il lock di colonna. Porta amministratore: GUC transazionale zeroerp.articolo_correggi_struttura = id dell''articolo E proprietario della tabella (script.fn_is_proprietario_tabella), aperta solo dal verbo catalogo.fn_articolo_correggi_struttura (SUPER_ADMIN). L''elenco UPDATE OF del trigger e le regole gemelle del form in dbops.lock_columns_conditional sono copie della dichiarazione: le confronta il pgTAP catalogo/test-articolo-colonne-struttura-v1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
