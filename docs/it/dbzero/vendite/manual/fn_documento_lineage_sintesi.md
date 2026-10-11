## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_sintesi(p_tipo_ids, p_uids)`

> 👀 **Vedi anche**
>
> [vendite.vw_documento_lineage](/dbzero/vendite/views/vw_documento_lineage) — la stessa sintesi per tutti i documenti (si ritira nel giro B)
> [vendite.fn_documento_lineage_archi](/dbzero/vendite/funzioni/fn_documento_lineage_archi) — gli archi per chiave
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage) — il pannello «Passaggi»
> Brief: `docs/it/dev/work-in-progress/brief-db-lineage-seminata-per-chiave.md` §8.5

---
### 🎯 Scopo Principale
(rev 2026-10-11)

Per ogni documento chiesto, **dove è arrivato e da dove viene**: la pratica, la
**frontiera** (il documento più a valle ancora attivo della sua catena), quanti
discendenti diretti ha e quanti sono attivi, quante sorgenti ha e qual è la
**radice**, la natura fiscale. Sono le colonne che le liste e il drawer mostrano
accanto a ogni documento.

È [`vw_documento_lineage`](vw_documento_lineage.md) ristretta ai documenti che
servono: la vista calcola tutto questo per **ogni** documento del sistema, e una
pagina da 25 righe ne pagava il costo intero. La funzione segue il grafo un
livello alla volta partendo dai documenti chiesti, e il costo segue la pagina.

---

### Il seme

La chiave del nodo, come per
[`fn_documento_lineage_archi`](fn_documento_lineage_archi.md): tipo e chiave del
documento resa a testo, in due array paralleli. **Obbligatorio**: senza seme la
funzione solleva `E_ERRORE_PARAMETRI` — la sintesi di tutti i documenti è la vista.
Un documento che chi legge non vede non compare.

---

### La regola, in breve

| Colonna | Come si decide |
| --- | --- |
| frontiera | fra il documento e quelli che raggiunge **in avanti** (senza i rami di ritorno: il reso che torna, la nota che rettifica), il primo **attivo**; a parità, il più lontano, poi il più avanzato nella pipeline |
| discendenti | i documenti raggiunti al primo passo, e quanti sono attivi |
| sorgenti e radice | i passaggi **entranti**; la radice è la sorgente `ROOT`, poi la più a monte |
| pratica | la pratica del documento (la prima, se sono più d'una, e quante sono) |

⛔ **Due copie fino al giro B.** Finché liste e drawer leggono la vista, la
regola sta anche lì: chi la cambia la cambia in tutte e due. Il presidio
`db/pgtap/vendite/test-documento-lineage-seminata-v1.sql` (test 19-20) le tiene
uguali; il giro B ritira la vista.

{% include-markdown "signature-core.md" %}
