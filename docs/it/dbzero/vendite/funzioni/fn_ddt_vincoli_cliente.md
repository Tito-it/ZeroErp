{% include-markdown "it/dbzero/vendite/manual/fn_ddt_vincoli_cliente.md" %}
# ⚙️ Funzione `fn_ddt_vincoli_cliente`

```sql
CREATE FUNCTION fn_ddt_vincoli_cliente(p_ddt_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_vincoli_cliente(p_ddt_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid uuid)
 RETURNS TABLE(vincolo text, sorgente character varying, billing_account_id bigint, etichetta text)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- ⚠️ Tipi nudi DICHIARATI: vincolo e' un selettore (SORGENTE |
--   FULFILLMENT) senza colonna di vocabolario; etichetta e' una frase
--   composta per l'operatore.
DECLARE
    v_sorgente  config.sorgenti.codice_interno%TYPE;
    v_ba        vendite.ddt.billing_account_id%TYPE;
    v_etichetta text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Da dove viene il cliente di una bolla, cioe' che cosa
    --   gli impedisce di cambiare (D-6 di brief-db-esecutivi-ba-
    --   coppia: «un esecutivo derivato ha il BA della sua
    --   sorgente»). Una riga per vincolo:
    --   - SORGENTE: la sorgente di testata e' un ordine o un reso
    --     (ORDINE_VENDITA, RESO_VENDITA). billing_account_id e'
    --     quello della sorgente (NULL compreso); etichetta NULL =
    --     dichiarata e non trovata (o invisibile sotto RLS);
    --   - FULFILLMENT: la bolla evade gia' righe d'ordine;
    --     etichetta = il primo ordine evaso.
    --   Nessuna riga: il cliente della bolla e' libero.
    -- E' il predicato condiviso (brief-db-testata-dopo-emissione
    --   §11, R-DB-1): lo usano il guard
    --   vendite.trgfn_ddt_guard_cliente_sorgente, che solleva, e
    --   la capability script.fn_available_actions_ddt, che spegne
    --   il campo. I due non possono rispondere in due modi.
    -- ⚠️ INVOKER come il guard: ordine, reso e fulfillment si
    --   leggono sotto la RLS di chi scrive.
    -- =========================================================

    -- 1. La sorgente di testata.
    IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_uid IS NOT NULL THEN
        SELECT s.codice_interno INTO v_sorgente
          FROM config.sorgenti s
         WHERE s.id = p_sorgente_tipo_id;

        IF v_sorgente = 'ORDINE_VENDITA' THEN
            SELECT o.billing_account_id,
                   'ordine ' || COALESCE(o.numero, '#' || o.id::text)
              INTO v_ba, v_etichetta
              FROM vendite.ordini o
             WHERE o.uid = p_sorgente_uid;
        ELSIF v_sorgente = 'RESO_VENDITA' THEN
            SELECT r.billing_account_id,
                   'reso ' || COALESCE(r.numero, '#' || r.id::text)
              INTO v_ba, v_etichetta
              FROM vendite.resi r
             WHERE r.uid = p_sorgente_uid;
        END IF;

        IF v_sorgente IN ('ORDINE_VENDITA', 'RESO_VENDITA') THEN
            vincolo            := 'SORGENTE';
            sorgente           := v_sorgente;
            billing_account_id := v_ba;
            etichetta          := v_etichetta;
            RETURN NEXT;
        END IF;
    END IF;

    -- 2. Le righe d'ordine che la bolla evade gia': hanno il BA
    --    di prima.
    IF p_ddt_id IS NOT NULL THEN
        v_etichetta := NULL;
        SELECT 'ordine ' || COALESCE(o.numero, '#' || o.id::text)
          INTO v_etichetta
          FROM vendite.ddt_righe dr
          JOIN vendite.ordini_righe_fulfillment ful ON ful.ddt_riga_id = dr.id
          JOIN vendite.ordini_righe orr ON orr.id = ful.ordine_riga_id
          JOIN vendite.ordini o ON o.id = orr.ordine_id
         WHERE dr.ddt_id = p_ddt_id
         ORDER BY ful.id
         LIMIT 1;

        IF FOUND THEN
            vincolo            := 'FULFILLMENT';
            sorgente           := NULL;
            billing_account_id := NULL;
            etichetta          := v_etichetta;
            RETURN NEXT;
        END IF;
    END IF;

    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_vincoli_cliente(p_ddt_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid uuid)
IS 'Building block (2026-10-11, brief-db-testata-dopo-emissione §11, R-DB-1): da dove viene il cliente di una bolla, cioe'' che cosa gli impedisce di cambiare (D-6 di brief-db-esecutivi-ba-coppia). Una riga per vincolo: SORGENTE (sorgente di testata ORDINE_VENDITA o RESO_VENDITA; billing_account_id della sorgente, NULL compreso; etichetta NULL = dichiarata e non trovata o invisibile sotto RLS) e FULFILLMENT (la bolla evade gia'' righe d''ordine; etichetta = il primo ordine). Nessuna riga = cliente libero. Predicato condiviso: il guard vendite.trgfn_ddt_guard_cliente_sorgente solleva da qui, la capability script.fn_available_actions_ddt spegne billing_account_id da qui (prima lo spegneva sempre, anche sulla bolla senza sorgente che D-2 vuole poter ricevere il cliente in bozza). INVOKER e STABLE, come il guard: ordine, reso e fulfillment si leggono sotto la RLS di chi scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
