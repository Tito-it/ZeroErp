## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_guard_emittente_ba`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[vendite.trgfn_commesse_default_emittente](/dbzero/vendite/manual/trgfn_commesse_default_emittente)
>
[anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
>
Approfondimenti tabelle:
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Verifica che l'emittente scritto su una commessa sia **esattamente quello che si
ricava dal suo cliente**, e blocca la scrittura se non lo e'.

---

### Perche' conta davvero

L'emittente della commessa non e' un attributo fra gli altri: e' **la chiave con
cui il sistema decide chi puo' vedere quella commessa**. Ci si appoggiano le
regole di visibilita' della tabella, il filtro dei cruscotti e il giornale degli
eventi.

Se quel valore e' sbagliato — o manca — la commessa non da' errore e non compare
a video sbagliata: **sparisce**. Il lavoro resta nel database, non lo vede
nessuno, e non viene mai fatturato. Una lista che non mostra una riga ha lo
stesso aspetto di una lista in cui quella riga non c'e'.

---

### Da dove viene il valore giusto

Dal **cliente**, sempre. La commessa non la compila una persona in un modulo:
nasce quando un documento viene spinto in fatturazione, e l'emittente si ricava
dal cliente di quel documento. Chi scrive non deve sceglierlo: se lo lascia
vuoto, lo mette [il riempitore](/dbzero/vendite/manual/trgfn_commesse_default_emittente);
se lo scrive diverso, questo controllo lo respinge.

---

### Perche' guarda solo due colonne

Il controllo scatta alla creazione e quando si tocca **il cliente o l'emittente**,
non a ogni modifica.

Non e' pigrizia: e' quello che tiene le commesse **modificabili**. Se il
controllo girasse a ogni modifica, il giorno in cui un cliente venisse spostato
su un altro emittente ogni sua commessa diventerebbe intoccabile — con un
messaggio che parla di una colonna che nessuno stava cambiando. Quel caso ha il
suo presidio, ed e' altrove: si impedisce lo spostamento del cliente, non si
congela il lavoro.

---

### Impatto e Vantaggi

* vale per **chiunque scriva**, non solo per la funzione che crea le commesse:
  il vincolo non sa chi lo scrive, e nel progetto ci sono decine di punti che
  scrivono su questa tabella direttamente;
* estende di un anello una famiglia che esisteva gia' su ordini, preventivi,
  contratti, DDT, offerte e resi: la commessa era **l'unica** che portava un
  emittente senza avere ne' il riempitore ne' il controllo;
* nessuna eccezione per i dati preesistenti e nessun interruttore di
  disattivazione.
