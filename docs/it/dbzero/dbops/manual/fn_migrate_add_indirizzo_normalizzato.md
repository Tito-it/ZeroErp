## 📘 Documentazione Concettuale – Funzione `dbops.fn_migrate_add_indirizzo_normalizzato`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — la tabella a cui aggiungeva la colonna
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) — chi scrive oggi l'indirizzo normalizzato
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — la regola di oggi con cui si compone

---

### 🎯 Scopo Principale

Utility di migrazione una tantum: aggiungeva a `anagrafiche.indirizzi_dettaglio` la colonna
`indirizzo_normalizzato`, se non c'era ancora. Oggi non ha chiamanti, e non ha più un lavoro.

---

### ⛔ Una regola vecchia, che non è più quella del database

La funzione crea la colonna come **colonna generata**, con una sua formula di composizione (via,
civico, palazzina, scala, piano, interno, con le loro etichette). Non è più così che la colonna
vive: oggi `indirizzo_normalizzato` è una colonna normale, scritta dal trigger
`anagrafiche.trgfn_indirizzi_dettaglio_normalize`, che delega tutta la regola a
`anagrafiche.fn_build_indirizzo_normalizzato`.

⇒ Sul database di oggi la funzione non fa niente, perché la colonna esiste. Su una tabella senza
quella colonna rifarebbe la colonna con la formula vecchia, che diverge da quella di oggi: è una
seconda copia della regola, ferma al giorno in cui è stata scritta.

---

### Chi la chiama

Nessuno: né un changeSet, né il backend, né un test. È nel baseline e basta.

⇒ È una candidata al ritiro.

---

### Codici errore

Nessuno.

---

{% include-markdown "signature-core.md" %}
