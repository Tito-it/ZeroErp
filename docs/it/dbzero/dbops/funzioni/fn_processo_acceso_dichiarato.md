# ⚙️ Funzione `fn_processo_acceso_dichiarato`

```sql
CREATE FUNCTION fn_processo_acceso_dichiarato(p_processo_codice text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_processo_acceso_dichiarato(p_processo_codice text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: la sveglia del processo e' accesa, su questa
    --   installazione? NULL = senza sveglia, inesistente, o
    --   ambiente non dichiarato. Non solleva: e' per chi
    --   descrive. La regola e' in fn_processo_acceso_su_valori.
    SELECT dbops.fn_processo_acceso_su_valori(
               p.canale,
               p.obsoleto_dal,
               p.spegnibile,
               p.acceso_in_sviluppo,
               p.acceso_in_produzione,
               a.acceso,
               script.fn_ambiente_dichiarato(),
               p.accendibile_in_produzione)
      FROM dbops.processi p
      LEFT JOIN dbops.processi_accensione a
        ON a.processo_id = p.id
     WHERE p.codice = p_processo_codice;
$function$

COMMENT ON FUNCTION dbops.fn_processo_acceso_dichiarato(p_processo_codice text)
IS 'Lo stato della sveglia di un processo su questa installazione: legge dbops.processi (default per ambiente, spegnibile, accendibile in produzione), dbops.processi_accensione (la scelta a mano) e script.fn_ambiente_dichiarato(), e chiede la regola a dbops.fn_processo_acceso_su_valori. Non solleva: NULL per un processo senza sveglia (CODA, ritirato), inesistente, o con l''ambiente non dichiarato. E'' la lettura di chi descrive (il panorama dbops.vw_processi_programmazione); chi decide usa maintenance.fn_sveglia_accesa, che rende quei NULL errori. RETURNS boolean nudo: e'' una risposta, non il riflesso di una colonna. Brief: brief-db-processi-accensione-per-ambiente (§5.3, R-BE-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
