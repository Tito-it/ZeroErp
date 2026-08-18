## 📘 Documentazione Concettuale – View `dbops.vw_liste_multi_emittente_non_certificate`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione)
>
[ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Elenca le liste che **dichiarano** di saper reggere piu' emittenti senza
mostrarne nessuno nelle righe.

> ⚠️ **Deve restare a zero righe.** Una riga qui e' una lista con l'etichetta
> «collaudato» addosso e nessun collaudo dietro.

---

### La regola che presidia

> **Una lista puo' dichiararsi multi-emittente solo se espone l'emittente nella
> riga.**

E' cio' che rende il contrassegno una **regola** e non un adesivo. Senza,
qualcuno lo accende per far sparire un fastidio, e da quel momento la lista
mescola emittenti senza dirlo — cioe' proprio il difetto che doveva impedire.

Con il controllo, il contrassegno diventa qualcosa che si **guadagna** facendo
un lavoro.

---

### Perche' e' un controllo di solo catalogo

Guarda unicamente la configurazione delle liste e delle loro colonne: non sa
niente delle viste dei dati ne' del programma che le mostra. E' un limite
dichiarato, ed e' anche il motivo per cui e' onesto e leggero.

**Non prova che la colonna arrivi a video** — per le liste che compongono le
righe nel programma applicativo quello dipende da un'altra meta' del lavoro.
Prova che qualcuno l'abbia almeno **dichiarata**, che e' la meta' verificabile
da qui.

---

### Come si legge il numero

Il contrassegno nasce spento su tutte le liste: e' un **registro di debito che
deve calare**, non un elenco di eccezioni che cresce. Il giorno in cui lo si
volesse accendere in blocco vorrebbe dire che ha smesso di significare qualcosa.
