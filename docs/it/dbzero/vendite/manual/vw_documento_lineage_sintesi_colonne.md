## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_sintesi_colonne`

> 👀 **Vedi anche**
>
> [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi)
> Brief: `docs/it/dev/work-done/brief-db-lineage-seminata-per-chiave.md` §8.1, §8.6

---
### 🎯 Scopo Principale
(rev 2026-10-11)

L'elenco delle colonne che restituisce
[`fn_documento_lineage_sintesi`](fn_documento_lineage_sintesi.md), letto dal
catalogo di sistema: una riga per colonna, con la posizione.

Serve a decidere **da dove viene una colonna di lista**. Se il `campo_sorgente`
di una colonna del catalogo `ui.lista_colonna` non è una colonna della vista di
lista ma compare qui, il backend la chiede alla sintesi per le chiavi della
pagina (o dell'export, o del drawer). È il caso della colonna «Transito»
(`frontiera_codice`). La stessa regola la usano i presidi `ui/test-lista-*-seed`.

Segue da sola la firma della funzione: non c'è un elenco da tenere allineato.

{% include-markdown "signature-core.md" %}
