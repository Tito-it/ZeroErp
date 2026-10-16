# ⚙️ Funzione `fn_processo_acceso_su_valori`

```sql
CREATE FUNCTION fn_processo_acceso_su_valori(p_canale text, p_obsoleto_dal date, p_spegnibile boolean, p_acceso_in_sviluppo boolean, p_acceso_in_produzione boolean, p_acceso_a_mano boolean, p_ambiente text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_processo_acceso_su_valori(p_canale text, p_obsoleto_dal date, p_spegnibile boolean, p_acceso_in_sviluppo boolean, p_acceso_in_produzione boolean, p_acceso_a_mano boolean, p_ambiente text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: la sveglia del processo e' accesa? NULL = senza
    --   sveglia, oppure non decidibile (ambiente non dichiarato).
    --   L'ordine dei rami e' la regola (vedi intestazione).
    SELECT CASE
             WHEN p_canale = 'CODA' OR p_obsoleto_dal IS NOT NULL THEN NULL
             WHEN p_spegnibile IS FALSE                          THEN true
             WHEN p_acceso_a_mano IS NOT NULL                    THEN p_acceso_a_mano
             WHEN p_ambiente = 'SVILUPPO'                        THEN p_acceso_in_sviluppo
             WHEN p_ambiente = 'PRODUZIONE'                      THEN p_acceso_in_produzione
             ELSE NULL
           END;
$function$

COMMENT ON FUNCTION dbops.fn_processo_acceso_su_valori(p_canale text, p_obsoleto_dal date, p_spegnibile boolean, p_acceso_in_sviluppo boolean, p_acceso_in_produzione boolean, p_acceso_a_mano boolean, p_ambiente text)
IS 'La regola dell''accensione della sveglia di un processo, pura sui valori: l''unico posto dove e'' scritta. In ordine: senza sveglia (CODA o ritirato) -> NULL; non spegnibile -> true sempre, senza leggere scelta a mano ne'' ambiente; scelta a mano presente -> la scelta; ambiente SVILUPPO o PRODUZIONE -> il default di quell''ambiente dal catalogo; ambiente non dichiarato -> NULL (non decidibile: chi decide lo rende E_CONFIG_MANCANTE). IMMUTABLE e LANGUAGE sql (si inlinea), senza STRICT (i NULL sono casi normali). Sui valori perche'' l''ambiente e'' immutabile e la CI e'' SVILUPPO: i pgTAP provano il ramo PRODUZIONE passando il valore. La leggono dbops.fn_processo_acceso_dichiarato e, attraverso di lei, maintenance.fn_sveglia_accesa e il panorama dbops.vw_processi_programmazione. Brief: brief-db-processi-accensione-per-ambiente (A-2, A-5, R-1).';
```

---
{% include-markdown "signature-core.md" %}
