{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_struttura_se_usato.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_struttura_se_usato`

```sql
CREATE FUNCTION trgfn_articoli_guard_struttura_se_usato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_struttura_se_usato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campo     text;
    v_etichetta text;
    v_porta     text := COALESCE(current_setting('zeroerp.articolo_correggi_struttura', true), '');
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un articolo usato (catalogo.fn_articolo_usato) non cambia
    --   i flag strutturali. BEFORE UPDATE OF le otto colonne.
    -- =========================================================
    -- La prima colonna cambiata, nell'ordine dichiarato.
    v_campo := CASE
        WHEN NEW.is_composito         IS DISTINCT FROM OLD.is_composito         THEN 'is_composito'
        WHEN NEW.is_solo_componente   IS DISTINCT FROM OLD.is_solo_componente   THEN 'is_solo_componente'
        WHEN NEW.natura_vendita_id    IS DISTINCT FROM OLD.natura_vendita_id    THEN 'natura_vendita_id'
        WHEN NEW.causale_onere_id     IS DISTINCT FROM OLD.causale_onere_id     THEN 'causale_onere_id'
        WHEN NEW.listino_tipologia_id IS DISTINCT FROM OLD.listino_tipologia_id THEN 'listino_tipologia_id'
        WHEN NEW.gestito_a_magazzino  IS DISTINCT FROM OLD.gestito_a_magazzino  THEN 'gestito_a_magazzino'
        WHEN NEW.requires_lotto       IS DISTINCT FROM OLD.requires_lotto       THEN 'requires_lotto'
        WHEN NEW.requires_serial      IS DISTINCT FROM OLD.requires_serial      THEN 'requires_serial'
    END;

    IF v_campo IS NULL THEN
        RETURN NEW;
    END IF;

    -- La porta amministratore: solo dal verbo (GUC + proprietario).
    IF v_porta = OLD.id::text
       AND script.fn_is_proprietario_tabella('catalogo.articoli'::regclass) THEN
        RETURN NEW;
    END IF;

    IF catalogo.fn_articolo_usato(OLD.id) THEN
        v_etichetta := CASE v_campo
            WHEN 'is_composito'         THEN 'composito'
            WHEN 'is_solo_componente'   THEN 'solo componente'
            WHEN 'natura_vendita_id'    THEN 'natura di vendita'
            WHEN 'causale_onere_id'     THEN 'causale onere'
            WHEN 'listino_tipologia_id' THEN 'tipologia di listino'
            WHEN 'gestito_a_magazzino'  THEN 'gestito a magazzino'
            WHEN 'requires_lotto'       THEN 'gestito a lotti'
            WHEN 'requires_serial'      THEN 'gestito a matricola'
        END;
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME::text, 'E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE',
            jsonb_build_object(
                'campo',       v_campo,
                'articolo_id', OLD.id),
            NEW.tx_id,
            OLD.codice,
            v_etichetta);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_struttura_se_usato()
IS 'Guard BEFORE UPDATE OF is_composito, is_solo_componente, natura_vendita_id, causale_onere_id, listino_tipologia_id, gestito_a_magazzino, requires_lotto, requires_serial su catalogo.articoli (A-10 di brief-db-articoli-ammessi-per-documento, 2026-10-13): un articolo USATO (catalogo.fn_articolo_usato: documenti, listini, commesse, magazzino, in qualunque stato e di qualunque azienda) non cambia queste colonne -> E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE (campo: la prima cambiata nell''ordine dell''elenco; valori: codice dell''articolo, nome del campo). Il messaggio non dice dove l''articolo e'' usato: puo'' essere un documento di un''altra azienda. Liberi iva_id e le colonne descrittive; codice e uom_id li tiene il lock di colonna. Porta amministratore: GUC transazionale zeroerp.articolo_correggi_struttura = id dell''articolo E proprietario della tabella (script.fn_is_proprietario_tabella), aperta solo dal verbo catalogo.fn_articolo_correggi_struttura (SUPER_ADMIN). Gemello per il form: le regole su queste colonne in dbops.lock_columns_conditional.';
```

</div>

---
{% include-markdown "signature-core.md" %}
