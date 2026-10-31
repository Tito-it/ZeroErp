# ⚙️ Funzione `fn_registro_che_copre_coppia`

```sql
CREATE FUNCTION fn_registro_che_copre_coppia(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer, p_registro_escluso_id bigint, p_collegamento_escluso_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_registro_che_copre_coppia(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer, p_registro_escluso_id bigint, p_collegamento_escluso_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_registro_id vendite.registri_fatturazione.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il registro (diverso da p_registro_escluso_id) che
    --   copre GIA' la coppia (tipo, natura) per questo
    --   emittente e questa utility; NULL se nessuno.
    --
    -- Regole:
    --   - utility confrontata NULL = NULL: e' cio' che il lookup
    --     non saprebbe scegliere;
    --   - anche i registri spenti: il lookup non guarda attivo;
    --   - p_collegamento_escluso_id: la riga che un BEFORE UPDATE
    --     sta spostando, che la tabella mostra ancora com'era.
    -- =========================================================
    SELECT r.id
      INTO v_registro_id
      FROM vendite.tipi_doc_fiscale_registri m
      JOIN vendite.registri_fatturazione r ON r.id = m.registro_id
     WHERE m.tipo_doc_fiscale_id         = p_tipo_doc_fiscale_id
       AND m.natura_doc_id               = p_natura_doc_id
       AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
       AND r.utility_id IS NOT DISTINCT FROM p_utility_id
       AND r.id <> p_registro_escluso_id
       AND m.id IS DISTINCT FROM p_collegamento_escluso_id
     ORDER BY r.id
     LIMIT 1;

    RETURN v_registro_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_registro_che_copre_coppia(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer, p_registro_escluso_id bigint, p_collegamento_escluso_id bigint)
IS 'LETTORE (2026-10-18, rev 2026-10-28): il registro, diverso da quello escluso, che copre GIA'' la coppia (tipo documento, natura) per questo emittente e questa utility (NULL = NULL); NULL se nessuno. E'' la chiave che vendite.fn_lookup_registro_id non saprebbe scegliere: due registri cosi'' li ordinerebbe per id. Conta anche i registri spenti (il lookup non guarda attivo); un registro di UNA utility accanto a quello di tutte non e'' ambiguo. p_collegamento_escluso_id (in coda, DEFAULT NULL): il collegamento che un guard BEFORE UPDATE sta spostando, che la tabella mostra ancora sul registro di partenza; senza, lo spostamento fra due registri dello stesso emittente e utility contava se stesso come occupante (rev 2026-10-28). ⭐ L''ORDER BY r.id qui non sceglie fra due candidati validi: con i guard accesi il candidato e'' uno, e l''ordine rende stabile la risposta sui dati nati prima del guard. Lettori: i due guard vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica (passa il collegamento) e vendite.trgfn_registri_fatturazione_guard_coppia_unica (non serve: esclude gia'' il registro che si sposta). R-BE-14, D-14d di Tid, brief-db-processi-accensione-per-ambiente §6.14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
