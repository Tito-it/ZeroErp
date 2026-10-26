{% include-markdown "it/dbzero/script/manual/fn_check_contratto_sovrapposto.md" %}
# ⚙️ Funzione `fn_check_contratto_sovrapposto`

```sql
CREATE FUNCTION fn_check_contratto_sovrapposto(p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_contratto_sovrapposto(p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- ⚠️ Il jsonb di ritorno e' l'array dei motivi: nessuna colonna
--   di cui sia il riflesso.
DECLARE
    v_id     vendite.contratti.id%TYPE;
    v_numero vendite.contratti.numero%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il periodo del contratto si sovrappone a un contratto
    --   VINCOLANTE (non in bozza, non abortito) dello stesso
    --   cliente, punto di fornitura, utility e ambito? Funzione
    --   PURA: non solleva, non scrive. Sollevare e' mestiere del
    --   guard di transizione, che la CHIAMA, come la capability
    --   che spegne «Attiva» (linee-guida-sql §12.5.2).
    -- Ritorna: [] se il periodo e' libero, altrimenti UN motivo
    --   che nomina il contratto in conflitto.
    -- =========================================================
    v_id := vendite.fn_contratto_sovrapposto(
        p_billing_account_id,
        p_istanza_utility_id,
        p_utility_id,
        p_ambito,
        p_valido_dal,
        p_valido_al);

    IF v_id IS NULL THEN
        RETURN jsonb_build_array();
    END IF;

    SELECT c.numero
      INTO v_numero
      FROM vendite.contratti c
     WHERE c.id = v_id;

    RETURN jsonb_build_array(jsonb_build_object(
        'codice',     'E_CONTRATTO_OVERLAP_ESISTENTE',
        'reason',     'CONTRATTO_SOVRAPPOSTO',
        'reason_key', 'vendite.contratti.azione_reason.contratto_sovrapposto',
        'dettaglio',  jsonb_build_object(
                          'contratto_sovrapposto_id',     v_id,
                          'contratto_sovrapposto_numero', v_numero),
        -- Il %s del messaggio e il {0} del tooltip.
        'valori',     jsonb_build_array(v_numero)));
END;
$function$

COMMENT ON FUNCTION script.fn_check_contratto_sovrapposto(p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date)
IS 'Motivo d''attivazione del contratto (richiesta BE del 2026-10-19): il periodo si sovrappone a un contratto VINCOLANTE (partecipa_overlap_snapshot: non in bozza e non abortito, quindi ATTIVO o CESSATO) sulla stessa quintupla dell''EXCLUDE ex_contratti_no_overlap (billing_account, istanza_utility, utility, ambito, periodo). PURA: non solleva, non scrive. Ritorna [] o un motivo {codice E_CONTRATTO_OVERLAP_ESISTENTE, reason CONTRATTO_SOVRAPPOSTO, reason_key vendite.contratti.azione_reason.contratto_sovrapposto, dettaglio {contratto_sovrapposto_id, contratto_sovrapposto_numero}, valori [numero]}. Predicato vendite.fn_contratto_sovrapposto. La quintupla entra come PARAMETRI: il guard BEFORE UPDATE passa NEW.*, la capability i valori salvati. Si chiama per un contratto che non partecipa ancora (verso ATTIVO solo da DRAFT): nessun id da escludere. INVOKER sotto la RLS degli emittenti: un vincolante fuori perimetro non da'' motivo e resta il 23P01 dell''EXCLUDE (D-2 di Tid). Lettori: script.fn_available_actions_contratto e vendite.trgfn_contratti_guard_transizione_stato (verso ATTIVO). ⚠️ La reason_key e'' un debito verso il frontend (locales).';
```

</div>

---
{% include-markdown "signature-core.md" %}
