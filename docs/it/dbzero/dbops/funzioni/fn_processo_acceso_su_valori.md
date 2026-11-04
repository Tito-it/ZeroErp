{% include-markdown "it/dbzero/dbops/manual/fn_processo_acceso_su_valori.md" %}
# ⚙️ Funzione `fn_processo_acceso_su_valori`

```sql
CREATE FUNCTION fn_processo_acceso_su_valori(p_canale text, p_obsoleto_dal date, p_spegnibile boolean, p_acceso_in_sviluppo boolean, p_acceso_in_produzione boolean, p_acceso_a_mano boolean, p_ambiente text, p_accendibile_in_produzione boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_processo_acceso_su_valori(p_canale text, p_obsoleto_dal date, p_spegnibile boolean, p_acceso_in_sviluppo boolean, p_acceso_in_produzione boolean, p_acceso_a_mano boolean, p_ambiente text, p_accendibile_in_produzione boolean)
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
             -- La scelta a mano decide solo se il divieto di
             -- accensione in PRODUZIONE la ammette: una riga
             -- accesa scritta prima della regola si ignora.
             WHEN p_acceso_a_mano IS NOT NULL
              AND dbops.fn_accensione_a_mano_ammessa_su_valori(
                      p_acceso_a_mano,
                      p_accendibile_in_produzione,
                      p_ambiente)                            THEN p_acceso_a_mano
             WHEN p_ambiente = 'SVILUPPO'                        THEN p_acceso_in_sviluppo
             WHEN p_ambiente = 'PRODUZIONE'                      THEN p_acceso_in_produzione
             ELSE NULL
           END;
$function$

COMMENT ON FUNCTION dbops.fn_processo_acceso_su_valori(p_canale text, p_obsoleto_dal date, p_spegnibile boolean, p_acceso_in_sviluppo boolean, p_acceso_in_produzione boolean, p_acceso_a_mano boolean, p_ambiente text, p_accendibile_in_produzione boolean)
IS 'La regola dell''accensione della sveglia di un processo, pura sui valori: l''unico posto dove e'' scritta. In ordine: senza sveglia (CODA o ritirato) -> NULL; non spegnibile -> true sempre, senza leggere scelta a mano ne'' ambiente; scelta a mano presente e ammessa dal divieto di accensione in PRODUZIONE (dbops.fn_accensione_a_mano_ammessa_su_valori) -> la scelta, altrimenti la riga si ignora; ambiente SVILUPPO o PRODUZIONE -> il default di quell''ambiente dal catalogo; ambiente non dichiarato -> NULL (non decidibile: chi decide lo rende E_CONFIG_MANCANTE). IMMUTABLE e LANGUAGE sql (si inlinea), senza STRICT (i NULL sono casi normali). Sui valori perche'' l''ambiente e'' immutabile e la CI e'' SVILUPPO: i pgTAP provano il ramo PRODUZIONE passando il valore. La leggono dbops.fn_processo_acceso_dichiarato e, attraverso di lei, maintenance.fn_sveglia_accesa e il panorama dbops.vw_processi_programmazione. Brief: brief-db-processi-accensione-per-ambiente (A-2, A-5, R-1, R-BE-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
