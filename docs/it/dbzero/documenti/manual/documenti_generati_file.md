## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati_file`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa a cui il file appartiene
> * [documenti.tipi_file_documento](/dbzero/documenti/tabelle/tipi_file_documento) — il ruolo del file
> * [documenti.documenti_generati_eventi](/dbzero/documenti/tabelle/documenti_generati_eventi) — l'evento che registra gli allegati aggiunti
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_file_protect_file](/dbzero/documenti/funzioni/trgfn_documenti_generati_file_protect_file) — il file non si sostituisce
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — che cosa succede quando si genera un documento

---

### 🎯 Scopo Principale

`documenti.documenti_generati_file` registra i file salvati di una stampa: dove stanno nello storage
(`storage_key`), che cosa sono e la loro impronta. Separa il fatto della stampa, in `documenti_generati`, dal file
che la materializza.

Una stampa ha il suo PDF (`PDF_FINALE`) e può avere degli allegati (`ALLEGATO`), anche aggiunti dopo l'emissione.

---

### Il file principale e gli altri

* `is_principale` dice qual è il file che rappresenta la stampa: al più uno per stampa
  (`uq_documenti_generati_file_principale`). Il PDF della generazione nasce principale, gli allegati no.
* `ordinamento` numera i file dello stesso ruolo sulla stessa stampa, da 1: la terna stampa, ruolo, ordinamento
  è unica.
* `sha256` (64 caratteri), `file_size_bytes` (positivo), `mime_type`, `file_name` e `storage_key` (non vuoti)
  descrivono il file com'era quando è stato salvato.

---

### ⭐ Un file salvato non si sostituisce

Dopo l'inserimento non cambiano né la stampa e il ruolo, né il file (posizione, impronta, dimensione, tipo, nome),
né `is_principale` (`trgfn_documenti_generati_file_protect_file`). Restano modificabili `ordinamento`, `meta` e i
campi di audit. Sostituire il PDF vorrebbe dire mentire su ciò che è stato emesso: una stampa sbagliata si
rigenera, e la nuova ha il suo progressivo e i suoi file.

Lo storico standard è spento, come sulla stampa: il file non cambia.

---

### Chi vede i file

Un file segue il perimetro della sua stampa: l'azienda si risale dalla stampa, e un operatore vede e scrive solo i
file delle stampe delle aziende del suo perimetro.

---

### ⚠️ Che cosa oggi non copre

* **Una stampa senza file è ammessa.** Il database non chiede che una stampa abbia un file principale: lo garantisce
  solo il backend, che scrive stampa e PDF nella stessa transazione.
* **Un file si può cancellare.** A differenza della stampa e dei suoi eventi, la tabella non ha un trigger che rifiuti
  il `DELETE`, e l'applicazione ha il privilegio: cancellando la riga del PDF principale la stampa resta senza il suo
  file, e la ristampa e il download non lo ritrovano più. Le colonne del file sono protette solo dall'UPDATE.
* **Un tipo di file usato non si spegne.** La tabella non ha `attivo`, e ogni file conta come figlio vivo per il
  blocco della regola ATTIVO su `tipi_file_documento`.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_FILE_IMMUTABILE` — si è cercato di cambiare il file o il suo ruolo.

---

### Test

* `db/pgtap/documenti/test-documenti-generati-file.sql` — un solo principale, la terna unica, il blocco della
  sostituzione;
* `db/pgtap/documenti/test-documenti-storico-disabled.sql` — lo storico spento;
* `db/pgtap/rls/test-rls-documenti-satelliti.sql` — il perimetro dei file.

---

### Note di migrazione

* 2026-04-29 — nasce la tabella, con lo storico standard spento dal 2026-05-01.
* 2026-05-01 — nasce `is_principale`.
* 2026-06-03 — gli allegati si possono aggiungere dopo l'emissione.
* 2026-09-10 — la tabella entra nel perimetro delle aziende.

---

{% include-markdown "signature-core.md" %}
