{% include-markdown "it/dbzero/script/manual/fn_check_versione_listino_attivabile.md" %}
# ⚙️ Funzione `fn_check_versione_listino_attivabile`

```sql
CREATE FUNCTION fn_check_versione_listino_attivabile(p_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_versione_listino_attivabile(p_versione_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_versione vendite.listini_versioni%ROWTYPE;
    v_riga_id  vendite.listini_righe.id%TYPE;
    v_articolo catalogo.articoli%ROWTYPE;
BEGIN
    -- =========================================================
    -- Scopo: dire perche' una versione di listino NON si attiva.
    --   '[]' = si attiva. Non solleva: sollevare e' del guard di
    --   transizione e del verbo, che la chiamano, come la
    --   superficie della lista (linee-guida-sql §12.5.2).
    -- =========================================================
    SELECT lv.* INTO v_versione
      FROM vendite.listini_versioni lv
     WHERE lv.id = p_versione_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_array();
    END IF;

    -- 1. La versione e' spenta.
    IF v_versione.attivo IS NOT TRUE THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_SPENTA',
            'reason',     'VERSIONE_SPENTA',
            'reason_key', 'vendite.listini.azione_reason.versione_spenta',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id),
            'valori',     jsonb_build_array(v_versione.codice_versione)));
    END IF;

    -- 2. La versione non ha prezzi: ne' una riga attiva, ne' un
    --    composito col prezzo bundle.
    SELECT r.id INTO v_riga_id
      FROM vendite.listini_righe r
     WHERE r.listino_versione_id = v_versione.id
       AND r.attivo IS TRUE
     LIMIT 1;
    IF NOT FOUND THEN
        SELECT c.id INTO v_riga_id
          FROM vendite.listini_righe_componenti c
         WHERE c.listino_versione_id = v_versione.id
           AND c.attivo IS TRUE
         LIMIT 1;
    END IF;
    IF NOT FOUND THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_SENZA_RIGHE',
            'reason',     'VERSIONE_SENZA_RIGHE',
            'reason_key', 'vendite.listini.azione_reason.versione_senza_righe',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id),
            'valori',     jsonb_build_array(v_versione.codice_versione)));
    END IF;

    -- 3. rev 2026-10-31 (20261031-39, D-3): una quota fissa a canone senza
    --    periodicita', riga di listino o kit (la sede la dice per tutti e due).
    SELECT a.* INTO v_articolo
      FROM (SELECT r.articolo_id
              FROM vendite.listini_righe r
             WHERE r.listino_versione_id = v_versione.id
               AND r.attivo IS TRUE
            UNION
            SELECT c.articolo_padre_id
              FROM vendite.listini_righe_componenti c
             WHERE c.listino_versione_id = v_versione.id
               AND c.attivo IS TRUE) x
      JOIN catalogo.articoli a ON a.id = x.articolo_id
     -- rev 2026-10-31 (20261031-50): «quota fissa a canone» dalla sede.
     WHERE vendite.fn_articolo_quota_fissa_a_canone(a.id)
       AND vendite.fn_listino_periodicita_articolo(v_versione.id, a.id) IS NULL
     ORDER BY a.codice
     LIMIT 1;
    IF FOUND THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA',
            'reason',     'QUOTA_FISSA_SENZA_PERIODICITA',
            'reason_key', 'vendite.listini.azione_reason.quota_fissa_senza_periodicita',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id,
                                             'articolo_id', v_articolo.id,
                                             'campo', 'periodicita'),
            'valori',     jsonb_build_array(v_versione.codice_versione, v_articolo.codice)));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_versione_listino_attivabile(p_versione_id bigint)
IS 'Perche'' una versione di listino NON si attiva: jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si attiva. Motivi: 1. E_LISTINO_VERSIONE_SPENTA (attivo = false); 2. E_LISTINO_VERSIONE_SENZA_RIGHE (nessuna riga attiva e nessun composito con prezzo bundle). Lo stato non e'' un motivo: lo giudica la matrice. Versione inesistente o fuori perimetro: ''[]''. Non solleva. La chiamano il guard vendite.trgfn_listini_versioni_guard_transizione_stato (-> ATTIVA), il verbo vendite.fn_attiva_versione_listino (prima di chiudere le precedenti) e la superficie vendite.vw_listini_versioni_azioni (registro config.azioni_riga). Prima la regola stava solo nel backend (listini_service._plan_versione_state_change). SECURITY INVOKER, STABLE. Brief: brief-modello-documento-vendita §16 (L-4, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
