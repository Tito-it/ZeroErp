## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_flag_etichetta`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_colonne_struttura](/dbzero/catalogo/funzioni/fn_articolo_colonne_struttura) — le colonne strutturali di cui dà il nome
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard dell'uso, che la legge
> * [catalogo.trgfn_articoli_guard_onere_natura](/dbzero/catalogo/funzioni/trgfn_articoli_guard_onere_natura) — il guard degli oneri, che la legge
> * [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/funzioni/fn_articolo_correggi_struttura) — la porta della struttura, che la legge

---

### 🎯 Scopo Principale

Dà il **nome che l'operatore riconosce** di una colonna strutturale dell'articolo: «composito»,
«solo componente», «natura di vendita», «causale onere», «tipologia di listino», «gestito a
magazzino», «gestito a lotti», «gestito a matricola». Per un'altra colonna non risponde niente.

Va nei valori dei messaggi d'errore al posto del nome tecnico della colonna, che resta nel
contesto (`campo`) per il frontend.

---

### ⭐ Un nome, una sede

Lo stesso elenco «colonna → nome leggibile» era scritto in due guard dell'articolo, quello
dell'uso e quello degli oneri. Alla seconda copia si è estratto qui; lo legge anche la porta
della struttura, per dire quale valore non va.

---

### Come è fatta

`LANGUAGE sql`, `IMMUTABLE`: una tabella di corrispondenze fissa, senza letture.

---

### Test

* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — il nome leggibile nella frase
  della porta (valore del tipo sbagliato, valore vuoto).

---

### Note di migrazione

* 2026-11-09 — nasce dalle due copie nei guard dell'articolo (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
