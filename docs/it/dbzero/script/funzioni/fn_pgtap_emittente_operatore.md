{% include-markdown "it/dbzero/script/manual/fn_pgtap_emittente_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_emittente_operatore`

```sql
CREATE FUNCTION fn_pgtap_emittente_operatore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_pgtap_emittente_operatore()
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dare a una fixture pgTAP l'emittente su cui l'operatore
--   corrente puo' davvero scrivere, invece di uno qualsiasi.
-- Uso, al posto di
--   (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo LIMIT 1):
--   script.fn_pgtap_emittente_operatore()
-- ⭐ Una sede sola: la risposta e' quella di
--   dbops.fn_pgtap_azienda_di_chi_agisce, cioe' la regola di produzione
--   (script.fn_resolve_emittente_for_user). Senza contesto, senza
--   un'azienda o senza un'identita' OPERATORE solleva: un emittente
--   scelto al posto di chi agisce e' un'azienda su cui chi agisce non
--   puo' ne' leggere ne' scrivere.
DECLARE
    v_emittente anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    SELECT a.emittente_fiscale_id
      INTO v_emittente
      FROM dbops.fn_pgtap_azienda_di_chi_agisce('script.fn_pgtap_emittente_operatore') a;

    RETURN v_emittente;
END;
$function$

COMMENT ON FUNCTION script.fn_pgtap_emittente_operatore()
IS 'Fixture pgTAP: l''emittente fiscale su cui l''operatore del contesto puo'' scrivere. Delega a dbops.fn_pgtap_azienda_di_chi_agisce, che lo risolve con la regola di produzione (script.fn_resolve_emittente_for_user: l''emittente scelto in alto, app.current_emittente_id, se l''utente lo puo'' usare, altrimenti la sua riga in config.user_emittenti_fiscali): una sede sola per la domanda. Senza contesto aperto, senza un''azienda per l''utente o senza un''identita'' OPERATORE attiva solleva, nominando questa funzione: non sceglie un emittente al posto di chi agisce. STABLE: non scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
