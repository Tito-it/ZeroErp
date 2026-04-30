## 📘 Documentazione Concettuale – Tabella `documenti.template_asset`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.tipi_asset_documento](/dbzero/documenti/tabelle/tipi_asset_documento)  
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.template_asset` è il catalogo degli **asset documentali riusabili**
associati a un emittente fiscale: logo, firme, immagini, CSS o altri file di
supporto usati nella resa dei template.

---

### Ruolo nel processo

* centralizza gli asset caricati e riusabili da più template/versioni;
* separa l'identità funzionale dell'asset dal file binario sottostante;
* consente validità temporale di asset diversi nel tempo per lo stesso
  emittente.

---

### Campi chiave (semantica)

* **Identita` funzionale**: `codice_interno`, `codice`, `descrizione`.
* **Classificazione**: `asset_tipo_id`, `emittente_fiscale_id`.
* **Identita` binaria**: `sha256`.
* **Persistenza file**: `mime_type`, `file_name`, `file_size_bytes`,
  `storage_key`.
* **Validita`**: `valido_dal`, `valido_al`, `validita`.

---

### Regole operative

* `codice_interno` è la chiave tecnica stabile dell'asset nel perimetro
  dell'emittente;
* `sha256` identifica il file binario ed evita duplicati per lo stesso
  emittente;
* `validita` è calcolata dal trigger standard e va trattata come derivata;
* la presenza di `attivo = false` o la chiusura della finestra di validità
  impediscono nuovi utilizzi senza perdere tracciabilità storica.

---

### Distinzione importante

* `codice_interno` identifica **che cos'è** l'asset nel dominio applicativo;
* `sha256` identifica **quale file binario** è stato caricato;
* due asset con ruolo diverso non devono condividere la stessa identità
  funzionale, anche se in teoria il file fosse uguale.

---

{% include-markdown "signature-core.md" %}
