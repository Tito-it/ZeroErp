{% include-markdown "it/dbzero/magazzino/manual/fn_documento_interno_transizioni.md" %}
# ⚙️ Funzione `fn_documento_interno_transizioni`

```sql
CREATE FUNCTION fn_documento_interno_transizioni(p_stato_da text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_documento_interno_transizioni(p_stato_da text)
 RETURNS text[]
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- Scopo: la matrice degli stati dei documenti interni di magazzino
--   (inventari e rettifiche: la stessa per le due famiglie, D-L2-h) —
--   quali destinazioni sono ammesse a partire da uno stato.
-- Consumatori, e sono il motivo per cui esiste:
--   magazzino.trgfn_documento_interno_guard_transizione, che la fa
--   rispettare, e script.fn_available_actions_inventario / _rettifica,
--   che ne disegnano i pulsanti. Una regola, una sede: se divergessero,
--   l'operatore vedrebbe un bottone su un'azione che verra' rifiutata
--   (linee-guida-sql §12.1, «la terza via»).
-- Ritorna: le destinazioni ammesse; {} su uno stato terminale (POSTED,
--   CANCEL) e su uno stato che non esiste — chi chiama non deve
--   distinguere i due casi, perche' il cancello sui valori e' il CHECK
--   di tabella, non questa funzione.
-- ⚠️ POSTED e' nella matrice ed e' una transizione ammessa, ma NON e'
--   un'azione che si possa chiedere: la porta la apre solo l'operazione
--   (fn_posta_inventario / fn_posta_rettifica) firmandosi con la GUC
--   transazionale. Chi disegna i pulsanti lo esclude e propone
--   «registra» — vedi la capability.
-- Brief: brief-db-magazzino-lotto-2-bis-be-fe R-1;
--   brief-db-magazzino-lotto-2-motore sezione 3 (D-L2-h).
BEGIN
    RETURN CASE p_stato_da
               WHEN 'DRAFT'   THEN ARRAY['CONFIRM', 'CANCEL']
               WHEN 'CONFIRM' THEN ARRAY['POSTED', 'CANCEL', 'DRAFT']
               ELSE '{}'::text[]     -- POSTED, CANCEL: terminali
           END;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_documento_interno_transizioni(p_stato_da text)
IS 'La matrice degli stati dei documenti interni di magazzino (inventari e rettifiche, la stessa per le due famiglie — D-L2-h): le destinazioni ammesse da uno stato. DRAFT -> {CONFIRM, CANCEL}; CONFIRM -> {POSTED, CANCEL, DRAFT} (riapri, C13); POSTED e CANCEL -> {} (terminali). Uno stato sconosciuto torna {}: il cancello sui valori e'' il CHECK di tabella. IMMUTABLE: non legge niente, la matrice e'' una costante del modello. ⭐ Esiste per avere UNA sede con due lettori: magazzino.trgfn_documento_interno_guard_transizione la fa rispettare, script.fn_available_actions_inventario / _rettifica disegnano i pulsanti (linee-guida-sql §12.2 punto 1). ⚠️ POSTED e'' ammesso ma non richiedibile: la porta la apre solo l''operazione con la GUC transazionale, quindi la capability lo esclude dalle azioni e propone «registra». Brief: brief-db-magazzino-lotto-2-bis-be-fe R-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
