# ⚙️ Funzione `fn_fonte_porta_quantita`

```sql
CREATE FUNCTION fn_fonte_porta_quantita(p_fonte character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_fonte_porta_quantita(p_fonte character varying)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- FISSA: la quantita' e' quella della riga (qta_operativa -> quantita).
    -- Ogni altra fonte (MANUALE, LETTURE, TIMESHEET) la porta a valle.
    -- Rev 2026-10-21: DERIVATA_COMPONENTI ritirata (brief-db-offerta-
    -- emissione-ed-erogazione §I.1): i componenti seguono la quantita' del
    -- padre, mai il contrario.
    SELECT p_fonte = 'FISSA';
$function$

COMMENT ON FUNCTION script.fn_fonte_porta_quantita(p_fonte character varying)
IS 'Building block: true se la fonte (fonte_quantita_attesa) porta la quantita'' sulla riga (FISSA), false se la quantita'' arriva a valle (MANUALE, LETTURE, TIMESHEET, e ogni fonte nuova finche'' non la si aggiunge qui), NULL su fonte NULL. Lettori: script.trgfn_righe_guard_quantita_per_fonte (rifiuta qta_operativa con una fonte a valle) e script.trgfn_qta_from_operativa (con una fonte a valle porta quantita a NULL). I CHECK chk_contrighe_quantita_per_fonte e chk_offerte_eccezioni_quantita_per_fonte (la rete) tengono lo stesso elenco: un pgTAP li confronta (test-righe-quantita-per-fonte-v1). Nasce il 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.1 (F-1.3). Rev 2026-10-21 (20261021-45, §I.1, I-D1 di Tid): DERIVATA_COMPONENTI ritirata, la porta solo FISSA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
