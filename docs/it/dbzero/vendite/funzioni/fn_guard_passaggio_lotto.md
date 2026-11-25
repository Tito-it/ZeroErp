{% include-markdown "it/dbzero/vendite/manual/fn_guard_passaggio_lotto.md" %}
# ⚙️ Funzione `fn_guard_passaggio_lotto`

```sql
CREATE FUNCTION fn_guard_passaggio_lotto(p_auth_user_id integer, p_stato_da_id bigint, p_stato_a_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_guard_passaggio_lotto(p_auth_user_id integer, p_stato_da_id bigint, p_stato_a_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: il permesso del passaggio di stato fiscale di un lotto, nella
--   forma che l'endpoint controlla (risposta 3d, PassaggioDocumento.azione):
--   l'azione della riga del passaggio, se la riga c'e' e ne dichiara una;
--   altrimenti (riga senza azione, o nessuna riga: il lotto gia' nello
--   stato d'arrivo) il livello TUTTO sull'area vendite, «il permesso sul
--   documento» della guida del modello.
-- Uso, nella prima riga del verbo, dopo aver letto il lotto nel perimetro:
--   PERFORM vendite.fn_guard_passaggio_lotto(v_utente, v_stato_da_id, v_stato_a_id);
-- ⚠️ Non giudica la matrice ne' il passaggio di processo: lo fa
--   script.fn_guard_passaggio dentro vendite.fn_cambia_stato_lotto, e il
--   guard di transizione all'UPDATE. Qui c'e' solo il permesso.
-- ⚠️ La ricaduta sull'area vale per il lotto (D-X a di
--   brief-db-porte-aperte-dalla-sola-guc, 2026-11-25): fn_guard_passaggio,
--   comune a tutti i documenti, non la fa.
DECLARE
    v_azione config.azioni_processo.permission_codename%TYPE;
BEGIN
    SELECT p.azione_processo_codename
      INTO v_azione
      FROM script.fn_doc_passaggio('vendite.fatturazione_lotti'::regclass,
                                   p_stato_da_id, p_stato_a_id) p;

    IF v_azione IS NOT NULL THEN
        PERFORM script.fn_guard_azione(p_auth_user_id, v_azione);
    ELSE
        PERFORM script.fn_guard_livello_area(p_auth_user_id, 'vendite', 'TUTTO');
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_guard_passaggio_lotto(p_auth_user_id integer, p_stato_da_id bigint, p_stato_a_id bigint)
IS 'Il permesso di un passaggio di stato fiscale del lotto, come lo controlla l''endpoint: l''azione della riga del passaggio (script.fn_doc_passaggio) se c''e'' (script.fn_guard_azione), altrimenti, riga senza azione o nessuna riga, il livello TUTTO sull''area vendite (script.fn_guard_livello_area). Rifiuto: E_PERMESSO_NEGATO. Non giudica la matrice: lo fanno fn_guard_passaggio e il guard di transizione. La chiamano vendite.fn_annulla_lotto_da_draft e vendite.fn_riporta_lotto_a_draft, verbi DEFINER, dopo aver letto il lotto nel perimetro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
