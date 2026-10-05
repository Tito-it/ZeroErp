## 📘 Documentazione Concettuale – Funzione `script.fn_sorgente_chiave_id()`

> 👀 **Vedi anche**
>
> **Gemella:** [script.fn_sorgente_chiave_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid) — il perché sta lì
> **Chi la chiama:** [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) · [script.vw_pratica_doc_sorgente](/dbzero/script/views/vw_pratica_doc_sorgente)

---

### 🎯 Scopo Principale
(scritta il 05-10-2026)

Gemella di `fn_sorgente_chiave_uuid` per i documenti indicati con l'**id** (ordini,
contratti, DDT, resi): riporta la chiave testuale al suo tipo intero, per cercare il
documento sulla colonna `sorgente_chiave_id` di `script.vw_stato_sorgente`.

| Testo in ingresso | Risultato |
| --- | --- |
| un intero scritto come lo scrive il database (`42`) | 42 |
| un intero in un'altra forma (`042`, ` 42`, `+42`) | NULL |
| un uuid, o qualunque altra cosa | NULL |
| NULL | NULL |

Non solleva mai errori. Le ragioni — perché esiste, perché le forme non canoniche danno NULL —
sono le stesse della gemella.

Presidio: `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql` casi 10-13.

{% include-markdown "signature-core.md" %}
