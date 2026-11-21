## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_sintesi_colonne`

> 👀 **Vedi anche**
>
> [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi)
> Brief: `docs/it/dev/work-done/2026/brief-db-lineage-seminata-per-chiave.md` §8.1, §8.6

---
### 🎯 Scopo Principale
(rev 2026-10-11)

L'elenco delle colonne che restituisce
[`fn_documento_lineage_sintesi`](fn_documento_lineage_sintesi.md), letto dal
catalogo di sistema: una riga per colonna, con la posizione.

Serve a verificare i nomi delle colonne di lista che leggono dalla lineage. Una
colonna del catalogo `ui.lista_colonna` dichiara da dove legge
(`origine_campo`): una colonna `LINEAGE`, su una lista che dichiara
`legge_lineage`, la chiede il backend alla sintesi per le chiavi della pagina (o
dell'export, o del drawer). È il caso della colonna «Transito»
(`frontiera_codice`). Che il suo nome compaia qui lo verificano il presidio
[dbops.vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano)
e i pgTAP `ui/test-lista-*-seed`; il guard delle colonne di `ui` non legge questa
vista.

Segue da sola la firma della funzione: non c'è un elenco da tenere allineato.

{% include-markdown "signature-core.md" %}
