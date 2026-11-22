## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_istanza_di_altro_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il soggetto dell'istanza, che non cambia
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_ruolo_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_ruolo_di_altro_soggetto) — la stessa domanda per il ruolo
> * [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/funzioni/trgfn_guard_istanza_del_ruolo) — il guard di indirizzi e conti del ruolo
> * [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_contesto_soggetto) — il guard dei contatti
> * [anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza) — il guard del billing account
> * [pratiche.trgfn_pratiche_guard_contesto](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_contesto) — il guard delle pratiche

---

### 🎯 Scopo Principale

`anagrafiche.fn_istanza_di_altro_soggetto` risponde alla domanda «questa istanza è di un altro soggetto?»:
restituisce il soggetto dell'istanza quando non è quello dato, e niente altrimenti.

---

### Che cosa risponde

| Caso | Risposta |
| --- | --- |
| L'istanza è del soggetto dato | nessun valore |
| L'istanza è di un altro soggetto | il soggetto dell'istanza |
| Nessuna istanza, o nessun soggetto | nessun valore: non c'è niente da confrontare |
| Un'istanza che non esiste | nessun valore: la rifiuta la chiave esterna della tabella che la nomina |

---

### ⭐ Una domanda, non un controllo

Una riga che porta un'istanza (un indirizzo, un contatto, un conto, un billing account, una pratica) deve
portare un'istanza del suo soggetto, altrimenti il dato di un soggetto finisce a un altro. La funzione non
rifiuta: il rifiuto lo dà chi la chiama, col suo codice e il suo campo. Per questo la stessa regola risponde
con codici diversi su tabelle diverse.

Basta guardare la riga che si scrive perché il soggetto dell'istanza non cambia
(`E_ISTANZA_SOGGETTO_IMMUTABILE`).

---

### Test

* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` — i quattro casi: stesso soggetto, altro
  soggetto, istanza assente, soggetto assente.

---

### Note di migrazione

* 2026-10-19 — nasce dal confronto che il guard del billing account e quello delle pratiche scrivevano
  ciascuno a mano.

---

{% include-markdown "signature-core.md" %}
