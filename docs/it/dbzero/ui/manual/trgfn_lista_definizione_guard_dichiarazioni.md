## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_lista_definizione_guard_dichiarazioni`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la tabella che porta le dichiarazioni
>
> Approfondimento viste:
>
> * [dbops.vw_liste_multi_emittente_non_certificate](/dbzero/dbops/views/vw_liste_multi_emittente_non_certificate) — le liste che si dicono multi-emittente senza la colonna dell'emittente
>
> Approfondimento funzioni:
>
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — chi scrive è il proprietario della tabella?
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — il bollino «multi-emittente»

---

### 🎯 Scopo Principale

Il trigger impedisce all'applicazione di cambiare le **dichiarazioni** di una lista:
`multi_emittente`, `perimetro_emittente` e `legge_lineage`. Le cambia solo il proprietario della
tabella, cioè la migrazione che carica il seed del catalogo, su ogni riga, anche su quelle create
dall'installazione.

---

### Che cosa dichiarano

* `multi_emittente` — la schermata **sa dire da quale azienda arriva ogni riga**;
* `perimetro_emittente` — le righe della lista **appartengono a un'azienda**;
* `legge_lineage` — il backend unisce alle righe la **sintesi della genealogia dei documenti**.

Sono capacità o nature del software, non preferenze di chi lo usa: si dichiarano nel seed insieme
al lavoro che le rende vere. Se fossero interruttori dell'interfaccia, il primo che trova fastidiosa
la scelta dell'azienda accenderebbe `multi_emittente`, o spegnerebbe `perimetro_emittente`, e la
lista mescolerebbe aziende senza dirlo.

---

### Che cosa conta come scrittura

* Alla nascita di una lista, un valore diverso da quello che non promette niente: `multi_emittente`
  acceso, `perimetro_emittente` spento, `legge_lineage` acceso. Il pericolo di `perimetro_emittente`
  è il `false`, quello delle altre due il `true`: una lista nuova dell'applicazione nasce col
  perimetro, non certificata, senza lineage.
* All'UPDATE, ogni cambio di valore, in un verso o nell'altro.

Un UPDATE che non tocca le tre colonne non fa partire il trigger. Se ne cambia più d'una, la frase
nomina la prima, nell'ordine dell'elenco qui sopra.

---

### ⭐ Perché un trigger e non un permesso di colonna

Togliere all'applicazione il diritto di scrivere le colonne sarebbe la difesa più forte, ma non
tiene: il giro dei permessi che gira a ogni migrazione riconsegna all'applicazione UPDATE su ogni
tabella dello schema, e la revoca verrebbe restituita. Su dbdev sembrerebbe funzionare fino alla
migrazione successiva; in CI, dove il database si ricostruisce da zero, non funzionerebbe mai.

Il trigger chiede se chi scrive è il proprietario della tabella al building block
[fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella), che lo legge dal
catalogo: nessun nome di ruolo è scritto a mano.

Sulle righe nate dal seed le stesse colonne sono anche colonne del software per il seed di primo
impianto; questo trigger le tiene su ogni riga.

---

### Codici errore

* `E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE` — l'applicazione scrive una dichiarazione alla nascita,
  o la cambia dopo. La frase porta la colonna e la lista.

---

### Test

* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — l'applicazione che dichiara `legge_lineage` alla
  nascita o porta `perimetro_emittente` a `false` è rifiutata; una lista nuova col perimetro di
  default passa.
* `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql` — gira come applicazione e lo verifica
  in testa; l'applicazione non accende il contrassegno né crea una lista già accesa.
* `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` — sulla lista creata
  dall'installazione a rifiutare `multi_emittente` è il trigger, prima del CHECK di coerenza.
* `db/pgtap/script/test-fn-is-proprietario-tabella-v1.sql` — l'applicazione che accende o spegne il
  contrassegno è rifiutata, e il trigger passa dal building block.

---

### Note di migrazione

* 2026-08-18 — nasce come `trgfn_lista_definizione_guard_multi_emittente`, insieme alla colonna; il
  piano di partenza era un permesso di colonna.
* 2026-09-25 — la domanda sul proprietario passa al building block `fn_is_proprietario_tabella`.
* 2026-11-21 — diventa il guard delle tre dichiarazioni, col nome nuovo: copre anche
  `perimetro_emittente` e la colonna nuova `legge_lineage`. Il codice
  `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` si ritira per `E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE`, che
  nomina la colonna.

---

{% include-markdown "signature-core.md" %}
