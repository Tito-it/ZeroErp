# ⚙️ Funzione `trgfn_ordini_righe_guard_onere_senza_data_consegna`

```sql
CREATE FUNCTION trgfn_ordini_righe_guard_onere_senza_data_consegna()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Il nome della prima colonna fuori regola: va nel contesto
    -- (campo), e' un nome di colonna, non un suo valore.
    v_campo     text;
    -- La frase (script.fn_get_stato_testata_documento, RETURNS
    -- TABLE di text): composta.
    v_etichetta text;
    v_codice    catalogo.articoli.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una riga-onere dell'ordine non porta date di consegna
    --   (K-3, brief-db-addebito-trasporto-ordine §8.4): un onere
    --   non si spedisce. BEFORE INSERT OR UPDATE FOR EACH ROW,
    --   WHEN almeno una data e' valorizzata (il resto non arriva qui).
    -- ⭐ «E' un onere» = NOT script.fn_natura_e_merce sulla natura
    --   CONGELATA della riga, gia' derivata da _a10_natura_vendita_
    --   (il nome di questo trigger ordina dopo). Su ordine «non
    --   merce» = onere: lo garantisce l'ammissione.
    -- =========================================================
    IF script.fn_natura_e_merce(NEW.natura_vendita_id) IS NOT FALSE THEN
        -- Merce, o natura che non si risolve: parla la FK.
        RETURN NEW;
    END IF;

    v_campo := CASE
                   WHEN NEW.data_consegna_richiesta_cliente IS NOT NULL
                       THEN 'data_consegna_richiesta_cliente'
                   WHEN NEW.data_consegna_confermata IS NOT NULL
                       THEN 'data_consegna_confermata'
               END;

    IF v_campo IS NULL THEN
        RETURN NEW;   -- nessuna data: in regola (il WHEN lo fa gia')
    END IF;

    SELECT t.etichetta
      INTO v_etichetta
      FROM script.fn_get_stato_testata_documento('ORDINE_VENDITA', NEW.ordine_id) AS t;

    SELECT a.codice INTO v_codice
      FROM catalogo.articoli a
     WHERE a.id = NEW.articolo_id;

    -- «%s, riga %s: l'articolo %s e' un onere, e un onere non porta date di consegna.»
    PERFORM script.fn_log_and_raise_error(
        'vendite', TG_NAME::text,
        'E_RIGA_ONERE_DATA_CONSEGNA',
        jsonb_build_object('campo',     v_campo,
                           'riga_id',   NEW.id,
                           'ordine_id', NEW.ordine_id,
                           'bersaglio', jsonb_build_array(
                               jsonb_build_object('tipo', 'ORDINE_VENDITA_RIGA', 'id', NEW.id))),
        NEW.tx_id,
        COALESCE(v_etichetta, 'Ordine #' || NEW.ordine_id::text),
        COALESCE(NEW.riga_nr::text, '?'),
        COALESCE(v_codice::text, '?'));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna()
IS 'Guard di riga (K-3, brief-db-addebito-trasporto-ordine §8.4, 2026-11-03): una riga-onere di vendite.ordini_righe non porta date di consegna — data_consegna_richiesta_cliente e data_consegna_confermata devono essere NULL, perche'' un onere non si spedisce (falserebbe la data minima della lista, il «riga spedita» e il ritardo). «E'' un onere» = NOT script.fn_natura_e_merce sulla natura CONGELATA della riga, gia'' derivata da _a10_natura_vendita_ (il trigger ordina dopo per nome, e dopo _a10_regole_articolo_). Solleva E_RIGA_ONERE_DATA_CONSEGNA (DATO_ERRATO, campo = la prima data valorizzata; valori: etichetta dell''ordine, numero di riga, codice articolo). Montato BEFORE INSERT OR UPDATE senza OF (la natura la scrive un altro trigger) e WHEN almeno una data NOT NULL. vendite.ddt_righe non ha date di consegna: nessun gemello.';
```

</div>

---
{% include-markdown "signature-core.md" %}
