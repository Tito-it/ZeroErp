## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — la matrice che legge
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il gemello sulla matrice della natura
> * [anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) — il guard del ruolo
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo_su_contesto) — la check del ruolo, motivo del tipo di ruolo
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — gli obbligatori del ruolo, che conta solo se ammessi
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo` dice se un tipo di ruolo ammette un tipo d'indirizzo, un
dato giorno, secondo la sua matrice. È la sede unica della regola del tipo di ruolo, sullo strato degli
indirizzi del ruolo.

---

### Un predicato puro

Riceve il tipo di ruolo, il tipo d'indirizzo e il giorno, e non legge né il ruolo né i suoi indirizzi: lo
leggono tanto chi scrive un indirizzo sul ruolo quanto il picker di un ruolo che non esiste ancora. Il giorno lo
passa il chiamante; tutti i lettori passano il giorno operativo.

Il tipo di ruolo vuoto è ammesso, come il tipo di ruolo senza righe di matrice. Sul ruolo questa è solo metà
della regola: l'altra metà è la natura del soggetto del ruolo, che giudica il gemello. Chi lo legge chiede
sempre a tutti e due, prima questo.

---

### Chi lo legge

* il guard degli indirizzi del ruolo;
* la check su contesto del ruolo, e per suo tramite la madre e i due picker del ruolo;
* la regola degli indirizzi obbligatori del ruolo (`anagrafiche.fn_indirizzi_obbligatori_ruolo`), che conta
  come obbligatorio solo un tipo ammesso, e da cui la creazione degli obbligatori del ruolo legge che cosa
  copiare.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — su una matrice costruita: la riga attiva e valida,
  la riga scaduta, il tipo assente, il tipo di ruolo vuoto; il guard legge il predicato, non la matrice.
* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — il tipo di ruolo senza matrice: tutti i tipi
  ammessi.

---

### Note di migrazione

* 2026-11-15 — estratto dal guard degli indirizzi del ruolo, perché la stessa regola la leggano la check della
  madre, i picker e gli obbligatori.

---

{% include-markdown "signature-core.md" %}
