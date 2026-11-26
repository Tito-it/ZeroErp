## 📘 Documentazione Concettuale – Funzione `magazzino.fn_guard_magazzino_nel_perimetro`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — il magazzino che controlla
>
> Approfondimento funzioni:
>
> * [script.fn_scope_ef_whitelist_via_magazzino](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_magazzino) — il predicato della policy
> * [magazzino.fn_aggiungi_ubicazione](/dbzero/magazzino/funzioni/fn_aggiungi_ubicazione) — un verbo che lo usa

---

### 🎯 Scopo Principale

Il guard dei verbi che fanno nascere qualcosa **dentro un magazzino** (un'ubicazione, la testata di un documento interno): il magazzino deve esistere ed essere dell'azienda dell'operatore.

---

### Perché serve

Il verbo gira come il proprietario delle tabelle, e lì la sicurezza per riga non filtra: senza questo controllo un operatore potrebbe far nascere un'ubicazione in un magazzino di un'altra azienda, e la risposta direbbe che quel magazzino esiste. Il guard usa lo stesso predicato della policy, e risponde «non trovato» in tutti e due i casi.

---

### Che cosa non fa

Non controlla il permesso: lo ha già fatto il verbo. Il rifiuto è della porta che lo chiama, che gli passa il proprio nome.

---

### Codici errore

* `E_MAG_MAGAZZINO_NON_TROVATO` — il magazzino non esiste o è di un'altra azienda.

---

### Test

`db/pgtap/magazzino/test-verbi-documenti-interni-v1.sql` e `db/pgtap/magazzino/test-verbi-anagrafiche-magazzino-v1.sql`.

---

### Note di migrazione

* 2026-11-23 — nasce dalla copia dello stesso controllo in `magazzino.fn_aggiungi_ubicazione`, che si ritira nello stesso giro (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "signature-core.md" %}
