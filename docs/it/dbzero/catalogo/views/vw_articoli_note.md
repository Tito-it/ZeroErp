{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_note.md" %}
# 🔍 View `vw_articoli_note`

> 📝 **Descrizione**
>
> Le note degli articoli, una riga per nota, col codice e la descrizione dell'articolo annotato e la decodifica dello stile e della lingua. Le colonne di nota vengono da catalogo.vw_note (nota_target_tipo ARTICOLO, la partizione catalogo.note_articoli). Non filtra le note nascoste ne' quelle di sola stampa. Si legge; le note si scrivono sulla partizione. nota_user_insert e nota_user_update sono text.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_note AS
SELECT a.id AS articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    n.nota_id,
    n.nota_target_tipo,
    n.nota_target_id,
    n.nota_target_riga_id,
    n.nota_anchor_tipo,
    n.nota_posizione,
    n.nota_seq,
    n.nota_testo,
    n.nota_testo_md,
    n.nota_visibile,
    n.nota_solo_stampa,
    n.nota_meta,
    n.nota_data_insert,
    n.nota_user_insert,
    n.nota_data_update,
    n.nota_user_update,
    n.stile_id,
    n.stile_codice,
    n.stile_descrizione,
    n.lingua_id,
    n.lingua_codice_iso,
    n.lingua_descrizione,
    n.lingua_descrizione_locale
   FROM (catalogo.vw_note n
     JOIN catalogo.articoli a ON ((a.id = n.nota_target_id)))
  WHERE ((n.nota_target_tipo)::text = 'ARTICOLO'::text);
```

</div>


---
{% include-markdown "signature-core.md" %}
