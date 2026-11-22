## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — le righe obbligatorie della natura, col ripiego
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi del soggetto che le soddisfano
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — la riga attiva e valida
> * [anagrafiche.fn_guard_indirizzi_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_soggetto) — il guard, che la legge sulla natura del soggetto
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli) — la lettura del form, sulla natura proposta
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_ruolo) — la gemella del livello ruolo

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto` restituisce gli indirizzi obbligatori che mancano a un
soggetto su una natura data, in un giorno dato: le righe obbligatorie della matrice della natura per cui il
soggetto non ha né un indirizzo del tipo né uno del ripiego.

---

### La natura è un parametro

Come la gemella del ruolo, giudica la natura **passata**, non quella del soggetto: il guard le passa quella che
il soggetto ha, la lettura del form quella che un cambio propone. Una riga conta se è obbligatoria, attiva e
valida nel giorno dato. Un soggetto che non esiste, o una natura assente, non hanno mancanti. Le righe sono
ordinate per tipo: la prima è quella che il guard solleva.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il ripiego del soggetto non si confronta con la natura.** A differenza del livello ruolo, il ripiego della
  riga vale com'è scritto: non si chiede se la natura lo ammetta. Un ripiego che la natura non ammette non si
  può scrivere sul soggetto (lo ferma il guard del tipo,
  [trgfn_indirizzi_soggetti_guard_tipo_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_tipo_indirizzo)),
  ma la funzione lo restituisce come alternativa e la frase del rifiuto lo propone.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — il guard che legge questa funzione; il
  soggetto completo, il tipo chiesto dalla natura proposta, il ripiego riportato, la natura assente e il
  soggetto che non esiste (niente).

---

### Note di migrazione

* 2026-11-17 — nasce estraendo dal guard la domanda «che cosa manca», per darla anche al form del cambio di
  natura.

---

{% include-markdown "signature-core.md" %}
