{% include-markdown "it/dbzero/vendite/manual/vw_note.md" %}
# 🔍 View `vw_note`

> 📝 **Descrizione**
>
> La proiezione di una nota di vendite, una riga per nota di ogni partizione di vendite.note, con la decodifica dello stile (config.note_stili: codice, descrizione, codice_interno) e della lingua (config.lingue). Non filtra: le note nascoste e quelle di sola stampa ci sono. Ha le stesse colonne, nello stesso ordine, di catalogo.vw_note, acquisti.vw_note, magazzino.vw_note: una vista per ogni sede delle note, e la proiezione sta solo qui. security_invoker: vendite.note e' sotto RLS: la vista vede, per chi la interroga, le note che le policy della madre gli concedono. Si legge, non si scrive: le note si scrivono sul padre o sulla partizione.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_note
WITH (security_invoker=true) AS
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
    l.descrizione_locale AS lingua_descrizione_locale,
    ns.codice_interno AS stile_codice_interno
   FROM ((vendite.note n
     LEFT JOIN config.note_stili ns ON ((ns.id = n.id_stile)))
     LEFT JOIN config.lingue l ON ((l.id = n.id_lingua)));
```

</div>


---
{% include-markdown "signature-core.md" %}
