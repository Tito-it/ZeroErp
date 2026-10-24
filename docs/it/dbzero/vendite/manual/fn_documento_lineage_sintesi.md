## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_sintesi(p_tipo_ids, p_uids)`

> 👀 **Vedi anche**
>
> [vendite.fn_documento_lineage_archi](/dbzero/vendite/funzioni/fn_documento_lineage_archi) — gli archi per chiave
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage) — il pannello «Passaggi»
> Brief: `docs/it/dev/work-done/brief-db-lineage-seminata-per-chiave.md` §8.5

---
### 🎯 Scopo Principale
(rev 2026-10-11)

Per ogni documento chiesto, **dove è arrivato e da dove viene**: la pratica, la
**frontiera** (il documento più a valle ancora attivo della sua catena), quanti
discendenti diretti ha e quanti sono attivi, quante sorgenti ha e qual è la
**radice**, la natura fiscale. Sono le colonne che le liste e il drawer mostrano
accanto a ogni documento.

È la regola di `vw_documento_lineage` (ritirata) ristretta ai documenti che
servono: la vista calcola tutto questo per **ogni** documento del sistema, e una
pagina da 25 righe ne pagava il costo intero. La funzione segue il grafo un
livello alla volta partendo dai documenti chiesti, e il costo segue la pagina.

---

### Il seme

La chiave del nodo, come per
[`fn_documento_lineage_archi`](fn_documento_lineage_archi.md): tipo e chiave del
documento resa a testo, in due array paralleli. **Obbligatorio**: senza seme la
funzione solleva `E_ERRORE_PARAMETRI`: si chiede per le chiavi dei documenti che servono.
Un documento che chi legge non vede non compare.

---

### La regola, in breve

| Colonna | Come si decide |
| --- | --- |
| frontiera | fra il documento e quelli che raggiunge **in avanti** (senza i rami di ritorno: il reso che torna, la nota che rettifica), il primo **attivo**; a parità, il più lontano, poi il più avanzato nella pipeline |
| discendenti | i documenti raggiunti al primo passo, e quanti sono attivi |
| sorgenti e radice | i passaggi **entranti**; la radice è la sorgente `ROOT`, poi la più a monte |
| pratica | la pratica del documento (la prima, se sono più d'una, e quante sono) |

⭐ **Sede unica.** Dal giro B (changeSet `20261011-96…-98`) la vista
`vw_documento_lineage`, che era la seconda copia della regola, non c'è più: liste,
export e drawer leggono le colonne del grafo da qui. La pratica la legge da
`pratiche.fn_pratica_del_documento`, la stessa delle liste.

### 🔄 rev 2026-10-13 — un legame ritirato non è una destinazione

`20261013-71`, D-15 di Tid. Un preventivo annullato, ritirato da una commessa
che resta viva, aveva per frontiera la commessa «pronta da fatturare»: la lista
diceva che il preventivo stava lì. Ora un arco il cui legame è ritirato
([`fn_documento_lineage_legami`](fn_documento_lineage_legami.md)) si scarta alla
lettura degli archi di ogni livello. Quindi non conta per niente di ciò che ne
deriva: cammino, frontiera, discendenti, «transitato», sorgenti e radice. Un
arco non censito resta, come prima. Il pannello «Passaggi» lo mostra ancora,
come storia.

Esempio: un preventivo evaso il cui ordine è stato annullato torna «non
transitato». È giusto: si può smistare di nuovo.

{% include-markdown "signature-core.md" %}
