{% include-markdown "it/dbzero/script/manual/fn_check_sorgente_chiudibile.md" %}
# ⚙️ Funzione `fn_check_sorgente_chiudibile`

```sql
CREATE FUNCTION fn_check_sorgente_chiudibile(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_sorgente_chiudibile(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi  jsonb := '[]'::jsonb;
    v_emesse  integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di CHIUDERE (annullare)
    --   un documento che ha spinto righe in commessa.
    --   Funzione PURA: nessuna scrittura, nessun raise di
    --   dominio. Chi ferma solleva il primo motivo.
    --
    -- ⛔ LA CHIAVE e' quella del modello: tipo + sorgente_id o
    --   sorgente_uid, con la regola d'incontro. Chi ha il
    --   documento passa il suo id e il suo uid. Sbagliarla non
    --   produce un errore: produce ZERO motivi.
    -- =========================================================
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_sorgente_chiudibile',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_sorgente_tipo_id',
                               'valore',    p_sorgente_tipo_id),
            NULL::uuid, 'p_sorgente_tipo_id');
    END IF;

    -- Una chiave almeno; un id, se c'e', positivo.
    IF (p_sorgente_id IS NULL AND p_sorgente_uid IS NULL)
       OR p_sorgente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_sorgente_chiudibile',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_sorgente_id',
                               'valore',    p_sorgente_id,
                               'sorgente_uid', p_sorgente_uid),
            NULL::uuid, 'p_sorgente_id / p_sorgente_uid');
    END IF;

    -- ── MOTIVO 1 — righe gia' EMESSA ─────────────────────────
    -- ⛔ Sono in volo verso una fattura: non si ritirano, e
    --    finche' ci sono la testata non si chiude.
    -- ⭐ Da L5 il rifiuto ha una via d'uscita, e il messaggio la
    --    nomina: «Riporta da emettere» le riporta a NON_EMESSA,
    --    e da li' il ritiro le prende. Prima era un vicolo cieco.
    -- ℹ️ Le ANNULLATA non si contano (sono uscite di proposito) e
    --    nemmeno le NON_EMESSA: quelle sono proprio cio' che il
    --    ritiro portera' via.
    SELECT count(*)
      INTO v_emesse
      FROM vendite.commesse_attivita ca
     WHERE ca.sorgente_tipo_id = p_sorgente_tipo_id
       AND (ca.sorgente_id = p_sorgente_id OR ca.sorgente_uid = p_sorgente_uid)
       AND ca.stato_emissione  = 'EMESSA';

    IF v_emesse > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_SORGENTE_CON_RIGHE_EMESSE',
            'reason',     'RIGHE_COMMESSA_EMESSE',
            'reason_key', 'vendite.sorgenti.azione_reason.righe_commessa_emesse',
            'dettaglio',  v_emesse::text,
            'quante',     v_emesse,
            -- ⭐ «Il documento ha %s righe di commessa gia' emesse»: ci va il
            --   CONTEGGIO. Fino al 2026-09-09 questo motivo viaggiava anche
            --   dentro fn_check_ordine_annullabile, che lo concatena, e li' la
            --   madre passava per primo il NUMERO dell'ordine: a video usciva
            --   «Il documento ha ORD-... righe». Il guard della chiusura
            --   sorgente invece passava il dettaglio, ed era corretto — due
            --   chiamanti, una frase sola, due esiti diversi.
            'valori',     jsonb_build_array(v_emesse));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_sorgente_chiudibile(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'Elenca i motivi che impediscono di chiudere (annullare) un documento che ha spinto righe in commessa. Funzione pura: nessuna scrittura e nessun raise di dominio; chi ferma solleva il primo motivo, chi disegna l''interfaccia li mostra tutti. Il motivo e'' uno: righe di commessa gia'' EMESSA (E_SORGENTE_CON_RIGHE_EMESSE, con il conteggio nei valori). Non si ritirano, sono in volo verso una fattura; la via d''uscita e'' «Riporta da emettere», che le riporta a NON_EMESSA e da li'' il ritiro (vendite.fn_ritira_commessa_attivita_da_sorgente) le prende. Una primitiva per tutti i tipi: il documento si passa con le colonne del modello (tipo, sorgente_id, sorgente_uid) e si cerca con la regola d''incontro; chi ha il documento passa il suo id e il suo uid. Una chiave sbagliata non solleva: produce zero motivi. Non conta le righe ANNULLATA ne'' le NON_EMESSA (sono quelle che il ritiro porta via), ne'' le righe senza documento (ONERE, RETTIFICA). Chiamanti: script.fn_check_ordine_annullabile, script.fn_check_preventivo_annullabile, vendite.trgfn_doc_guard_chiusura_sorgente, vendite.fn_documento_ritira_legami. Solleva E_RITIRO_SORGENTE_PARAMETRO_MANCANTE su tipo o chiave mancanti o <= 0.';
```

</div>

---
{% include-markdown "signature-core.md" %}
