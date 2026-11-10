## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_child_requires_non_obsolete_parent`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — figlia cablata, verso `pratiche.tipi_prestazione`
> * [vendite.listini_kit](/dbzero/vendite/tabelle/listini_kit) — figlia cablata, verso `catalogo.articoli`
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la gemella sull'asse `attivo`
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica degli argomenti
> * [dbops.fn_trigger_padre_stato](/dbzero/dbops/funzioni/fn_trigger_padre_stato) — legge il catalogo, fuori dalla row level security
> * [script.fn_e_obsoleto](/dbzero/script/funzioni/fn_e_obsoleto) — il predicato «ritirato alla data operativa»
> * [dbops.fn_get_lookup_codici](/dbzero/dbops/funzioni/fn_get_lookup_codici) — la selezione che nasconde le voci obsolete
> * [script.fn_bersaglio_di_riga](/dbzero/script/funzioni/fn_bersaglio_di_riga) — il bersaglio della voce, dal catalogo dei tipi
>
> Guide:
>
> * [Uso di obsoleto](/guide/uso-di-obsoleto) — l'asse `obsoleto_dal`, separato da `attivo`

---

### 🎯 Scopo Principale

Impedisce di **creare** un'istanza, o di **ricollegarla**, verso una voce di catalogo **obsoleta**,
cioè con `obsoleto_dal` raggiunto alla data operativa (`script.fn_e_obsoleto`). Le istanze che
puntano già a quella voce restano, e i loro avanzamenti di stato non si bloccano.

È la difesa in profondità di «la selezione nasconde, il database rifiuta»: la selezione nasconde
le voci obsolete (`dbops.fn_get_lookup_codici` senza obsoleti), questo trigger vieta di usarle
comunque.

---

### ⭐ Un asse diverso da `attivo`

Una voce obsoleta resta `attivo = true`: è ancora un riferimento valido per le istanze che la
usano, ma non si sceglie più per il nuovo. Il require della regola ATTIVO non la ferma, ed è per
questo che serve un trigger suo.

| | Asse `attivo` | Asse `obsoleto_dal` |
| --- | --- | --- |
| Domanda | il riferimento è valido? | si può scegliere per il nuovo? |
| Padre che blocca | spento | `obsoleto_dal` raggiunto |
| Montaggio | generato dal framework | cablato a mano, una relazione alla volta |
| Su un aggiornamento | dipende dalla colonna attivo del figlio | solo se la FK cambia |

---

### Quando il controllo si fa e quando no

* Una FK vuota passa: è facoltativa.
* Su un aggiornamento, se la FK non cambia il controllo non si fa: un cambio di stato di
  un'istanza storica non ripunta il catalogo e non si blocca mai.
* Una riga **derivata** da un altro documento passa all'inserimento, se il montaggio nomina la
  colonna di esenzione e la riga la valorizza (per esempio `sorgente_tipo_id`). Sull'aggiornamento
  l'esenzione non vale: cambiare la FK è sempre una scelta nuova.
* Una voce con `obsoleto_dal` vuoto, o con una data futura (ritiro programmato), si può usare.
* Il catalogo si legge con `dbops.fn_trigger_padre_stato`, fuori dalla row level security, come
  la gemella: una voce è obsoleta o no per tutti.

---

### Il cablaggio

Un trigger per relazione, con gli argomenti nella grammatica di `dbops.fn_trigger_attivo_argomenti`:
schema e tabella del catalogo, nome della colonna `obsoleto_dal`, colonna FK del figlio, colonna
referenziata — tutti obbligatori — e, facoltativa, la colonna di esenzione del figlio. Cablaggi di
esempio: `pratiche.pratiche` verso `pratiche.tipi_prestazione`, `pratiche.flussi` verso
`pratiche.template_flussi`, `vendite.listini_kit` verso `catalogo.articoli`,
`vendite.commesse_attivita` verso `catalogo.articoli` (con l'esenzione della riga derivata),
`anagrafiche.indirizzi_dettaglio` verso `config.stradario` (la via soppressa). Un catalogo nuovo è
un altro trigger, nessuna logica nuova.

---

### Codici errore

* `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (conflitto di stato, colonna FK nel campo) — la voce di
  catalogo è obsoleta: il caso per cui il codice esiste. La frase non nomina tabelle; quale voce lo
  dice il **bersaglio** (tipo e id), quando il catalogo dei tipi ne dichiara la tabella, come per la
  gemella. La data del ritiro, la voce, la colonna e il valore stanno nel contesto del registro
  errori.
* `E_PADRE_INESISTENTE` (dato errato) — nessuna voce del catalogo ha quella chiave; succede dove il
  collegamento non è una FK. Frase senza tabelle, nessun bersaglio.
* `E_TRIGGER_ARGOMENTI_INVALIDI` — il trigger è montato fuori grammatica, o nomina una colonna FK o
  di esenzione che la figlia non ha, o una tabella o una colonna del catalogo che non esiste.

---

### Test

* `db/pgtap/pratiche/test-guard-non-obsolete-parent-v1.sql` — su pratiche e flussi: voce
  selezionabile o con ritiro programmato passa, voce obsoleta si rifiuta; un aggiornamento che non
  tocca la FK passa anche quando la voce è diventata obsoleta; il ricollegamento a una voce
  obsoleta si rifiuta; la voce obsoleta resta attiva.
* `db/pgtap/dbops/test-guard-attivo-grammatica-e-codici-v1.sql` — su tabelle temporanee: il
  catalogo assente, l'esenzione della riga derivata, i montaggi sbagliati col loro codice.
* `db/pgtap/vendite/test-articolo-ritirato-v1.sql` — il kit e l'onere su un articolo ritirato.
* `db/pgtap/dbops/test-bersaglio-guard-attivo-v1.sql` — la frase del catalogo e il bersaglio della
  voce ritirata.

---

### Note di migrazione

* 2026-06-30 — nasce con il cablaggio su pratiche e flussi
  (`brief-db-obsoleto-dal-filtro-lookup-e-guard`).
* 2026-10-09 — «oggi» diventa la data operativa, nel fuso aziendale; prima era la data del server.
* 2026-11-05 — la colonna di esenzione della riga derivata, e il predicato in `script.fn_e_obsoleto`.
* 2026-11-07 — i montaggi sbagliati escono con `E_TRIGGER_ARGOMENTI_INVALIDI` (prima con il codice
  dell'obsoleto, un 409 che chiedeva all'operatore di scegliere un'altra voce); il catalogo assente
  si riconosce (prima passava); la colonna referenziata è obbligatoria; il catalogo si legge fuori
  dalla row level security.
* 2026-11-10 — la frase non nomina più il catalogo (prima: «Catalogo schema.tabella obsoleto dal …»,
  composta qui) e il rifiuto porta il bersaglio della voce.

---

{% include-markdown "signature-core.md" %}
