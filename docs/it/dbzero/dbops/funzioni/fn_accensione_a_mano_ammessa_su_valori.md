# ⚙️ Funzione `fn_accensione_a_mano_ammessa_su_valori`

```sql
CREATE FUNCTION fn_accensione_a_mano_ammessa_su_valori(p_acceso_a_mano boolean, p_accendibile_in_produzione boolean, p_ambiente text)
```

**Definizione completa:**

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
IS 'Il divieto di accendere a mano in PRODUZIONE un processo non accendibile (dbops.processi.accendibile_in_produzione = false), puro sui valori: l''unico posto dove e'' scritto. In ordine: una scelta che non accende (false, o NULL = torna al default) -> true; processo accendibile, o senza sveglia -> true; ambiente SVILUPPO -> true; PRODUZIONE -> false; ambiente non dichiarato -> NULL (non decidibile). Lo leggono il guard di dbops.processi_accensione (rifiuta con E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE; NULL -> E_CONFIG_MANCANTE), la regola dbops.fn_processo_acceso_su_valori (ignora una riga accesa che il divieto non ammette) e il backend per la capability del drawer, con acceso = true. IMMUTABLE e LANGUAGE sql (si inlinea), senza STRICT. Sui valori perche'' l''ambiente e'' immutabile e la CI e'' SVILUPPO. Brief: brief-db-processi-accensione-per-ambiente (R-BE-5).';
```

---
{% include-markdown "signature-core.md" %}
