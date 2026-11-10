{% include-markdown "it/dbzero/dbops/manual/fn_accensione_a_mano_ammessa_su_valori.md" %}
# ⚙️ Funzione `fn_accensione_a_mano_ammessa_su_valori`

```sql
CREATE FUNCTION fn_accensione_a_mano_ammessa_su_valori(p_acceso_a_mano boolean, p_accendibile_in_produzione boolean, p_ambiente text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_accensione_a_mano_ammessa_su_valori(p_acceso_a_mano boolean, p_accendibile_in_produzione boolean, p_ambiente text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: la scelta a mano e' ammessa dal divieto di
    --   accensione in PRODUZIONE? NULL = non decidibile
    --   (ambiente non dichiarato). L'ordine dei rami e' la
    --   regola (vedi intestazione).
    SELECT CASE
             WHEN p_acceso_a_mano IS NOT TRUE             THEN true
             WHEN p_accendibile_in_produzione IS NOT FALSE THEN true
             WHEN p_ambiente = 'SVILUPPO'                 THEN true
             WHEN p_ambiente = 'PRODUZIONE'               THEN false
             ELSE NULL
           END;
$function$

COMMENT ON FUNCTION dbops.fn_accensione_a_mano_ammessa_su_valori(p_acceso_a_mano boolean, p_accendibile_in_produzione boolean, p_ambiente text)
IS 'Il divieto di accendere a mano in PRODUZIONE un processo non accendibile (dbops.processi.accendibile_in_produzione = false), puro sui valori: e'' l''unico posto dove e'' scritto. In ordine: una scelta che non accende (false, o NULL = torna al default) -> true; processo accendibile, o senza sveglia -> true; ambiente SVILUPPO -> true; PRODUZIONE -> false; ambiente non dichiarato -> NULL (non decidibile). Lo leggono il guard di dbops.processi_accensione (dbops.trgfn_processi_accensione_guard: rifiuta con E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE, e con NULL E_CONFIG_MANCANTE), la regola dbops.fn_processo_acceso_su_valori (ignora una riga accesa che il divieto non ammette) e il backend per la capability del drawer, con acceso = true. IMMUTABLE e LANGUAGE sql (si inlinea), senza STRICT. Sui valori perche'' l''ambiente dell''installazione non cambia e la CI e'' SVILUPPO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
