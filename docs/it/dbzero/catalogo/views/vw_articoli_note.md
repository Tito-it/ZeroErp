{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_note.md" %}
# 🔍 View `vw_articoli_note`

> 📝 **Descrizione**
>
> Vista note per articoli con dati stile e lingua. Rev 2026-10-25 (20261025-57/-58, brief-db-grammatica-unica-documenti lotto 3, G-7): tolta e rimessa identica perche' la colonna che legge cambia tipo; nota_target_tipo vale ARTICOLO (era ARTICOLI) e diventa varchar(50), dalla partizione.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_note AS
SELECT a.id AS articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    n.id AS nota_id,
    n.target_tipo AS nota_target_tipo,
    n.target_id AS nota_target_id,
    n.target_riga_id AS nota_target_riga_id,
    n.anchor_tipo AS nota_anchor_tipo,
    n.posizione AS nota_posizione,
    n.seq AS nota_seq,
    n.testo AS nota_testo,
    n.testo_md AS nota_testo_md,
    n.visibile AS nota_visibile,
    n.solo_stampa AS nota_solo_stampa,
    n.meta AS nota_meta,
    n.data_insert AS nota_data_insert,
    n.user_insert AS nota_user_insert,
    n.data_update AS nota_data_update,
    n.user_update AS nota_user_update,
    ns.id AS stile_id,
    ns.codice AS stile_codice,
    ns.descrizione AS stile_descrizione,
    l.id AS lingua_id,
    l.codice_iso AS lingua_codice_iso,
    l.descrizione AS lingua_descrizione,
    l.descrizione_locale AS lingua_descrizione_locale
   FROM (((catalogo.note_articoli n
     JOIN catalogo.articoli a ON ((a.id = n.target_id)))
     LEFT JOIN config.note_stili ns ON ((ns.id = n.id_stile)))
     LEFT JOIN config.lingue l ON ((l.id = n.id_lingua)));
```

</div>


---
{% include-markdown "signature-core.md" %}
