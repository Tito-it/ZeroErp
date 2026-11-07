{% include-markdown "it/dbzero/vendite/manual/fn_commessa_viva_di_sorgente.md" %}
# ⚙️ Funzione `fn_commessa_viva_di_sorgente`

```sql
CREATE FUNCTION fn_commessa_viva_di_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_commessa_viva_di_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
    -- Aperta = lo stato non chiude la commessa: lo stesso predicato
    -- del riuso in vendite.fn_get_or_create_commessa.
    -- La regola d'incontro del modello: la colonna che il key_selector
    -- del tipo non usa e' NULL, quindi passare tutte e due le chiavi del
    -- documento trova il link senza leggere il key_selector.
    SELECT cs.commessa_id
      FROM vendite.commesse_sorgenti cs
      JOIN vendite.commesse c        ON c.id  = cs.commessa_id
      JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
     WHERE cs.sorgente_tipo_id = p_sorgente_tipo_id
       AND (cs.sorgente_id = p_sorgente_id OR cs.sorgente_uid = p_sorgente_uid)
       AND sc.chiude_commessa  = false
     ORDER BY cs.commessa_id DESC
     LIMIT 1
$function$

COMMENT ON FUNCTION vendite.fn_commessa_viva_di_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'Building block: la commessa APERTA in cui sta un documento, o NULL. Aperta = vendite.stati_commessa.chiude_commessa = false, lo stesso predicato con cui vendite.fn_get_or_create_commessa riusa una commessa: una commessa che il push non riusa non trattiene il documento. Il link documento -> commessa resta come storia dopo la chiusura e l''annullo, quindi un documento puo'' avere piu'' link: questa funzione dice quale conta. Il documento si passa con le colonne del modello (tipo, sorgente_id, sorgente_uid) e si cerca con la regola d''incontro (sorgente_id = p_sorgente_id OR sorgente_uid = p_sorgente_uid): chi ha il documento passa il suo id e il suo uid, chi ha la chiave del modello passa quella e NULL nell''altra. Lettori: vendite.fn_link_commessa_sorgente (un secondo invio e'' rifiutato solo se il documento sta in un''altra commessa aperta), vendite.trgfn_guard_fatturazione_immediata_immutabile (il flag si blocca solo con una commessa aperta), il backend. SECURITY INVOKER: le policy di commesse e commesse_sorgenti filtrano per emittente e una commessa ha l''emittente del documento (vendite.trgfn_commesse_sorgenti_guard_emittente), quindi chi vede il documento vede tutte le sue commesse. ORDER BY + LIMIT 1: la porta ne garantisce al piu'' una aperta; l''ordine rende la risposta deterministica. CHIUSA e ANNULLATA sono terminali nella matrice: se un giorno non lo fossero, la riapertura andrebbe controllata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
