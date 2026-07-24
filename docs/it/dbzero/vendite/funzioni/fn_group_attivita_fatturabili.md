{% include-markdown "it/dbzero/vendite/manual/fn_group_attivita_fatturabili.md" %}
# ⚙️ Funzione `fn_group_attivita_fatturabili`

```sql
CREATE FUNCTION fn_group_attivita_fatturabili(p_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_group_attivita_fatturabili(p_attivita_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_articolo_id    catalogo.articoli.id%TYPE;
    v_dest_ba_id     anagrafiche.billing_account.id%TYPE;
    v_uom_id         catalogo.unita_misura.id%TYPE;
    v_prezzo_unitario vendite.attivita_fatturabili.prezzo_unitario%TYPE;
    v_iva_id         config.iva.id%TYPE;
    v_regole         RECORD;
    v_comp_dal       vendite.attivita_fatturabili.competenza_dal%TYPE;
    v_comp_al        vendite.attivita_fatturabili.competenza_al%TYPE;
    v_data_attivita  vendite.attivita_fatturabili.data_attivita%TYPE;
    v_use_competenza BOOLEAN;
BEGIN
    IF p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_group_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_attivita_id', 'valore', p_attivita_id), NULL::uuid, 'p_attivita_id obbligatorio e > 0');
    END IF;

    SELECT a.articolo_id, a.billing_account_id, COALESCE(a.uom_id, art.uom_id),
           a.prezzo_unitario, art.iva_id, a.competenza_dal, a.competenza_al, a.data_attivita
      INTO v_articolo_id, v_dest_ba_id, v_uom_id, v_prezzo_unitario, v_iva_id, v_comp_dal, v_comp_al, v_data_attivita
      FROM vendite.attivita_fatturabili a
      JOIN catalogo.articoli art ON art.id = a.articolo_id
     WHERE a.id = p_attivita_id;

    IF v_articolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_group_attivita_fatturabili', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id), NULL::uuid, concat('attivita_id ', p_attivita_id));
    END IF;

    -- Regole articolo con FALLBACK ai default: LEFT JOIN da una riga-base
    -- cosi' si ottiene SEMPRE una riga (i default scattano quando manca la
    -- riga in articolo_regole_fatturazione; un SELECT diretto darebbe 0
    -- righe e la COALESCE non servirebbe a nulla). ALIAS espliciti: senza,
    -- i campi del record si chiamerebbero 'coalesce' e l'accesso
    -- v_regole.visibilita_componenti fallirebbe. (fix 2026-07-21)
    SELECT COALESCE(r.visibilita_componenti, 'solo_padre')       AS visibilita_componenti,
           COALESCE(r.calcolo_qta_padre, 'fissa')                AS calcolo_qta_padre,
           COALESCE(r.arrotondamento_importi_dec, 2)             AS arrotondamento_importi_dec,
           COALESCE(r.arrotondamento_quantita_dec, 3)            AS arrotondamento_quantita_dec,
           COALESCE(r.metodo_arrotondamento_importi, 'HALF_UP')  AS metodo_arrotondamento_importi,
           COALESCE(r.metodo_arrotondamento_quantita, 'HALF_UP') AS metodo_arrotondamento_quantita
      INTO v_regole
      FROM (SELECT 1) base
      LEFT JOIN vendite.articolo_regole_fatturazione r ON r.articolo_id = v_articolo_id;

    v_use_competenza := v_comp_dal IS NOT NULL AND v_comp_al IS NOT NULL
        AND (v_comp_dal <> v_comp_al OR v_comp_dal <> v_data_attivita);

    RETURN jsonb_build_object(
        'articolo_id', v_articolo_id, 'dest_billing_account_id', v_dest_ba_id,
        'uom_id', v_uom_id, 'prezzo_unitario', v_prezzo_unitario, 'iva_id', v_iva_id,
        'competenza_dal', CASE WHEN v_use_competenza THEN v_comp_dal ELSE NULL END,
        'competenza_al', CASE WHEN v_use_competenza THEN v_comp_al ELSE NULL END,
        'visibilita_componenti', v_regole.visibilita_componenti,
        'calcolo_qta_padre', v_regole.calcolo_qta_padre,
        'arrotondamento_importi_dec', v_regole.arrotondamento_importi_dec,
        'arrotondamento_quantita_dec', v_regole.arrotondamento_quantita_dec,
        'metodo_arrotondamento_importi', v_regole.metodo_arrotondamento_importi,
        'metodo_arrotondamento_quantita', v_regole.metodo_arrotondamento_quantita
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_group_attivita_fatturabili(p_attivita_id bigint)
IS 'Chiave aggregazione riga fattura da attivita_fatturabili con fallback regole articolo (LEFT JOIN: default se manca la riga articolo_regole_fatturazione). rev 2026-07-21: fix alias record v_regole + fallback no-row (il path fn_generate_fatture_righe era rotto per qualunque articolo).';
```

---
{% include-markdown "signature-core.md" %}
