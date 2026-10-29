{% include-markdown "it/dbzero/script/manual/fn_check_versione_listino_clonabile.md" %}
# ⚙️ Funzione `fn_check_versione_listino_clonabile`

```sql
CREATE FUNCTION fn_check_versione_listino_clonabile(p_sorgente_id bigint, p_valido_dal date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_versione_listino_clonabile(p_sorgente_id bigint, p_valido_dal date DEFAULT NULL::date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_sorgente vendite.listini_versioni%ROWTYPE;
BEGIN
    -- =========================================================
    -- Scopo: dire perche' una versione di listino NON si clona
    --   in una versione che decorre da p_valido_dal. '[]' = si
    --   clona. Non solleva: sollevare e' del verbo, che la
    --   chiama (linee-guida-sql §12.5.2).
    --   Vedi l'intestazione del changeSet 20261029-03.
    -- =========================================================
    SELECT lv.* INTO v_sorgente
      FROM vendite.listini_versioni lv
     WHERE lv.id = p_sorgente_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_array();
    END IF;

    -- 1. D2: la copia non comincia prima della sorgente.
    IF p_valido_dal < v_sorgente.valido_dal THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE',
            'reason',     'CLONE_PRIMA_DELLA_SORGENTE',
            'reason_key', 'vendite.listini.azione_reason.clone_prima_della_sorgente',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_sorgente.id,
                                             'listino_id', v_sorgente.listino_id,
                                             'valido_dal', p_valido_dal,
                                             'valido_dal_sorgente', v_sorgente.valido_dal),
            'valori',     jsonb_build_array(to_char(p_valido_dal, 'DD/MM/YYYY'),
                                            v_sorgente.codice_versione,
                                            to_char(v_sorgente.valido_dal, 'DD/MM/YYYY'))));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_versione_listino_clonabile(p_sorgente_id bigint, p_valido_dal date)
IS 'Perche'' una versione di listino NON si clona in una versione che decorre da p_valido_dal: jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si clona. Motivo: E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE (CLONE_PRIMA_DELLA_SORGENTE: p_valido_dal precede la decorrenza della sorgente; decisione D2 di sviluppo-listini-v2; una decorrenza passata e'' ammessa). Nessun motivo di stato: si clona da qualunque stato, anche da una BOZZA (C-1 = a, come O1); per questo «Clona» non ha superficie ne'' riga in config.azioni_riga. p_valido_dal NULL o versione inesistente o fuori perimetro: ''[]''. Non solleva. La chiama il verbo vendite.fn_clona_versione_listino. Prima la regola stava nel backend (listini_service.fn_clone_versione, E_VENDITE_VALIDATION). SECURITY INVOKER, STABLE. Brief: brief-modello-documento-vendita §16.14 (C-1 = a, Tid 2026-10-29).';
```

</div>

---
{% include-markdown "signature-core.md" %}
