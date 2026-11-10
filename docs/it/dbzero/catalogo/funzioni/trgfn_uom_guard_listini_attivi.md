{% include-markdown "it/dbzero/catalogo/manual/trgfn_uom_guard_listini_attivi.md" %}
# ⚙️ Funzione `trgfn_uom_guard_listini_attivi`

```sql
CREATE FUNCTION trgfn_uom_guard_listini_attivi()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_uom_guard_listini_attivi()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- La riga come jsonb: una funzione sola su due tabelle.
    v_old       jsonb := to_jsonb(OLD);
    v_articolo  catalogo.articoli.id%TYPE;
    v_uom       catalogo.unita_misura.id%TYPE;
    v_uom_altra catalogo.unita_misura.id%TYPE;
    v_oggetto   text;
    -- Conteggi di righe: nessuna colonna dietro.
    v_prezzi    integer;
    v_altre     integer;
    v_primo     date;
    v_dettaglio jsonb;
BEGIN
    -- =========================================================
    -- Scopo: una conversione che si chiude, si spegne o si toglie
    --   non lascia un listino ATTIVO con un prezzo scoperto.
    --   Constraint trigger differito: lo stato di fine transazione.
    -- =========================================================
    IF TG_TABLE_NAME = 'articoli_uom_operativa' THEN
        IF (v_old ->> 'is_base')::boolean THEN
            RETURN NULL;
        END IF;
        v_articolo  := (v_old ->> 'articolo_id')::uuid;
        v_uom       := (v_old ->> 'uom_id')::bigint;
        v_oggetto   := catalogo.fn_uom_conversione_nome(v_articolo, v_uom, NULL);
    ELSE
        v_uom       := (v_old ->> 'uom_from_id')::bigint;
        v_uom_altra := (v_old ->> 'uom_to_id')::bigint;
        v_oggetto   := catalogo.fn_uom_conversione_nome(NULL, v_uom, v_uom_altra);
    END IF;
    -- L'articolo o l'unita' non c'e' piu': i suoi prezzi se ne sono
    -- andati con lui, o parla la FK.
    IF v_oggetto IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT count(*),
           count(*) FILTER (WHERE NOT x.nel_perimetro),
           min(x.primo_giorno),
           COALESCE(jsonb_agg(jsonb_build_object('riga_id', x.riga_id,
                                                 'listino_versione_id', x.listino_versione_id,
                                                 'listino_id', x.listino_id))
                        FILTER (WHERE x.nel_perimetro), '[]'::jsonb)
      INTO v_prezzi, v_altre, v_primo, v_dettaglio
      FROM vendite.fn_listini_attivi_uom_non_convertibili(v_articolo, v_uom, v_uom_altra) x;

    IF v_prezzi > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_uom_guard_listini_attivi', 'E_UOM_CHIUSURA_CON_LISTINI_ATTIVI',
            jsonb_build_object(
                'campo',        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE 'valido_al' END,
                'tabella',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'riga_id',      v_old -> 'id',
                'operazione',   TG_OP,
                'prezzi',       v_dettaglio,
                'primo_giorno', v_primo)
            || CASE WHEN v_articolo IS NULL THEN '{}'::jsonb
                    ELSE jsonb_build_object('articolo_id', v_articolo,
                                            'bersaglio', jsonb_build_array(
                                                jsonb_build_object('tipo', 'ARTICOLO', 'id', v_articolo::text)))
               END,
            (v_old ->> 'tx_id')::uuid,
            v_oggetto,
            v_prezzi::text,
            to_char(v_primo, 'DD/MM/YYYY'),
            v_altre::text);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_uom_guard_listini_attivi()
IS 'Guard dei listini attivi sulle conversioni, su catalogo.articoli_uom_operativa (la mappatura) e catalogo.unita_misura_conversioni (la conversione generale): chiudere, spegnere o togliere una conversione non lascia una versione di listino ATTIVA con un prezzo in un''unita'' che, in un giorno del suo periodo, non si converte per l''articolo. CONSTRAINT TRIGGER AFTER UPDATE OF valido_al, attivo (quando cambiano) e AFTER DELETE, DEFERRABLE INITIALLY DEFERRED: si giudica lo stato di fine transazione, cosi'' «chiudi e inserisci» (la riga nuova che continua la vecchia) passa in qualunque ordine. Legge vendite.fn_listini_attivi_uom_non_convertibili sulla mappatura (articolo, unita'') o sulla coppia di unita'' della conversione. Prezzi scoperti -> E_UOM_CHIUSURA_CON_LISTINI_ATTIVI (valori: la conversione, catalogo.fn_uom_conversione_nome; quanti prezzi; il primo giorno scoperto; quanti in listini fuori dal perimetro di chi chiude; dettaglio dei prezzi nel perimetro: riga, versione, listino). Il rimedio e'' chiudere prima quelle versioni. La riga dell''unita'' base non passa di qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
