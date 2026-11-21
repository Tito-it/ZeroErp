## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_guard_file_principale`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa che il controllo giudica
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — il file principale che deve trovare
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_file_protect_file](/dbzero/documenti/funzioni/trgfn_documenti_generati_file_protect_file) — il flag del principale non cambia
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il file non si cancella
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — le garanzie del modulo
> * [Linee guida Trigger](/linee-guida-trigger) — i trigger differiti, e chi legge una riga correlata

---

### 🎯 Scopo Principale

Trigger function di un constraint trigger differito su `documenti.documenti_generati`: a fine transazione una
stampa nata ha il suo file principale, il PDF che si scarica e si ristampa.

Senza il suo PDF una stampa è un fatto senza prova: non si scarica, non si ristampa, e l'impronta conservata non
ha niente da verificare.

---

### ⭐ Al commit, e solo alla nascita

Il servizio che stampa scrive prima la stampa e poi il suo PDF, nella stessa transazione: il controllo aspetta la
fine della transazione per giudicare la coppia intera.

Guarda solo la nascita. Dopo non serve altro: il file non si cancella, e il flag del principale non cambia. Le
stampe nate prima del controllo non sono giudicate.

Che il principale sia **al più uno** lo tiene già l'indice `uq_documenti_generati_file_principale`; questo
controllo dà l'altra metà, **almeno uno**.

---

### Legge il file fuori dalla row security

Il controllo decide su una riga correlata e scatta al commit: non la legge con l'identità di chi chiude la
transazione, che potrebbe non vederla. La funzione è del proprietario delle tabelle, con un percorso di ricerca
fisso, e guarda soltanto i file della stampa che nasce.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE` (`TECNICO`) — la stampa non ha il suo PDF principale; la frase dice
  il nome del file. È un difetto di chi scrive la stampa, non un dato dell'operatore.

---

### Test

* `db/pgtap/documenti/test-documenti-stampa-e-storia-v1.sql` — una stampa senza principale rifiutata, con la sua
  frase; una stampa col suo PDF registrata.

I pgTAP costruiscono le stampe con `dbops.fn_pgtap_stampa_con_pdf`, che scrive stampa e PDF in due istruzioni e fa
giudicare subito il controllo.

---

### Note di migrazione

* 2026-11-15 — nasce il controllo. Prima che una stampa avesse il suo PDF lo garantiva solo il servizio.

---

{% include-markdown "signature-core.md" %}
