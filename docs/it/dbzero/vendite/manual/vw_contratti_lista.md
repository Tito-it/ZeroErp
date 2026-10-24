## 📘 Documentazione Concettuale – Vista `vendite.vw_contratti_lista`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
>
Approfondimento viste:
> • [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) (era `vw_documento_lineage`, ritirata nel giro B)
>
Approfondimento funzioni:
> • [vendite.trgfn_contratti_set_categoria_cliente_snapshot](/dbzero/vendite/funzioni/trgfn_contratti_set_categoria_cliente_snapshot)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Vista **flat** dei contratti per la lista UI configurabile `vendite.contratti`. Tredici join
denormalizzati in una riga: cliente e sua ragione sociale, emittente fiscale (codice **e**
ragione sociale), utility, stato con la sua `fase`, listino e versione, variazione globale,
categoria cliente **dallo snapshot**, valuta, audit — più il blocco di lineage.

---

### ⚠️ «Nessuno scope» significa «nessun filtro suo», non «nessun perimetro»

Il commento della vista dice *pura denormalizzazione: nessuno scope*, e va letto con
precisione, perché da solo si presta a essere frainteso.

La vista è `WITH (security_invoker = on)`: **eredita** le policy RLS di chi interroga. E fra
le tabelle lette ce ne sono due con RLS attiva — `vendite.contratti` (una policy) e
`anagrafiche.billing_account` (quattro).

Quindi il perimetro c'è, e morde. Quello che manca è un filtro **scritto nel corpo**, ed è
giusto che manchi: duplicherebbe le policy in un secondo posto.

⚠️ Il billing account è agganciato con un **`JOIN` interno**, come il suo soggetto, la utility
e lo stato. Un contratto il cui BA è fuori perimetro **non compare affatto** — non compare
«senza cliente». Anche qui vale la regola: *un conteggio più basso del previsto può essere il
perimetro, non i dati.*

---

### La categoria cliente è quella **congelata**, non quella corrente

`categoria_cliente_id_snapshot` e le due colonne derivate
(`categoria_cliente_snapshot_codice`, `..._descrizione`) vengono dallo **snapshot preso sul
contratto**, non dal billing account di oggi. Lo mantiene
`trgfn_contratti_set_categoria_cliente_snapshot`, che lo riempie alla creazione e lo congela
fuori da `DRAFT`.

⚠️ Se il cliente viene riclassificato dopo la firma, questa lista continua a mostrare la
categoria **del contratto** — ed è il dato corretto per un contratto. Chi si aspetta la
categoria attuale del cliente sta guardando la colonna sbagliata: quella sta in
`anagrafiche.billing_account`.

---

### Il blocco lineage è agganciato per chiave polimorfa

Le colonne `pratica_id`, `pratica_numero`, `n_pratiche`, `frontiera_*`,
`n_discendenti_attivi`, `is_transitato` arrivano da `vendite.vw_documento_lineage` con un
`LEFT JOIN` su due condizioni: il `tipo_id` risolto da `config.sorgenti` con
`codice_interno = 'CONTRATTO'`, e `lin.uid = c.id::text`.

⚠️ Due cose da sapere:

* la chiave del lineage è **`id::text`**, non `uid`. È la scelta per-dominio della sorgente
  polimorfa: alcuni domini si agganciano per `uid`, il contratto per `id`. Non è un residuo
  da uniformare;
* la sotto-select su `config.sorgenti` filtra `attivo IS TRUE`. **Se quella riga venisse
  disattivata, il `tipo_id` diventerebbe `NULL`** e tutto il blocco lineage arriverebbe
  `NULL` per ogni contratto — senza errori, senza righe perse: solo colonne vuote.

---

### Cosa **non** garantisce

* **Nessun filtro di stato né di validità**: contratti annullati e scaduti ci sono, con il
  loro `stato_codice_interno` e le date. Filtrare è compito della lista.
* **Nessun ordinamento**.
* **Nessuna riga per contratto senza BA, soggetto, utility o stato** (`JOIN` interni);
  emittente, listino, versione, categoria e valuta sono invece `LEFT JOIN` e lasciano `NULL`.

---

### Consumatori

Backend (repository contratti) e frontend, più la lista configurabile in `ui.lista_colonna`.
⚠️ Aggiungere una colonna alla lista vuol dire aggiungerla **qui** e poi registrarla: la lista
non può mostrare ciò che la vista non espone.

---

---

### 🔄 rev 2026-10-11 — la lista non calcola più il grafo

Changeset `20261011-97`. La vista non legge più la sintesi della lineage di tutti
i documenti. Le colonne della frontiera e del transito (`frontiera_*`,
`n_discendenti_attivi`, `is_transitato`) le chiede il backend a
[`fn_documento_lineage_sintesi`](fn_documento_lineage_sintesi.md) per i soli
documenti della pagina. La pratica (`pratica_id`, `pratica_numero`,
`n_pratiche`) resta qui, filtrabile e ordinabile, e la legge
`pratiche.fn_pratica_del_documento`. Una pagina da 25 righe costava ~320-390 ms,
ora ~8-70 ms più la sintesi delle 25 chiavi (~58 ms) — dbdev, 2026-10-11.

{% include-markdown "signature-core.md" %}
