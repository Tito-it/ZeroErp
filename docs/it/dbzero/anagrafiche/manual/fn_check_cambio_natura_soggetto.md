## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_cambio_natura_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto di cui cambia la natura
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — le nature, con la macro-tipologia, il formato della partita IVA e la policy dei dati societari
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_guard_cambio_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cambio_natura) — il guard che solleva il primo motivo
> * [anagrafiche.fn_nature_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_nature_proponibili_soggetto) — il picker delle nature, sulla stessa regola
> * [anagrafiche.fn_soggetto_primo_documento](/dbzero/anagrafiche/funzioni/fn_soggetto_primo_documento) — il documento che blocca il cambio d'identità fiscale
> * [anagrafiche.fn_titoli_iva_non_ammessi](/dbzero/anagrafiche/funzioni/fn_titoli_iva_non_ammessi) — i titoli IVA visibili che la natura nuova non ammette
> * [anagrafiche.fn_titoli_iva_non_ammessi_conta](/dbzero/anagrafiche/funzioni/fn_titoli_iva_non_ammessi_conta) — quanti sono in tutto
> * [anagrafiche.fn_regime_pa_campo_non_ammesso](/dbzero/anagrafiche/funzioni/fn_regime_pa_campo_non_ammesso) — il predicato dei flag del regime PA
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il predicato degli indirizzi
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, la natura e i ruoli

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_cambio_natura_soggetto` dice perché un soggetto non può passare a una natura di
dettaglio: restituisce l'elenco ordinato dei motivi, vuoto quando il cambio si può fare o quando la natura
non cambia. Non scrive e non solleva niente sul cambio: il rifiuto è del guard, la proposta è del picker.

---

### ⭐ La sede unica della regola

La regola del cambio di natura sta qui e solo qui. La leggono il guard su `anagrafiche.soggetti`, che solleva
il primo motivo, e il picker `anagrafiche.fn_nature_proponibili_soggetto`, che spegne le nature che hanno
motivi: per costruzione il picker propone ciò che il guard accetta. La regola, con l'elenco dei motivi e chi
controlla il resto, è nel blocco qui sotto.

Ogni motivo porta il **codice** dell'errore, il **motivo macchina** e la sua chiave di traduzione (che il
frontend usa per spiegare la natura spenta), il **dettaglio** (soggetto, natura proposta, il campo da
evidenziare nel form e, secondo il motivo, quanti titoli o indirizzi) e i **valori** della frase.

---

### I valori proposti e quelli salvati

* La **natura di partenza** è quella salvata del soggetto, la **natura nuova** quella passata.
* **Partita IVA, cliente PA e split payment** sono quelli passati, cioè i valori che il salvataggio porta:
  chi li corregge insieme alla natura non ha il motivo. Il guard passa i valori della riga nuova, il picker
  quelli salvati.
* Una natura nuova che non esiste non ha motivi: la rifiuta la chiave esterna.
* Il **giorno** con cui si giudicano titoli e indirizzi è il giorno operativo.

---

### Chi vede che cosa

La funzione gira coi permessi di chi la chiama. I titoli IVA hanno la visibilità per azienda: il motivo dei
titoli visibili conta e nomina quelli che chi agisce vede; il motivo dei titoli di altre aziende nasce dalla
differenza con il conteggio totale, letto sopra la visibilità. Anche i documenti si cercano sopra la
visibilità: un documento di un'altra azienda blocca, e il motivo ne dice solo il tipo.

---

{% include-markdown "it/dbzero/anagrafiche/_cambio-di-natura.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il passaggio per la natura vuota aggira i due motivi che non si tolgono.** Verso nessuna natura la
  funzione guarda solo i titoli IVA, e da nessuna natura non guarda né la macro-tipologia né i documenti.
  Due salvataggi, anche nella stessa transazione (prima la natura vuota, poi quella nuova), portano una
  società a privato o una ditta con documenti a privato senza nessuno dei due rifiuti. Gli altri motivi
  restano: si giudicano sulla natura d'arrivo.
* **La natura ammessa dei ruoli non è un motivo.** Che un ruolo sia ammesso per la macro-tipologia del
  soggetto lo controlla solo il guard dei ruoli, quando il ruolo si scrive. Restando nella stessa
  macro-tipologia il caso non si presenta; passando per la natura vuota sì, e un ruolo ammesso solo per le
  persone giuridiche resta su una persona fisica.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il soggetto non è passato.
* `E_SOGGETTO_NOT_FOUND` — il soggetto non esiste.

I codici dei motivi (quelli del blocco) la funzione non li solleva: li restituisce.

---

### Test

* `db/pgtap/anagrafiche/test-cambio-natura-soggetto-v1.sql` — la regola su casi costruiti: la natura che non
  cambia, l'altra macro-tipologia da sola, i documenti con una natura senza partita IVA costruita apposta, la
  partita IVA proposta o tolta, il soggetto mancante o non passato.
* `db/pgtap/anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.sql` — i titoli non ammessi, anche quelli di
  un'altra azienda.
* `db/pgtap/anagrafiche/test-soggetti-regime-pa-v1.sql` — i flag del regime PA dentro la stessa
  macro-tipologia.
* `db/pgtap/anagrafiche/test-fn-elimina-dati-societari-v1.sql` — il motivo dei dati societari, che sparisce
  dopo l'eliminazione.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — il motivo degli indirizzi del ruolo, coi
  suoi valori. Il motivo degli indirizzi del soggetto è provato sul predicato, non su righe vere.

---

### Note di migrazione

* 2026-11-14 — nasce con il modello «il cambio non pulisce niente» (`brief-db-cambio-natura-soggetto-conferma-e-pulizia`,
  D-5 … D-11). Sostituisce la regola delle nature modificabili che stava nel backend (stessa macro-tipologia)
  e assorbe il guard dei titoli IVA al cambio, ritirato. Il motivo degli indirizzi dei ruoli si aggiunge il
  2026-11-16.

---

{% include-markdown "signature-core.md" %}
