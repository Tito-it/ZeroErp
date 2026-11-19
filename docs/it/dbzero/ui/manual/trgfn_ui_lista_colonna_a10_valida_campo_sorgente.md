## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — la colonna che si scrive
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la vista e lo schema della lista
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_sintesi_colonne](/dbzero/vendite/views/vw_documento_lineage_sintesi_colonne) — i nomi della lineage, ammessi anche se la vista non li ha
>
> Approfondimento funzioni:
>
> * [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql) — il controllo gemello sulla vista della lista
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — da dove il backend prende le colonne della lineage
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — il catalogo delle colonne

---

### 🎯 Scopo Principale

Il trigger verifica, quando una colonna di lista si scrive, che il suo `campo_sorgente` sia una
colonna vera della vista della lista, cercata nel suo schema: un nome sbagliato si ferma al
salvataggio invece che alla prima apertura della lista.

---

### Quando controlla

Parte alla nascita della colonna e quando cambiano `campo_sorgente`, `tipo_colonna` o `lista_id`, i
tre campi da cui dipende la risposta. Non controlla:

* le colonne `azione`;
* le colonne senza sorgente;
* le colonne di una lista che non dichiara una vista: lì le celle le riempie il backend, e non c'è
  niente contro cui verificare.

---

### Che cosa vale come campo vero

* Una colonna non di sistema e non cancellata della relazione `vista_sql` nello schema
  `schema_dati` della lista; la relazione è una vista, una vista materializzata o una tabella. Una
  omonima in un altro schema non conta.
* Oppure un nome della sintesi della lineage dei documenti: quelle colonne sono uscite dalle viste
  di lista, e il backend le chiede alla funzione della lineage per le righe della pagina, unendole
  con lo stesso nome.

---

### ⚠️ Che cosa oggi non copre

* **Una vista che cambia, o una lista che cambia vista, non fa ripartire il controllo**: le colonne
  già scritte restano anche se la vista non le ha più. Il controllo non è stato messo sul trigger
  della definizione perché il seed delle definizioni si carica prima di quello delle colonne, e un
  cambio di vista fatto insieme alle colonne fermerebbe la migrazione a metà. Le vede il presidio
  pgTAP del catalogo, solo sulle righe del seed; un cambio di vista fatto dalla pagina tecnica
  sfugge.
* **Le azioni non si controllano anche quando hanno un campo sorgente.** Il modello ammette
  un'azione con `campo_sorgente`, e un nome inventato passa.
* **I nomi della lineage passano su ogni lista**, anche su una che non legge documenti. Il guard di
  `ui` dipende da una vista di `vendite`.
* **Il controllo non salta sulle liste spente.** Una lista registrata prima che la sua vista esista
  non accetta colonne con sorgente finché la vista non c'è: il gemello della vista, invece, sulle
  liste spente salta.
* **Una sorgente partizionata è rifiutata**: le tabelle partizionate non sono fra i tipi ammessi.
* **Il corpo tratta ancora la stringa vuota come assenza.** Non è più raggiungibile: il CHECK di
  `campo_sorgente` la rifiuta prima.

---

### Codici errore

* `E_UI_CAMPO_SORGENTE_NON_TROVATO` — il campo non è nella vista della lista, nel suo schema, né fra
  i nomi della lineage. La frase porta il campo e la vista qualificata.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — un campo che esiste solo
  nell'omonima di un altro schema è rifiutato (saltato, e dichiarato, se la gemella storica non
  c'è); la colonna vera passa; ogni campo del catalogo sta nella sua vista o nella lineage.
* `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql` — le colonne della lineage sulle liste dei
  documenti.

---

### Note di migrazione

* 2026-05-06 — nasce, col catalogo delle colonne.
* 2026-09-27 — la vista si cerca nel suo schema: prima bastava un'omonima in qualunque schema.
* 2026-10-11 — sono ammessi i nomi della sintesi della lineage, usciti dalle viste di lista.

---

{% include-markdown "signature-core.md" %}
