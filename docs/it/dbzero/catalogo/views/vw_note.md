{% include-markdown "it/dbzero/catalogo/manual/vw_note.md" %}
# 🔍 View `vw_note`

> 📝 **Descrizione**
>
> La proiezione di una nota di catalogo, una riga per nota di ogni partizione di catalogo.note, con la decodifica dello stile (config.note_stili) e della lingua (config.lingue). Non filtra: le note nascoste e quelle di sola stampa ci sono. E' la sede unica delle colonne di nota: catalogo.vw_articoli_note e catalogo.vw_articoli_componenti_note la leggono per il loro nota_target_tipo. Si legge, non si scrive: le note si scrivono sul padre o sulla partizione.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_note AS
SELECT n.id AS nota_id,
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
   FROM ((catalogo.note n
     LEFT JOIN config.note_stili ns ON ((ns.id = n.id_stile)))
     LEFT JOIN config.lingue l ON ((l.id = n.id_lingua)));
```

</div>


---
{% include-markdown "signature-core.md" %}
