{% include-markdown "it/dbzero/script/manual/fn_esigibilita_iva.md" %}
# ⚙️ Funzione `fn_esigibilita_iva`

```sql
CREATE FUNCTION fn_esigibilita_iva(p_iva_per_cassa boolean, p_cliente_split_payment character, p_cliente_partita_iva text, p_iva_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_esigibilita_iva(p_iva_per_cassa boolean, p_cliente_split_payment character, p_cliente_partita_iva text, p_iva_id integer)
 RETURNS TABLE(esigibilita character, split_payment boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la coppia (esigibilita, split_payment) di una riga IVA.
--   Regola completa e ordine delle domande nel COMMENT.
--   rev 2026-10-01 (D-12, 20261001-40): 'D' solo con imposta.
DECLARE
    v_con_imposta  boolean;
BEGIN
    -- 1. Cliente non noto: la scissione non e' stata determinata, e
    --    «immediata, non scissa» sarebbe un'affermazione (D32).
    IF p_cliente_split_payment IS NULL THEN
        esigibilita := NULL; split_payment := NULL;
        RETURN NEXT; RETURN;
    END IF;

    split_payment := (p_cliente_split_payment = 'S');

    -- 2. La scissione dei pagamenti prevale su tutto: 'S' e' imposta.
    IF split_payment THEN
        esigibilita := 'S';
        RETURN NEXT; RETURN;
    END IF;

    -- 3-4. Il regime dell'emittente.
    IF p_iva_per_cassa IS NULL THEN
        esigibilita := NULL;
        RETURN NEXT; RETURN;
    END IF;

    IF NOT p_iva_per_cassa THEN
        esigibilita := 'I';
        RETURN NEXT; RETURN;
    END IF;

    -- 5. Per cassa, ma verso chi non e' soggetto passivo IVA (D-2:
    --    la partita IVA del cliente). ⚠️ btrim: una stringa vuota
    --    non e' una partita IVA.
    IF NULLIF(btrim(p_cliente_partita_iva), '') IS NULL THEN
        esigibilita := 'I';
        RETURN NEXT; RETURN;
    END IF;

    -- 6. Senza codice IVA non si sa se la riga ha un'imposta (in
    --    bozza e' legittimo, D3).
    IF p_iva_id IS NULL THEN
        esigibilita := NULL;
        RETURN NEXT; RETURN;
    END IF;

    -- 7. D-12: c'e' imposta solo su un codice SENZA Natura e con
    --    aliquota maggiore di zero. Ogni Natura, dalla N1 alla N7
    --    (inversione contabile compresa), va a 'I'. Il NOT FOUND
    --    resta per il codice che non esiste.
    SELECT (i.natura_iva_id IS NULL AND i.aliquota_iva > 0)
      INTO v_con_imposta
      FROM config.iva i
     WHERE i.id = p_iva_id;

    IF NOT FOUND THEN
        esigibilita := NULL;
        RETURN NEXT; RETURN;
    END IF;

    -- 8. Con imposta: differita all'incasso.
    esigibilita := CASE WHEN v_con_imposta THEN 'D' ELSE 'I' END;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_esigibilita_iva(p_iva_per_cassa boolean, p_cliente_split_payment character, p_cliente_partita_iva text, p_iva_id integer)
IS 'La regola UNICA di esigibilita'' IVA (I immediata, D differita, S scissione) e del flag split_payment di una riga, sui VALORI: il regime dell''emittente come attributo (config.regimi_fiscali.iva_per_cassa, D-10), la scissione e la partita IVA del cliente (D-2), il codice IVA della riga. ''D'' SOLO su una riga con imposta (codice senza Natura e aliquota > 0) di un emittente per cassa, verso un cliente soggetto passivo IVA, fuori dalla scissione; ogni Natura N1-N7, inversione contabile compresa, va a ''I'' (D-12, rev 20261001-40). Ordine: cliente non noto -> NULL/NULL; scissione -> S/true; regime non noto -> NULL; regime ordinario -> I; per cassa verso un cliente senza partita IVA -> I; per cassa senza codice IVA -> NULL; per cassa con Natura o aliquota zero -> I; per cassa con imposta -> D. ⭐ Derivazione PURA (D-7): chi la usa riscrive sempre il valore. Le parti le risolvono i chiamanti: vendite.fn_esigibilita_iva_fattura (trigger di riga e ricalcolo del riepilogo), vendite.fn_resolve_iva_riga_it, script.fn_esigibilita_iva_documento (riepiloghi di preventivi, ordini, DDT). STABLE: legge il solo codice IVA. Brief: brief-db-esigibilita-iva-per-cassa-emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
