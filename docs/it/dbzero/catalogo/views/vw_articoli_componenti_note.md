{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_componenti_note.md" %}
# 🔍 View `vw_articoli_componenti_note`

> 📝 **Descrizione**
>
> Le note dei legami di distinta, una riga per nota, col legame, i codici e le descrizioni di padre e componente e la decodifica dello stile e della lingua. Le colonne di nota vengono da catalogo.vw_note (nota_target_tipo ARTICOLO_COMPONENTE, la partizione catalogo.note_articoli_componenti). Non filtra le note nascoste ne' quelle di sola stampa. Si legge; le note si scrivono sulla partizione. Rev 2026-11-11 (20261111-77/-80, brief-db-revisione-catalogo giro 4, R6): sopra la vista base, stesse colonne; user_* text.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_componenti_note AS
SELECT ac.id AS articolo_componente_id,
    ac.prodotto_id,
    ap.codice AS prodotto_codice,
    ap.descrizione AS prodotto_descrizione,
    ac.componente_id,
    acmp.codice AS componente_codice,
    acmp.descrizione AS componente_descrizione,
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
   FROM (((catalogo.vw_note n
     JOIN catalogo.articoli_componenti ac ON ((ac.id = n.nota_target_id)))
     LEFT JOIN catalogo.articoli ap ON ((ap.id = ac.prodotto_id)))
     LEFT JOIN catalogo.articoli acmp ON ((acmp.id = ac.componente_id)))
  WHERE ((n.nota_target_tipo)::text = 'ARTICOLO_COMPONENTE'::text);
```

</div>


---
{% include-markdown "signature-core.md" %}
