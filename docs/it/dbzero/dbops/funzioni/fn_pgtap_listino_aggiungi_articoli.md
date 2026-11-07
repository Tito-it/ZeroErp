{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_listino_aggiungi_articoli.md" %}
# ⚙️ Funzione `fn_pgtap_listino_aggiungi_articoli`

```sql
CREATE FUNCTION fn_pgtap_listino_aggiungi_articoli(p_listino_versione_id bigint, p_articoli uuid[], p_prezzo numeric, p_periodicita character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_listino_aggiungi_articoli(p_listino_versione_id bigint, p_articoli uuid[], p_prezzo numeric DEFAULT 100, p_periodicita character varying DEFAULT NULL::character varying)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: mettere degli articoli in una versione di listino, per le
--   fixture pgTAP che scrivono OVERRIDE o ESCLUSIONE, o che vogliono un
--   listino col loro prezzo.
-- ⚠️ p_periodicita: la periodicita' delle righe. Una quota fissa a canone
--   (vendite.fn_articolo_quota_fissa_a_canone) senza periodicita' non
--   lascia attivare la versione (script.fn_check_versione_listino_attivabile):
--   il test che la mette in listino la da'.
DECLARE
    v_tipologia vendite.listini.tipologia_id%TYPE;
BEGIN
    SELECT l.tipologia_id INTO v_tipologia
      FROM vendite.listini_versioni lv
      JOIN vendite.listini l ON l.id = lv.listino_id
     WHERE lv.id = p_listino_versione_id;
    IF v_tipologia IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_listino_aggiungi_articoli: versione di listino % assente o senza tipologia',
            p_listino_versione_id;
    END IF;

    UPDATE catalogo.articoli a
       SET listino_tipologia_id = v_tipologia
     WHERE a.id = ANY (p_articoli)
       AND a.listino_tipologia_id IS DISTINCT FROM v_tipologia;

    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo, periodicita)
    SELECT p_listino_versione_id, a.id, a.uom_id, p_prezzo, p_periodicita
      FROM catalogo.articoli a
     WHERE a.id = ANY (p_articoli);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_listino_aggiungi_articoli(p_listino_versione_id bigint, p_articoli uuid[], p_prezzo numeric, p_periodicita character varying)
IS 'Fixture pgTAP: mette degli articoli in una versione di listino, una riga attiva per articolo con la unita'' di misura base, il prezzo dato (p_prezzo, default 100) e la periodicita'' data (p_periodicita, default nessuna). Allinea prima la tipologia dell''articolo a quella del listino, se diversa (su un articolo gia'' usato la tipologia non cambia: va chiamato prima di usarlo). La periodicita'' serve a una quota fissa a canone (vendite.fn_articolo_quota_fissa_a_canone): senza, la versione non si attiva (script.fn_check_versione_listino_attivabile). La usano le fixture che scrivono OVERRIDE o ESCLUSIONE, che pretendono l''articolo nel listino del documento, e dbops.fn_pgtap_crea_listino per la riga d''appoggio. Versione inesistente o senza tipologia: RAISE EXCEPTION. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
