{% include-markdown "it/dbzero/script/manual/fn_check_legame_distinta_chiudibile.md" %}
# ⚙️ Funzione `fn_check_legame_distinta_chiudibile`

```sql
CREATE FUNCTION fn_check_legame_distinta_chiudibile(p_legame_id uuid, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_legame_distinta_chiudibile(p_legame_id uuid, p_valido_al date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_kit        catalogo.articoli.codice%TYPE;
    v_componente catalogo.articoli.codice%TYPE;
    -- Conteggio di righe: nessuna colonna dietro.
    v_altre      integer;
    v_prima_fine vendite.listini_righe_componenti.valido_dal%TYPE;
    v_motivi     jsonb := jsonb_build_array();
BEGIN
    -- =========================================================
    -- Scopo: dire perche' il legame p_legame_id NON si chiude
    --   alla data p_valido_al per i suoi prezzi bundle. '[]' =
    --   si chiude. Non solleva: sollevare e' del guard e del
    --   verbo, che la chiamano. Vedi l'intestazione del changeSet.
    -- =========================================================
    IF p_legame_id IS NULL OR p_valido_al IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT p.codice, c.codice
      INTO v_kit, v_componente
      FROM catalogo.articoli_componenti ac
      JOIN catalogo.articoli p ON p.id = ac.prodotto_id
      JOIN catalogo.articoli c ON c.id = ac.componente_id
     WHERE ac.id = p_legame_id;
    IF NOT FOUND THEN
        RETURN v_motivi;
    END IF;

    SELECT count(*) FILTER (WHERE NOT r.nel_perimetro),
           max(r.valido_dal) FILTER (WHERE r.nel_perimetro AND r.esito = 'BLOCCA')
      INTO v_altre, v_prima_fine
      FROM vendite.fn_prezzi_legame_oltre_la_fine(p_legame_id, p_valido_al) r;

    -- 1. Prezzi in listini che chi chiude non vede.
    IF v_altre > 0 THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE',
            'reason',     'PREZZI_ALTRE_AZIENDE',
            'reason_key', 'catalogo.distinta.azione_reason.prezzi_altre_aziende',
            'dettaglio',  jsonb_build_object('legame_id', p_legame_id,
                                             'valido_al', p_valido_al,
                                             'prezzi',    v_altre),
            'valori',     jsonb_build_array(v_componente, v_kit, v_altre::text)));
    END IF;

    -- 2. Prezzi di una versione non in bozza che cominciano dopo la fine.
    IF v_prima_fine IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_BOM_CHIUSURA_PRIMA_DEI_PREZZI',
            'reason',     'PREZZI_DOPO_LA_FINE',
            'reason_key', 'catalogo.distinta.azione_reason.prezzi_dopo_la_fine',
            'dettaglio',  jsonb_build_object('legame_id',     p_legame_id,
                                             'valido_al',     p_valido_al,
                                             'valido_al_min', v_prima_fine),
            'valori',     jsonb_build_array(v_componente, v_kit,
                                            to_char(v_prima_fine, 'DD/MM/YYYY'))));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_legame_distinta_chiudibile(p_legame_id uuid, p_valido_al date)
IS 'Perche'' il legame di distinta p_legame_id (catalogo.articoli_componenti) NON si chiude alla data p_valido_al per i suoi prezzi bundle: array di motivi {codice, reason, reason_key, dettaglio, valori}; ''[]'' = si chiude. Le righe le da'' vendite.fn_prezzi_legame_oltre_la_fine. Motivi, nell''ordine: E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE (prezzi in listini fuori dal perimetro di chi chiude: la distinta e'' comune a tutte le aziende, i listini no; valori componente, kit, numero di prezzi); E_BOM_CHIUSURA_PRIMA_DEI_PREZZI (prezzi di una versione non in bozza che cominciano dopo la fine: non si accorciano e non si cancellano; valori componente, kit, prima fine ammessa, cioe'' l''inizio piu'' tardo; dettaglio.valido_al_min). Legame assente o p_valido_al NULL: ''[]''. Non solleva: il primo motivo lo sollevano catalogo.trgfn_articoli_componenti_block_modifica_struttura e catalogo.fn_chiudi_legame_distinta, sul campo valido_al. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
