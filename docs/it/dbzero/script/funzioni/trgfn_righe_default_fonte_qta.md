{% include-markdown "it/dbzero/script/manual/trgfn_righe_default_fonte_qta.md" %}
# ⚙️ Funzione `trgfn_righe_default_fonte_qta`

```sql
CREATE FUNCTION trgfn_righe_default_fonte_qta()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_default_fonte_qta()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: normalizza fonte_quantita_attesa al default coerente con
--   tipo_erogazione, letto da config.erogazioni_fonti (e_default).
-- Generica: usabile su qualunque *_righe / *_eccezioni con le colonne
--   tipo_erogazione + fonte_quantita_attesa (oggi vendite.contratti_righe e
--   vendite.offerte_commerciali_eccezioni).
-- INSERT: fonte NULL -> la fonte di default dell'erogazione.
-- UPDATE: se l'erogazione cambia e la combinazione con la fonte attuale non
--   e' coerente (non sta in config.erogazioni_fonti) -> la fonte di default.
--   Le combinazioni coerenti non si toccano.
-- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.7, giro B1):
--   la matrice era scritta qui due volte, in un CASE, ed era la stessa dei
--   CHECK chk_*_coerenza_fonte_erogazione. Ora e' un dato, e la sede e' una.
-- ⚠️ Senza erogazione (NULL) la fonte resta NULL: prima diventava FISSA, ma
--   una riga che si fattura senza erogazione la rifiuta comunque
--   trgfn_righe_guard_erogazione_obbligatoria, e l'ESCLUSIONE non passa di
--   qui (WHEN del trigger).
BEGIN
    IF NEW.fonte_quantita_attesa IS NULL
       OR (TG_OP = 'UPDATE'
           AND NEW.tipo_erogazione IS DISTINCT FROM OLD.tipo_erogazione
           AND NOT EXISTS (
               SELECT 1
                 FROM config.erogazioni_fonti ef
                WHERE ef.tipo_erogazione       = NEW.tipo_erogazione
                  AND ef.fonte_quantita_attesa = NEW.fonte_quantita_attesa))
    THEN
        NEW.fonte_quantita_attesa := (
            SELECT ef.fonte_quantita_attesa
              FROM config.erogazioni_fonti ef
             WHERE ef.tipo_erogazione = NEW.tipo_erogazione
               AND ef.e_default);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_default_fonte_qta()
IS 'Trigger generico (righe di contratto e di offerta): normalizza fonte_quantita_attesa alla fonte di default dell''erogazione, letta da config.erogazioni_fonti (e_default). INSERT: fonte NULL -> default. UPDATE: se cambia l''erogazione e la combinazione con la fonte attuale non è in config.erogazioni_fonti -> default; le combinazioni coerenti non si toccano. Senza erogazione la fonte resta NULL (la riga la rifiuta trgfn_righe_guard_erogazione_obbligatoria). Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.7, giro B1): la matrice era scritta qui in un CASE, copia dei CHECK chk_*_coerenza_fonte_erogazione; ora è il vocabolario, sede unica. Riusata da contratti_righe e offerte_commerciali_eccezioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
