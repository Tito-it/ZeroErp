## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_nomi_tipo_indirizzo_richiesto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — le descrizioni dei tipi
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_indirizzi_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_soggetto) — la frase del livello soggetto
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — la frase del livello ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.fn_nomi_tipo_indirizzo_richiesto` compone i nomi di un tipo d'indirizzo richiesto e del suo ripiego
come li legge l'operatore: le descrizioni del catalogo fra caporali, nell'ordine tipo e ripiego, separate da una
barra.

---

### I nomi, non gli id

È il valore che la frase del rifiuto degli indirizzi obbligatori mostra al posto del tipo, sui due livelli: chi
legge «manca «Sede legale» / «Domicilio fiscale»» sa che cosa aggiungere, e sa che ne basta uno. Gli id
restano nel contesto dell'errore.

* Senza ripiego, o con un ripiego uguale al tipo, c'è il solo tipo.
* Un id che il catalogo non ha non compare; se non ne compare nessuno il risultato è vuoto, e il guard mette
  l'id del tipo al suo posto.

Il testo della frase sta in `config.messaggi_errore`; qui si compone solo il valore.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` — il solo tipo fra caporali, tipo e
  ripiego nell'ordine, il ripiego uguale al tipo, i due id assenti dal catalogo; poi la frase intera sui due
  livelli, composta dalle descrizioni del catalogo.

---

### Note di migrazione

* 2026-11-17 — nasce quando le frasi dei due rifiuti passano dagli id alle descrizioni.

---

{% include-markdown "signature-core.md" %}
