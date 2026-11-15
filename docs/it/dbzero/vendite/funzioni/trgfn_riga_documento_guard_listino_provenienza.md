# ⚙️ Funzione `trgfn_riga_documento_guard_listino_provenienza`

```sql
CREATE FUNCTION trgfn_riga_documento_guard_listino_provenienza()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_riga_documento_guard_listino_provenienza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_componente   boolean := TG_TABLE_NAME LIKE '%\_componenti' ESCAPE '\';
    -- text nudo: NOMI di colonna, con due grafie fra righe e componenti.
    v_col_articolo text;
    v_col_rif      text;
    v_new          jsonb := to_jsonb(NEW);
    v_old          jsonb;
    v_rif_id       vendite.listini_righe.id%TYPE;   -- bigint, come ogni id di testata o riga
    v_emittente    anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_codice       config.codici_errore.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   AFTER INSERT OR UPDATE sulle righe e sui componenti dei
    --   documenti di vendita: la provenienza del prezzo (versione
    --   e riga di listino) e' ammessa per l'azienda del documento
    --   (vendite.fn_check_listino_provenienza_emittente).
    -- =========================================================
    IF NEW.listino_riga_id IS NULL AND NEW.listino_versione_id IS NULL THEN
        RETURN NULL;
    END IF;

    v_col_articolo := CASE WHEN v_componente THEN 'componente_id' ELSE 'articolo_id' END;
    v_col_rif := CASE TG_TABLE_NAME
        WHEN 'preventivi_righe'                         THEN 'preventivo_id'
        WHEN 'ordini_righe'                             THEN 'ordine_id'
        WHEN 'contratti_righe'                          THEN 'contratto_id'
        WHEN 'ddt_righe'                                THEN 'ddt_id'
        WHEN 'offerte_commerciali_eccezioni'            THEN 'offerta_id'
        WHEN 'preventivi_righe_componenti'              THEN 'riga_preventivo_id'
        WHEN 'ordini_righe_componenti'                  THEN 'riga_ordine_id'
        WHEN 'contratti_righe_componenti'               THEN 'riga_contratto_id'
        WHEN 'ddt_righe_componenti'                     THEN 'riga_ddt_id'
        WHEN 'offerte_commerciali_eccezioni_componenti' THEN 'eccezione_offerta_id'
    END;
    -- Una tabella fuori elenco la rifiuta vendite.fn_riga_documento_emittente.

    IF TG_OP = 'UPDATE' THEN
        v_old := to_jsonb(OLD);
        IF  NEW.listino_riga_id     IS NOT DISTINCT FROM OLD.listino_riga_id
        AND NEW.listino_versione_id IS NOT DISTINCT FROM OLD.listino_versione_id
        AND NEW.uom_operativa_id    IS NOT DISTINCT FROM OLD.uom_operativa_id
        AND (v_new ->> v_col_articolo) IS NOT DISTINCT FROM (v_old ->> v_col_articolo)
        AND (v_new ->> v_col_rif)      IS NOT DISTINCT FROM (v_old ->> v_col_rif) THEN
            RETURN NULL;
        END IF;
    END IF;

    v_rif_id    := (v_new ->> v_col_rif)::bigint;
    v_emittente := vendite.fn_riga_documento_emittente(TG_TABLE_NAME::text, v_rif_id);

    v_codice := vendite.fn_check_listino_provenienza_emittente(
        v_emittente,
        (v_new ->> v_col_articolo)::uuid,
        NEW.uom_operativa_id,
        NEW.listino_versione_id,
        NEW.listino_riga_id);

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
                'riferimento_id',      v_rif_id,
                'listino_riga_id',     NEW.listino_riga_id,
                'articolo_id',         v_new ->> v_col_articolo,
                'uom_id',              NEW.uom_operativa_id,
                'listino_versione_id', NEW.listino_versione_id),
            NEW.tx_id,
            NEW.listino_riga_id::text);
    ELSE
        -- Frase chiusa: il listino puo' essere di un'azienda che
        -- l'operatore non vede.
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, v_codice,
            jsonb_build_object(
                'campo',               CASE WHEN NEW.listino_versione_id IS NULL
                                            THEN 'listino_riga_id'
                                            ELSE 'listino_versione_id' END,
                'tabella',             TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',                  NEW.id,
                'riferimento_id',      v_rif_id,
                'listino_riga_id',     NEW.listino_riga_id,
                'listino_versione_id', NEW.listino_versione_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_riga_documento_guard_listino_provenienza()
IS 'Trigger AFTER INSERT OR UPDATE (fase a10) sulle righe principali e sui componenti di preventivi, ordini, contratti, DDT e offerte: la riga e la versione di listino citate per il prezzo sono ammesse per l''azienda del documento (vendite.fn_riga_documento_emittente), con le regole di vendite.fn_check_listino_provenienza_emittente: riga coerente con articolo (articolo_id, o componente_id sui componenti), unita'' di misura operativa e versione; listino dell''azienda; versione non in bozza. Solleva il primo motivo: E_ATTIVITA_LISTINO_RIGA_INCOERENTE, E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO, E_ATTIVITA_LISTINO_VERSIONE_BOZZA, col contesto della tabella, della riga e del riferimento (la testata, o la riga principale di un componente). Ne'' riga ne'' versione: niente. In UPDATE giudica solo se cambia uno dei valori giudicati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
