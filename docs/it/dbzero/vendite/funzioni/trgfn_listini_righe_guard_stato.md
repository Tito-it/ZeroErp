{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_guard_stato.md" %}
# ⚙️ Funzione `trgfn_listini_righe_guard_stato`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: protezione righe listino in base allo stato della versione padre.
--   BOZZA  → passa sempre
--   ATTIVA → ammessa solo se la riga non e` propagata a valle
--   CHIUSA → blocca sempre
-- Perimetro: solo UPDATE e DELETE (INSERT su ATTIVA e` ammesso come rettifica).
DECLARE
    v_stato config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_propagata boolean;
BEGIN
    -- Recupera stato della versione padre
    SELECT s.codice_interno
      INTO v_stato
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = OLD.listino_versione_id;

    -- BOZZA: modifica libera
    IF v_stato = 'BOZZA' THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    -- CHIUSA: blocca sempre
    IF v_stato = 'CHIUSA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.trgfn_listini_righe_guard_stato',
            'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            jsonb_build_object(
                'listino_riga_id', OLD.id,
                'listino_versione_id', OLD.listino_versione_id,
                'stato', v_stato,
                'operazione', TG_OP
            ),
            OLD.tx_id,
            -- ⚠️ ARITA' (2026-08-18): il messaggio comincia con «Operazione %s
            --   non ammessa: ...» e di segnaposto ne ha TRE; qui ne arrivavano
            --   due. Mancava proprio il primo, l'operazione — che il trigger
            --   aveva gia' in mano (TG_OP) e metteva perfino nel context.
            TG_OP, OLD.id::text, v_stato
        );
    END IF;

    -- ATTIVA: verifica propagazione. Una riga e' «propagata» se il suo prezzo
    -- e' stato USATO: la cita una riga di commessa, un'attivita' fatturabile, o
    -- una riga (o un componente) di preventivo, ordine, contratto, DDT, offerta
    -- (D-4 di Tid, 2026-11-13, brief-db-provenienza-prezzo-segue-il-prezzo §8.5:
    -- anche da una bozza). Ogni colonna listino_riga_id ha il suo indice parziale.
    -- Per aggiungere nuove tabelle: UNION ALL qui sotto
    SELECT EXISTS(
        SELECT 1 FROM vendite.commesse_attivita
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.attivita_fatturabili
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.preventivi_righe
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.preventivi_righe_componenti
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.ordini_righe
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.ordini_righe_componenti
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.contratti_righe
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.contratti_righe_componenti
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.ddt_righe
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.ddt_righe_componenti
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.offerte_commerciali_eccezioni
         WHERE listino_riga_id = OLD.id
        UNION ALL
        SELECT 1 FROM vendite.offerte_commerciali_eccezioni_componenti
         WHERE listino_riga_id = OLD.id
    )
    INTO v_propagata;

    IF v_propagata THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.trgfn_listini_righe_guard_stato',
            'E_RIGA_LISTINO_PROPAGATA',
            jsonb_build_object(
                'listino_riga_id', OLD.id,
                'listino_versione_id', OLD.listino_versione_id,
                'stato', v_stato,
                'operazione', TG_OP
            ),
            OLD.tx_id,
            OLD.id::text
        );
    END IF;

    -- ATTIVA e non propagata: rettifica controllata ammessa
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_stato()
IS 'Guard sulle righe di listino, BEFORE UPDATE e DELETE, secondo lo stato della versione (dal vocabolario config.stati_doc_listino_versioni, codice_interno): BOZZA passa; CHIUSA rifiuta sempre (E_RIGA_LISTINO_VERSIONE_CHIUSA); ATTIVA passa solo se la riga non e'' propagata, cioe'' se il suo prezzo non e'' stato usato (E_RIGA_LISTINO_PROPAGATA). Propagata: la cita (listino_riga_id) una riga di commessa, un''attivita'' fatturabile, o una riga principale o un componente di preventivo, ordine, contratto, DDT od offerta, anche in bozza. Per cambiare il prezzo di una riga propagata si fa una versione nuova del listino.';
```

</div>

---
{% include-markdown "signature-core.md" %}
