{% include-markdown "it/dbzero/vendite/manual/fn_resi_riga_residuo_riconsegna.md" %}
# ⚙️ Funzione `fn_resi_riga_residuo_riconsegna`

```sql
CREATE FUNCTION fn_resi_riga_residuo_riconsegna(p_resi_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resi_riga_residuo_riconsegna(p_resi_riga_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: residuo RI-CONSEGNABILE di una riga reso, cioe' quanta
--   merce resta da ri-spedire al cliente oppure da dichiarare
--   definitiva (rinuncia):
--     quantita - Sigma riconsegnate - Sigma rinunciate
--   Punto UNICO della formula (brief §4.2-bis): prima era ripetuta
--   in vw_resi_da_riconsegnare, fn_genera_ddt_riconsegna e
--   trgfn_resi_riconsegne_guard, che ora la consumano da qui.
-- NB: e' un'aritmetica di copertura sulla singola riga. NON filtra
--   stato reso / attivo / tipo: quei filtri di dominio restano ai
--   chiamanti (la vista li ha nella WHERE, il guard deve poter
--   valutare la copertura mentre la riga cambia).
-- Da non confondere con fn_ordine_riga_qta_riconsegna, che calcola
--   l'addendo del residuo ORDINE.
DECLARE
    v_quantita vendite.resi_righe.quantita%TYPE;
    v_ric      numeric;
    v_rin      numeric;
BEGIN
    IF p_resi_riga_id IS NULL OR p_resi_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_resi_riga_residuo_riconsegna','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','resi_riga_id','valore',p_resi_riga_id),
            NULL::uuid, 'resi_riga_id obbligatorio (>0)');
    END IF;

    SELECT rr.quantita INTO v_quantita
      FROM vendite.resi_righe rr
     WHERE rr.id = p_resi_riga_id;

    -- Riga inesistente: 0 residuo, non un errore. La funzione e'
    -- letta da viste che possono valutarla su insiemi in movimento;
    -- un raise qui le farebbe fallire per una riga cancellata.
    IF v_quantita IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(SUM(q.qta), 0) INTO v_ric
      FROM vendite.resi_righe_riconsegne q
     WHERE q.resi_riga_id = p_resi_riga_id;

    SELECT COALESCE(SUM(r.qta), 0) INTO v_rin
      FROM vendite.resi_righe_rinunce r
     WHERE r.resi_riga_id = p_resi_riga_id;

    -- GREATEST(0, ...): il residuo non e' mai negativo verso i
    -- consumatori. L'invariante quantita >= Sigma ric + Sigma rin
    -- e' presidiato dai due guard dei ponti; qui si evita solo che
    -- un'eventuale incoerenza si propaghi come numero negativo
    -- nelle viste.
    RETURN GREATEST(0::numeric, v_quantita - v_ric - v_rin);
END;
$function$

COMMENT ON FUNCTION vendite.fn_resi_riga_residuo_riconsegna(p_resi_riga_id bigint)
IS 'Residuo RI-CONSEGNABILE di una riga reso: quantita - Sigma resi_righe_riconsegne.qta - Sigma resi_righe_rinunce.qta (brief-db-chiusura-riconsegna-reso-definitivo S4.2-bis). PUNTO UNICO della formula, prima ripetuta in vw_resi_da_riconsegnare, fn_genera_ddt_riconsegna e trgfn_resi_riconsegne_guard: modificarla qui la allinea in tutti. Non filtra stato reso / attivo / tipo riapre_residuo: e'' aritmetica di copertura sulla singola riga, i filtri di dominio restano ai chiamanti. Ritorna 0 su riga inesistente (letta da viste su insiemi in movimento) e mai un valore negativo. DA NON CONFONDERE con fn_ordine_riga_qta_riconsegna, che calcola l''addendo del residuo ORDINE. rev 2026-07-26.';
```

</div>

---
{% include-markdown "signature-core.md" %}
