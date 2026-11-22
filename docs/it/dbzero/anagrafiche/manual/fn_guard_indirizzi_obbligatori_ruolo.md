## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo giudicato
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — i suoi indirizzi
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_ruolo) — che cosa manca
> * [anagrafiche.fn_nomi_tipo_indirizzo_richiesto](/dbzero/anagrafiche/funzioni/fn_nomi_tipo_indirizzo_richiesto) — i nomi della frase
> * [anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_indirizzi_required) — chi lo chiama quando si scrive il ruolo
> * [anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_obbligatori_ruolo) — chi lo chiama quando un indirizzo se ne va
> * [anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_obbligatori_ruoli) — chi lo chiama quando cambia la natura
> * [anagrafiche.fn_guard_indirizzi_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_soggetto) — il gemello del livello soggetto

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_indirizzi_obbligatori_ruolo` rifiuta un ruolo che non ha tutti gli indirizzi che il suo
tipo di ruolo chiede sulla natura del soggetto, nel giorno aziendale. È la sede unica del controllo del livello
ruolo.

---

### Come giudica

* Legge il tipo del ruolo e la natura del suo soggetto, e chiede i mancanti a
  `anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo` su quella natura.
* Al primo mancante, per id del tipo richiesto, rifiuta: la frase nomina il ruolo e il tipo richiesto col suo
  ripiego, per descrizione; se una descrizione manca, al suo posto va l'id. Dice un mancante alla volta:
  l'elenco intero, da chiedere prima di salvare, lo dà
  `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`.
* Un ruolo che non c'è più, cancellato nella stessa transazione coi suoi indirizzi, non si giudica.
* Un id assente o non positivo è una chiamata sbagliata, non un ruolo da giudicare.

Il `tx_id` che riceve va al log dell'errore. Gira coi permessi di chi scrive: le tabelle che legge non hanno
sicurezza di riga.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il requisito che cambia non rigiudica.** Una riga della matrice che diventa obbligatoria, o entra nella sua
  validità, non tocca i ruoli che esistono: il rifiuto arriva alla loro prossima scrittura, in qualunque colonna.

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` — al ruolo manca un indirizzo che il requisito chiede. Il contesto porta
  il ruolo del soggetto, il tipo di ruolo, la natura, il tipo richiesto e il ripiego.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — chiamato senza un id di ruolo valido.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — chiamato da solo: il ruolo
  che non esiste tace, l'id assente è una chiamata non valida; i tre trigger che lo chiamano senza copie della
  regola; la cancellazione e il cambio di tipo dell'unica fatturazione rifiutati, il ripiego che la lascia
  cancellare, la sostituzione nella stessa transazione e il ruolo cancellato coi suoi indirizzi che passano.
* `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` — la frase intera, con e senza ripiego.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — il guard che legge i mancanti.

---

### Note di migrazione

* 2026-11-17 — nasce come sede unica del controllo del ruolo, chiamata dai tre trigger delle strade che possono
  togliere un obbligatorio; prima il controllo stava nel solo trigger della scrittura del ruolo.

---

{% include-markdown "signature-core.md" %}
