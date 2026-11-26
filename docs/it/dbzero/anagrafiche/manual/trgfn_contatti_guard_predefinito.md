## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_contatti_guard_predefinito`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_contatti_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_set_default_contatto) — il gemello che mette il segno del predefinito
> * [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_contesto_soggetto) — l'altro guard della stessa fase
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto col codice e il campo
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il contatto predefinito nel modello dei contatti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_contatti_guard_predefinito` impedisce che un contesto (soggetto, ruolo, istanza) che ha
contatti resti senza predefinito. Il predefinito non perde il segno e non esce dal contesto finché nel contesto
restano altri contatti: chi vuole cambiarlo marca un altro contatto.

Il database non promuove nessuno da solo: sceglierebbe per ordine di nascita, non per chi è davvero il referente.

---

### Quando scatta

Prima di ogni modifica e di ogni cancellazione di `anagrafiche.contatti`, montato come
`trg_contatti_a10_guard_predefinito_upd_dlt` (fase `a10`, guard). Nella stessa fase, in ordine di nome, gira prima
il guard del contesto del soggetto: un ruolo o un'istanza di un altro soggetto si rifiutano per primi.

Non giudica:

* una riga che non è il predefinito;
* una scrittura fatta da un altro trigger: il segno tolto dal trigger del predefinito quando un altro contatto
  diventa predefinito, e la cancellazione in cascata del soggetto.

Una scrittura diretta (applicazione, import, test) è sempre giudicata.

---

### Che cosa rifiuta

* **Il segno tolto.** Una modifica che lascia il predefinito nel suo contesto e mette `is_default` a `false` è
  rifiutata. Il segno non si toglie: passa a un altro contatto, marcandolo.
* **Il predefinito che esce dal contesto.** Cancellare il predefinito, o portarlo in un altro contesto (cambiando
  soggetto, ruolo o istanza), è rifiutato quando nel suo contesto restano altri contatti. Prima si marca un altro
  contatto, poi si cancella o si sposta questo.

L'ultimo contatto del contesto si cancella e si sposta: il contesto resta senza contatti, quindi senza predefinito.

---

{% include-markdown "it/dbzero/anagrafiche/_contatto-predefinito.md" %}

---

### Codici errore

* `E_CONTATTO_PREDEFINITO_OBBLIGATORIO` — il segno tolto al predefinito restando nel contesto; campo `is_default`.
  Il messaggio porta il nominativo del contatto.
* `E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE` — il predefinito cancellato o spostato mentre nel suo contesto restano
  altri contatti; campo `is_default`. Il messaggio porta il nominativo del contatto.

---

### Test

* `db/pgtap/anagrafiche/test-contatto-predefinito-per-contesto-v1.sql` (test 6-10) — il segno tolto all'unico
  predefinito rifiutato, la modifica di un altro contatto che non sposta il segno, la cancellazione del predefinito
  con un altro accanto rifiutata, il vecchio predefinito che si cancella dopo aver marcato l'altro, l'ultimo
  contatto del contesto che si cancella.

---

### Note di migrazione

* 2026-11-25 — nasce insieme al predefinito per riga di contesto, col suo montaggio (`20261125-36`).

---

{% include-markdown "signature-core.md" %}
