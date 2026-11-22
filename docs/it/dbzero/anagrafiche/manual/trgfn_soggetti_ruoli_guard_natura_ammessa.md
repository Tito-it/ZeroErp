## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — la tabella su cui è montato
> * [config.tipi_ruoli_nature_ammesse](/dbzero/config/tabelle/tipi_ruoli_nature_ammesse) — la matrice dei tipi di ruolo per macro-tipologia
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — da cui si risale alla macro-tipologia del soggetto
> * [config.tipi_soggetto](/dbzero/config/tabelle/tipi_soggetto) — le macro-tipologie
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) — lo stesso schema «matrice assente, nessun vincolo» per gli indirizzi del ruolo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa` rifiuta un ruolo che la macro-tipologia del soggetto
non ammette: un ruolo che vale solo per le persone giuridiche non si dà a un privato, quello della risorsa
umana non si dà a una società.

---

### La matrice è per macro-tipologia

La matrice `config.tipi_ruoli_nature_ammesse` lega i tipi di ruolo alle **macro-tipologie** (persona fisica,
persona giuridica, ente), non alle nature di dettaglio: il guard risale dalla natura del soggetto alla sua
famiglia e cerca la coppia.

* **Un tipo di ruolo senza righe nella matrice è libero**: lo può avere qualunque soggetto, anche senza
  natura.
* **Un tipo di ruolo con righe nella matrice** ammette solo le macro-tipologie che hanno una riga attiva e
  valida nel giorno operativo. Basta una riga qualunque, anche spenta o scaduta, perché il tipo non sia più
  libero: un tipo le cui righe sono tutte spente non lo ammette più nessuno.
* **Un soggetto senza natura** non può avere un ruolo che ha una matrice: non c'è niente da confrontare.

---

### Quando scatta

Prima della nascita del ruolo e prima di ogni modifica del suo tipo. Il soggetto del ruolo non si cambia
(`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`), quindi non c'è un'altra strada dalla parte del ruolo.

Dalla parte del soggetto, un cambio di natura resta nella stessa macro-tipologia (la regola del cambio di
natura rifiuta le altre), e la risposta della matrice non cambia: il guard non ha bisogno di rigirare.

---

### ⚠️ Che cosa oggi non copre

* **La natura vuota come passaggio.** Un soggetto portato a nessuna natura e poi a una natura di un'altra
  macro-tipologia tiene i suoi ruoli senza che nessuno li ricontrolli: il guard scatta solo quando si scrive
  il ruolo.
* **Una riga della matrice che si spegne o scade** non tocca i ruoli che già ci sono: vale per i ruoli che
  nascono dopo.
* **La frase dice gli id, non i nomi.** I due rifiuti riempiono la frase con l'id della macro-tipologia, del
  tipo di ruolo e del soggetto, invece dei loro nomi, e il contesto non nomina un campo da evidenziare nel
  form.

---

### Codici errore

* `E_RUOLO_NATURA_NON_AMMESSA` — la macro-tipologia del soggetto non è fra quelle ammesse dal tipo di ruolo.
* `E_RUOLO_NATURA_TIPO_DET_NULL` — il tipo di ruolo ha una matrice e il soggetto non ha natura.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-ruoli-guard-natura-ammessa.sql` — persona giuridica ammessa e persona
  fisica rifiutata per il gestore, il contrario per la risorsa umana, persona fisica ed ente ammessi per il
  cliente, il soggetto senza natura rifiutato.

---

{% include-markdown "signature-core.md" %}
