## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_guard_istanza_del_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi del ruolo, anche per una sola istanza
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — i conti del ruolo, anche per una sola istanza
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_istanza_di_altro_soggetto) — la domanda che pone
> * [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_contesto_soggetto) — la stessa regola sui contatti
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — chi crea l'indirizzo di un ruolo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_guard_istanza_del_ruolo` rifiuta un indirizzo o un conto del ruolo che nomina l'istanza
di un altro soggetto: l'istanza della riga deve essere del soggetto del suo ruolo.

---

### Perché

Un indirizzo del ruolo vale per tutto il ruolo o per una sola istanza, e la ricerca degli indirizzi scende
dall'istanza al ruolo al soggetto. Una riga sul ruolo di un soggetto con l'istanza di un altro darebbe a un
soggetto l'indirizzo dell'altro. Lo stesso vale per i conti bancari del ruolo. Un corpo solo è montato sulle
due tabelle, prima della scrittura di ogni riga, per chiunque scriva.

---

### Quando giudica

* A ogni nascita di una riga con un'istanza.
* In modifica, solo se cambiano il ruolo o l'istanza: le righe di prima restano valide finché nessuno le
  tocca.
* Una riga senza istanza vale per tutto il ruolo: niente da giudicare.

L'altra porta, cambiare il soggetto dell'istanza o del ruolo, è chiusa dai blocchi di colonna
`E_ISTANZA_SOGGETTO_IMMUTABILE` ed `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`.

---

### Codici errore

* `E_ISTANZA_ALTRO_SOGGETTO` — l'istanza è di un altro soggetto. Il campo dell'errore è
  `istanza_utility_id`; nella frase c'è il codice dell'istanza.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` — i guard montati; sugli indirizzi e sui
  conti del ruolo l'istanza di un altro soggetto rifiutata, quella dello stesso soggetto e la riga senza
  istanza che passano, il cambio dell'istanza o del ruolo verso un altro soggetto rifiutato.

---

### Note di migrazione

* 2026-10-19 — nasce su richiesta del backend, per gli indirizzi e i conti del ruolo legati a un'istanza.

---

{% include-markdown "signature-core.md" %}
