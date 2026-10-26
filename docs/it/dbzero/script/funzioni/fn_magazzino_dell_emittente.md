# ⚙️ Funzione `fn_magazzino_dell_emittente`

```sql
CREATE FUNCTION fn_magazzino_dell_emittente(p_magazzino_id bigint, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_magazzino_dell_emittente(p_magazzino_id bigint, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: «questo magazzino appartiene a questo emittente?» — la regola M-6
--   di un documento che nomina un magazzino (nessuna operazione attraversa
--   due emittenti), in una sede sola.
-- ⛔ INVOKER, di proposito: si legge SOTTO RLS. Un magazzino di un altro
--   emittente non si vede, e deve rispondere come uno inesistente (false):
--   il chiamante dice la stessa frase, e non rivela che cosa c'e' fuori dal
--   perimetro. Una DEFINER qui darebbe al rifiuto un'informazione in piu'.
-- Contratto: magazzino NULL -> NULL (non c'e' niente da giudicare: la
--   scelta e' del chiamante, di solito «salta»); altrimenti true solo se il
--   magazzino e' visibile ed e' dell'emittente passato.
-- Consumatori (2026-09-28): vendite.trgfn_ddt_guard_magazzino (partenza e
--   arrivo della bolla), vendite.trgfn_resi_guard_magazzino (rientro del reso).
DECLARE
    v_ef magazzino.magazzini.emittente_fiscale_id%TYPE;
BEGIN
    IF p_magazzino_id IS NULL THEN
        RETURN NULL;
    END IF;
    SELECT m.emittente_fiscale_id INTO v_ef
      FROM magazzino.magazzini m
     WHERE m.id = p_magazzino_id;
    RETURN v_ef IS NOT NULL AND v_ef IS NOT DISTINCT FROM p_emittente_fiscale_id;
END;
$function$

COMMENT ON FUNCTION script.fn_magazzino_dell_emittente(p_magazzino_id bigint, p_emittente_fiscale_id bigint)
IS 'Building block (regola del 2, 2026-09-28): true se il magazzino e'' visibile ed e'' dell''emittente passato — la regola M-6 di un documento che nomina un magazzino. INVOKER: letto sotto RLS, un magazzino di un altro emittente risponde come uno inesistente (false), cosi'' il rifiuto non rivela niente fuori dal perimetro. Magazzino NULL -> NULL (il chiamante salta). Consumatori: vendite.trgfn_ddt_guard_magazzino, vendite.trgfn_resi_guard_magazzino. Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso (D-3b-a).';
```

</div>

---
{% include-markdown "signature-core.md" %}
