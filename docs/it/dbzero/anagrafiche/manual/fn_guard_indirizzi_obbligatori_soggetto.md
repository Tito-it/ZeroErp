## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto giudicato, con la sua natura
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — i suoi indirizzi
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto) — che cosa manca
> * [anagrafiche.fn_nomi_tipo_indirizzo_richiesto](/dbzero/anagrafiche/funzioni/fn_nomi_tipo_indirizzo_richiesto) — i nomi della frase
> * [anagrafiche.trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required) — chi lo chiama quando si scrive il soggetto
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_obbligatori_soggetto) — chi lo chiama quando un indirizzo se ne va
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — il gemello del livello ruolo

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_indirizzi_obbligatori_soggetto` rifiuta un soggetto che non ha tutti gli indirizzi che la
sua natura dichiara obbligatori, nel giorno aziendale. È la sede unica del controllo del livello soggetto.

---

### Come giudica

* Legge la natura del soggetto e chiede i mancanti a `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto` su
  quella natura.
* Al primo mancante, per id del tipo, rifiuta: la frase nomina la natura e il tipo richiesto col suo ripiego, per
  descrizione; se una descrizione manca, al suo posto va l'id. Dice un mancante alla volta: l'elenco intero lo
  dà `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`.
* Un soggetto senza natura non deve avere niente; un soggetto che non c'è più, cancellato nella stessa
  transazione coi suoi indirizzi, non si giudica.
* Un id assente è una chiamata sbagliata, non un soggetto da giudicare.

Il `tx_id` che riceve va al log dell'errore. Gira coi permessi di chi scrive: le tabelle che legge non hanno
sicurezza di riga.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il requisito che cambia non rigiudica.** Una riga della matrice della natura che diventa obbligatoria, o
  entra nella sua validità, non tocca i soggetti che esistono: il rifiuto arriva alla loro prossima scrittura,
  in qualunque colonna.
* **La frase può proporre un ripiego che il soggetto non può avere.** Il ripiego della riga non si confronta con
  la natura (vedi [fn_indirizzi_obbligatori_mancanti_soggetto](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto)).

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` — al soggetto manca un indirizzo che la natura chiede. Il
  contesto porta il soggetto, la natura, il tipo richiesto e il ripiego.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — chiamato senza l'id del soggetto.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — chiamato da solo: il
  soggetto che non esiste tace, l'id assente è una chiamata non valida; i due trigger che lo chiamano senza
  copie della regola; la società a cui la cancellazione o il cambio di tipo tolgono la sede legale, rifiutata, e
  la sostituzione nella stessa transazione, che passa.
* `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` — il codice del livello soggetto e la
  frase intera, con e senza ripiego.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — il guard che legge i mancanti.

---

### Note di migrazione

* 2026-11-17 — nasce come sede unica del controllo del soggetto, chiamata anche dal trigger della cancellazione
  di un indirizzo; prima il controllo stava nel solo trigger della scrittura del soggetto, e sollevava lo stesso
  codice del livello ruolo.

---

{% include-markdown "signature-core.md" %}
