{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga.md" %}
# ⚙️ Funzione `trgfn_attivita_guard_listino_riga`

```sql
CREATE FUNCTION trgfn_attivita_guard_listino_riga()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_guard_listino_riga()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- attivita_fatturabili non ha la colonna: NULL, non si confronta.
    v_versione_new vendite.listini_righe.listino_versione_id%TYPE :=
        (to_jsonb(NEW) ->> 'listino_versione_id')::bigint;
    v_versione_old vendite.listini_righe.listino_versione_id%TYPE;
    -- Il codice del primo motivo, dalla check.
    v_codice       config.codici_errore.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   AFTER INSERT OR UPDATE su commesse_attivita e
    --   attivita_fatturabili: la provenienza del prezzo (versione
    --   e riga di listino) e' ammessa
    --   (vendite.fn_check_listino_provenienza).
    -- =========================================================
    IF NEW.listino_riga_id IS NULL AND v_versione_new IS NULL THEN
        RETURN NULL;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        v_versione_old := (to_jsonb(OLD) ->> 'listino_versione_id')::bigint;
        IF  NEW.listino_riga_id IS NOT DISTINCT FROM OLD.listino_riga_id
        AND NEW.articolo_id     IS NOT DISTINCT FROM OLD.articolo_id
        AND NEW.uom_id          IS NOT DISTINCT FROM OLD.uom_id
        AND NEW.commessa_id     IS NOT DISTINCT FROM OLD.commessa_id
        AND v_versione_new      IS NOT DISTINCT FROM v_versione_old THEN
            RETURN NULL;
        END IF;
    END IF;

    v_codice := vendite.fn_check_listino_provenienza(
        NEW.commessa_id, NEW.articolo_id, NEW.uom_id,
        v_versione_new, NEW.listino_riga_id);

    IF v_codice IS NULL THEN
        RETURN NULL;   -- trigger AFTER: il valore di ritorno e' ignorato
    END IF;

    IF v_codice = 'E_ATTIVITA_LISTINO_RIGA_INCOERENTE' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, v_codice,
            jsonb_build_object(
                'campo',               'listino_riga_id',
                'tabella',             TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',                  NEW.id,
                'commessa_id',         NEW.commessa_id,
                'listino_riga_id',     NEW.listino_riga_id,
                'articolo_id',         NEW.articolo_id,
                'uom_id',              NEW.uom_id,
                'listino_versione_id', v_versione_new),
            NEW.tx_id,
            NEW.listino_riga_id::text);
    ELSE
        -- Frase chiusa: il listino puo' essere di un'azienda che
        -- l'operatore non vede.
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, v_codice,
            jsonb_build_object(
                'campo',               CASE WHEN v_versione_new IS NULL
                                            THEN 'listino_riga_id'
                                            ELSE 'listino_versione_id' END,
                'tabella',             TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',                  NEW.id,
                'commessa_id',         NEW.commessa_id,
                'listino_riga_id',     NEW.listino_riga_id,
                'listino_versione_id', v_versione_new),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_guard_listino_riga()
IS 'Guard AFTER INSERT OR UPDATE su vendite.commesse_attivita e vendite.attivita_fatturabili (brief-db-coerenza-listino-della-riga-di-commessa: D-1 2026-10-15, §6 2026-10-16): la provenienza del prezzo e'' ammessa. Solleva il codice del primo motivo di vendite.fn_check_listino_provenienza: E_ATTIVITA_LISTINO_RIGA_INCOERENTE (la riga di listino non e'' dell''articolo, dell''unita'' di misura o della versione della riga; valori: id della riga di listino), E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO (listino di un altro emittente rispetto alla commessa), E_ATTIVITA_LISTINO_VERSIONE_BOZZA (versione in BOZZA); gli ultimi due a frase chiusa. Tutti TECNICO: la provenienza la scrive il programma dal risolutore. Giudica anche la riga con la sola versione. La versione si legge per nome da to_jsonb(NEW): attivita_fatturabili non la porta (li'' conta quella della riga di listino). AFTER: giudica la riga finale. Ne'' riga ne'' versione -> passa; in UPDATE giudica solo se cambia riga di listino, articolo, unita'' di misura, versione o commessa. Il lato della riga di listino (articolo, unita'' di misura e versione immutabili) lo tiene il lock di colonna, E_LISTINO_RIGA_IDENTITA_IMMUTABILE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
