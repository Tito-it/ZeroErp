## 📘 Documentazione Concettuale – Vista `vendite.vw_contratti_lista`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — la tabella base
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il cliente
> * [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti) — stato e fase
>
> Approfondimento funzioni:
>
> * [pratiche.fn_pratica_del_documento](/dbzero/pratiche/funzioni/fn_pratica_del_documento) — la pratica del contratto
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — frontiera e transito, per le righe della pagina
> * [vendite.trgfn_contratti_set_categoria_cliente_snapshot](/dbzero/vendite/funzioni/trgfn_contratti_set_categoria_cliente_snapshot) — la categoria congelata

---

### 🎯 Scopo Principale

Vista **flat** dei contratti per la lista UI configurabile `vendite.contratti`: in una riga cliente e sua ragione sociale, emittente fiscale (codice **e** ragione sociale), utility, stato con la sua `fase`, listino e versione, variazione globale, categoria cliente **dallo snapshot**, valuta, audit e la pratica a cui il contratto appartiene.

---

### ⚠️ «Nessuno scope» significa «nessun filtro suo», non «nessun perimetro»

Il commento della vista dice *pura denormalizzazione: nessuno scope*, e va letto con precisione.

La vista è `WITH (security_invoker = on)`: **eredita** le policy RLS di chi interroga. E fra le
tabelle lette ce ne sono con RLS attiva — `vendite.contratti` e `anagrafiche.billing_account`.

Quindi il perimetro c'è, e morde. Quello che manca è un filtro **scritto nel corpo**, ed è giusto
che manchi: duplicherebbe le policy in un secondo posto.

⚠️ Il billing account è agganciato con un **`JOIN` interno**, come il suo soggetto, la utility e lo
stato. Un contratto il cui BA è fuori perimetro **non compare affatto** — non compare «senza
cliente». Anche qui vale la regola: *un conteggio più basso del previsto può essere il perimetro,
non i dati.*

---

### La categoria cliente è quella **congelata**, non quella corrente

`categoria_cliente_id_snapshot` e le due colonne derivate (`categoria_cliente_snapshot_codice`,
`..._descrizione`) vengono dallo **snapshot preso sul contratto**, non dal billing account di oggi.
Lo mantiene `trgfn_contratti_set_categoria_cliente_snapshot`, che lo riempie alla creazione e lo
congela fuori da `DRAFT`.

⚠️ Se il cliente viene riclassificato dopo la firma, questa lista continua a mostrare la categoria
**del contratto** — ed è il dato corretto per un contratto. La categoria attuale del cliente sta in
`anagrafiche.billing_account`.

---

### La pratica del contratto

`pratica_id`, `pratica_numero` e `n_pratiche` arrivano da
[`pratiche.fn_pratica_del_documento`](/dbzero/pratiche/funzioni/fn_pratica_del_documento), in un
`LEFT JOIN LATERAL`: la vista le passa il tipo `CONTRATTO` (risolto da `config.sorgenti` per
`codice_interno`) e le **due chiavi** del contratto, `id` e `uid`. La funzione cerca il collegamento
in `pratiche.pratiche_sorgenti`, che tiene la chiave nelle colonne tipizzate del modello (per il
contratto, a chiave `id`, in `sorgente_id`). Restano filtrabili e ordinabili.

⚠️ La lettura del tipo filtra `attivo IS TRUE`: se la riga `CONTRATTO` di `config.sorgenti` venisse
disattivata, le tre colonne arriverebbero vuote per ogni contratto — senza errori, senza righe
perse.

Le colonne del grafo (frontiera, discendenti, transito) **non** sono in questa vista: il backend le
chiede a [`fn_documento_lineage_sintesi`](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi)
per i soli contratti della pagina.

---

### Cosa **non** garantisce

* **Nessun filtro di stato né di validità**: contratti annullati e scaduti ci sono, con il loro
  `stato_codice_interno` e le date. Filtrare è compito della lista.
* **Nessun ordinamento**.
* **Nessuna riga per contratto senza BA, soggetto, utility o stato** (`JOIN` interni); emittente,
  listino, versione, categoria e valuta sono invece `LEFT JOIN` e lasciano `NULL`.

---

### Consumatori

Backend (repository contratti) e frontend, più la lista configurabile in `ui.lista_colonna`.
⚠️ Aggiungere una colonna alla lista vuol dire aggiungerla **qui** e poi registrarla: la lista non
può mostrare ciò che la vista non espone.

---

### Note di migrazione

* 2026-10-11 — la vista non calcola più il grafo: le colonne della frontiera e del transito passano
  a `fn_documento_lineage_sintesi`, chiesta dal backend per le righe della pagina, e la pratica
  resta qui (brief-db-lineage-seminata-per-chiave).
* 2026-11-08 — la pratica si legge con le due chiavi del contratto, sulle colonne tipizzate di
  `pratiche_sorgenti`; prima con la chiave in testo (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
