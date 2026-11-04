## 📘 Documentazione Concettuale – Vista `dbops.vw_liste_multi_emittente_non_certificate`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — le liste e il loro contrassegno `multi_emittente`
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — le colonne dichiarate di ogni lista
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento funzioni:
>
> * [ui.trgfn_lista_definizione_guard_multi_emittente](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_multi_emittente) — il contrassegno si scrive solo dal proprietario della tabella
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Le liste che **dichiarano** di saper reggere più emittenti senza mostrarne nessuno nelle righe.
Deve restare vuota: una riga è una lista con l'etichetta «collaudato» addosso e nessun collaudo
dietro.

---

### La regola che presidia

> **Una lista può dichiararsi multi-emittente solo se espone l'emittente nella riga.**

È ciò che rende il contrassegno una **regola** e non un adesivo. Senza, qualcuno lo accende per
far sparire un fastidio, e da quel momento la lista mescola emittenti senza dirlo: proprio il
difetto che doveva impedire. Con il controllo, il contrassegno si **guadagna** facendo un lavoro.

Una lista è in regola quando almeno una sua colonna **attiva** legge un campo il cui nome comincia
con `emittent`. Il contrassegno lo guarda su tutte le liste, anche quelle spente: la colonna
`lista_attiva` dice se la lista è in uso.

---

### Perché è un controllo di solo catalogo

Guarda unicamente la configurazione delle liste e delle loro colonne: non sa niente delle viste
dei dati né del programma che le mostra. È un limite dichiarato, ed è anche il motivo per cui è
onesto e leggero.

⚠️ **Non prova che la colonna arrivi a video**: per le liste che compongono le righe nel programma
quello dipende da un'altra metà del lavoro. Prova che qualcuno l'abbia almeno **dichiarata**, che
è la metà verificabile da qui.

---

### Come si legge il numero

Il contrassegno nasce spento su tutte le liste, e si scrive solo dal proprietario della tabella,
cioè dalle migrazioni: l'applicazione non lo può accendere. Il giorno in cui lo si volesse
accendere in blocco vorrebbe dire che ha smesso di significare qualcosa.

A catalogo è `ZERO`, `SETTIMANALE`, perimetro `LIBERO`: il catalogo delle liste non ha un perimetro
per operatore, e chi deve agire è lo sviluppo.

---

### Test

* `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql`, test 6 — la vista è a zero righe.
* `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` e
  `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`, test 11 — dopo che quelle liste hanno acceso
  il contrassegno, la vista resta a zero righe.

---

### Note di migrazione

* 2026-08-18 — nasce col perimetro dell'emittente, come controllo automatico della regola P-2b
  (`brief perimetro-emittente` §7, decisione 3).

---

{% include-markdown "signature-core.md" %}
