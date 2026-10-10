## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_default_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.trgfn_doc_guard_emittente_ba](/dbzero/script/manual/trgfn_doc_guard_emittente_ba)
>
[anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id)
>
Approfondimenti tabelle:
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Quando una commessa nasce senza emittente, glielo mette: quello **del suo
cliente**.

---

### Perche' conta davvero

Una commessa senza emittente non e' una commessa incompleta: e' una commessa
**invisibile**. L'emittente e' il dato con cui il sistema decide chi puo'
vederla, e senza di lui nessun operatore con un perimetro ristretto la trova —
ne' in lista, ne' nei cruscotti, ne' in fatturazione.

Prima di questa funzione il valore lo garantiva soltanto il fatto che la funzione
che lo calcola *si rifiuta di rispondere «non lo so»*: una proprieta' di un pezzo
di codice, non del dato.

---

### La differenza con i documenti

Sui documenti — ordini, preventivi, contratti, DDT — l'emittente di default si
prende **dall'operatore che li sta creando**: e' una persona davanti a un modulo,
e l'emittente e' quello per cui lavora.

La commessa no: **non la crea nessuno a mano**. Nasce quando un documento viene
spinto in fatturazione, quindi il suo emittente si prende **dal cliente**. E'
la stessa catena che decide su quale registro la fattura verra' numerata: «di chi
e' questa commessa» e «chi fattura questo cliente» sono la stessa domanda.

---

### Cosa non fa

**Non sovrascrive mai** un valore gia' scritto. Se chi crea la commessa dichiara
un emittente, questa funzione lo lascia stare: a giudicarlo ci pensa
[il controllo](/dbzero/script/manual/trgfn_doc_guard_emittente_ba), che lo
respinge se non coincide con quello del cliente.

E' una distinzione che sembra sottile e non lo e': una correzione silenziosa
farebbe passare una scrittura sbagliata **cambiandola**, e chi l'ha scritta non
saprebbe mai di aver sbagliato.

---

### Impatto e Vantaggi

* chi crea una commessa non deve piu' sapere niente di emittenti: il dato si
  ricava, e non si passa;
* le regole di visibilita' vengono valutate sul valore **vero**, perche' il
  riempimento avviene prima del controllo di perimetro — un dettaglio tecnico
  con un effetto concreto: una commessa creata da un operatore con perimetro
  ristretto non viene piu' respinta per un campo vuoto.
