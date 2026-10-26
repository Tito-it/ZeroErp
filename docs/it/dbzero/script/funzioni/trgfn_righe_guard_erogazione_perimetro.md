# ⚙️ Funzione `trgfn_righe_guard_erogazione_perimetro`

```sql
CREATE FUNCTION trgfn_righe_guard_erogazione_perimetro()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_erogazione_perimetro()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- Scopo: rifiutare una riga di contratto o di offerta fuori dal perimetro
--   dell'articolo (B-R3, B-D4 di Tid del 2026-10-07): solleva il primo
--   motivo di script.fn_check_riga_erogazione, col suo campo. Il predicato sta
--   nella check: qui si solleva soltanto (linee-guida-sql §12.5.2).
-- TG_ARGV[0]: documento (CONTRATTO | OFFERTA_COMMERCIALE); TG_ARGV[1]: colonna del
--   documento padre (contratto_id | offerta_id).
-- Montato BEFORE INSERT e BEFORE UPDATE (solo quando cambiano articolo,
--   erogazione o fonte: le righe gia' scritte restano come sono, B-D6),
--   WHEN tipo_eccezione <> 'ESCLUSIONE', con un nome che viene DOPO
--   default_erogazione_da_articolo e default_fonte_qta: giudica la riga
--   gia' completata.
DECLARE
    v_documento   text   := TG_ARGV[0];
    v_col_padre   text   := TG_ARGV[1];
    v_documento_id bigint := (to_jsonb(NEW) ->> v_col_padre)::bigint;
    v_motivi      jsonb;
BEGIN
    v_motivi := script.fn_check_riga_erogazione(
        v_documento, v_documento_id, NEW.articolo_id, NEW.tipo_eccezione,
        NEW.tipo_erogazione, NEW.fonte_quantita_attesa);

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        v_motivi,
        v_motivi -> 0 -> 'dettaglio' ->> 'campo',
        NEW.tx_id,
        jsonb_build_object('riga_id', NEW.id, v_col_padre, v_documento_id));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_erogazione_perimetro()
IS 'Guard generico (vendite.contratti_righe, vendite.offerte_commerciali_eccezioni): solleva il primo motivo di script.fn_check_riga_erogazione — E_RIGA_TIPOLOGIA_FUORI_UTILITY o E_RIGA_EROGAZIONE_FUORI_PERIMETRO — col campo che il motivo indica (dettaglio.campo). TG_ARGV[0] = documento (CONTRATTO | OFFERTA), TG_ARGV[1] = colonna del padre. Montato BEFORE INSERT e BEFORE UPDATE quando cambiano articolo, erogazione o fonte (le righe già scritte restano come sono, decisione B-D6 di Tid), WHEN tipo_eccezione <> ESCLUSIONE, dopo l''eredità e la fonte di default. Parla prima della FK sul vocabolario, che resta la rete. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.7 (B3). ⭐ rev 2026-10-19 (20261019-29, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. I due montaggi su vendite.offerte_commerciali_eccezioni passano OFFERTA_COMMERCIALE dal 20261019-30.';
```

</div>

---
{% include-markdown "signature-core.md" %}
