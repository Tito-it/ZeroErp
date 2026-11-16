## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati_file`

> **Ultimo aggiornamento**: 15 novembre 2026
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

* `is_principale` dice qual è il file che rappresenta la stampa: **esattamente uno** per stampa. Al più uno lo
  tiene `uq_documenti_generati_file_principale`; almeno uno lo chiede, a fine transazione, il controllo della
  stampa che nasce (`documenti.trgfn_documenti_generati_guard_file_principale`). Il PDF della generazione nasce
  principale, gli allegati no.
* `ordinamento` numera i file dello stesso ruolo sulla stessa stampa, da 1: la terna stampa, ruolo, ordinamento
  è unica.
* `sha256` (64 caratteri), `file_size_bytes` (positivo), `mime_type`, `file_name` e `storage_key` (non vuoti)
  descrivono il file com'era quando è stato salvato.

---

### ⭐ Un file salvato non si sostituisce e non si cancella

Dopo l'inserimento non cambiano né la stampa e il ruolo, né il file (posizione, impronta, dimensione, tipo, nome),
né `is_principale` (`trgfn_documenti_generati_file_protect_file`). Restano modificabili `ordinamento`, `meta` e i
campi di audit. Sostituire il PDF vorrebbe dire mentire su ciò che è stato emesso: una stampa sbagliata si
rigenera, e la nuova ha il suo progressivo e i suoi file.

Il file non si cancella, da nessun ruolo (il rifiuto sempre attivo di `script.trgfn_prevent_modification_generic`):
senza il suo PDF la stampa non si scarica e non si ristampa, e l'impronta conservata non verifica più niente.

Lo storico standard è spento, come sulla stampa: il file non cambia.

---

### Il tipo di file si spegne anche se è stato usato

Un file è storia come la sua stampa: la sua chiave verso `tipi_file_documento` è un'eccezione della regola ATTIVO
(`dbops.automazione_attivo_eccezioni`). Un tipo di file che ha avuto dei file si spegne; un tipo spento non tiene
fermi gli allegati di una stampa vecchia.

---

### Chi vede i file

Un file segue il perimetro della sua stampa: l'azienda si risale dalla stampa, e un operatore vede e scrive solo i
file delle stampe delle aziende del suo perimetro.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_FILE_IMMUTABILE` — si è cercato di cambiare il file o il suo ruolo;
* `E_FILE_DOCUMENTO_DELETE_VIETATA` — si è cercato di cancellare il file.

---

### Test

* `db/pgtap/documenti/test-documenti-generati-file.sql` — un solo principale, la terna unica, il blocco della
  sostituzione;
* `db/pgtap/documenti/test-documenti-stampa-e-storia-v1.sql` — il principale obbligatorio, il file che non si
  cancella, il tipo di file che si spegne;
* `db/pgtap/documenti/test-documenti-storico-disabled.sql` — lo storico spento;
* `db/pgtap/rls/test-rls-documenti-satelliti.sql` — il perimetro dei file.

---

### Note di migrazione

* 2026-04-29 — nasce la tabella, con lo storico standard spento dal 2026-05-01.
* 2026-05-01 — nasce `is_principale`.
* 2026-06-03 — gli allegati si possono aggiungere dopo l'emissione.
* 2026-09-10 — la tabella entra nel perimetro delle aziende.
* 2026-11-15 — il file non si cancella più, e una stampa nuova deve avere il suo principale; la chiave del tipo di
  file diventa un'eccezione della regola ATTIVO.

---

{% include-markdown "signature-core.md" %}
