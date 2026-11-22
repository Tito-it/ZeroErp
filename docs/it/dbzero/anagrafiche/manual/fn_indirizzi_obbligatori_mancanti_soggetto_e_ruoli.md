## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli del soggetto
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto) — i mancanti del soggetto
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_ruolo) — i mancanti di ogni ruolo
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — gli indirizzi che la natura nuova vieta
> * [anagrafiche.fn_nature_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_nature_proponibili_soggetto) — le nature fra cui scegliere

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli` elenca gli indirizzi obbligatori che una natura
chiede e che un soggetto non ha, sul soggetto e su ognuno dei suoi ruoli: è la lista di ciò che il form del
cambio di natura deve chiedere.

---

### Che cosa dà da chiedere

* **Prima il soggetto**, con ruolo e tipo di ruolo vuoti; **poi i ruoli**, in ordine di id; dentro ciascuno, per
  tipo richiesto. Ogni riga porta il tipo richiesto e il ripiego che basterebbe al suo posto.
* **La natura è quella proposta**, passata da chi chiama; con quella di oggi la lista dice che cosa manca adesso.
  La natura non ha un default: assente vuol dire che non conta, e sul soggetto non chiede niente.
* **Il giorno è quello aziendale**, lo stesso dei guard.

Un soggetto che non esiste non ha righe. La funzione non legge altro che i due mancanti, che sono le letture dei
guard: ciò che la lista chiede di dare è ciò che i guard pretendono al COMMIT. Il form manda questi indirizzi
nello stesso salvataggio del cambio, scritti dopo la natura.

Nessun oggetto del database la chiama: è la lettura dell'applicazione.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — la lettura composta dai due mancanti; su
  righe costruite (un tipo obbligatorio per il fornitore e vietato al privato, uno obbligatorio per la ditta):
  la natura di oggi sul soggetto completo, la natura proposta che chiede un indirizzo al ruolo e uno al
  soggetto, il ripiego, la natura assente, il soggetto che non esiste; poi il salvataggio come lo fa
  l'applicazione, rifiutato senza l'indirizzo del ruolo e accettato con tutti quelli elencati.

---

### Note di migrazione

* 2026-11-17 — nasce per il form del cambio di natura, che porta con sé gli indirizzi nello stesso salvataggio.

---

{% include-markdown "signature-core.md" %}
