{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_listino_aggiungi_articoli.md" %}
# ⚙️ Funzione `fn_pgtap_listino_aggiungi_articoli`

```sql
CREATE FUNCTION fn_pgtap_listino_aggiungi_articoli(p_listino_versione_id bigint, p_articoli uuid[], p_prezzo numeric)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_listino_aggiungi_articoli(p_listino_versione_id bigint, p_articoli uuid[], p_prezzo numeric DEFAULT 100)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipologia vendite.listini.tipologia_id%TYPE;
BEGIN
    -- Scopo: mettere degli articoli in una versione di listino,
    --   per le fixture pgTAP che scrivono OVERRIDE o ESCLUSIONE (A-5).
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

    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT p_listino_versione_id, a.id, a.uom_id, p_prezzo
      FROM catalogo.articoli a
     WHERE a.id = ANY (p_articoli);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_listino_aggiungi_articoli(p_listino_versione_id bigint, p_articoli uuid[], p_prezzo numeric)
IS 'Builder pgTAP (Lotto 3b di brief-db-articoli-ammessi-per-documento, 2026-10-13): mette degli articoli in una versione di listino — tipologia dell''articolo allineata a quella del listino se diversa, poi una riga attiva per articolo con la UoM base e il prezzo dato (default 100). Per le fixture che scrivono OVERRIDE o ESCLUSIONE, che dal Lotto 3b pretendono l''articolo nel listino del documento (A-5). Va chiamato prima di usare l''articolo: su un articolo usato la tipologia non cambia (A-10). INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
