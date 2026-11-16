## 📘 Documentazione Concettuale – Tabella `documenti.template_asset`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.tipi_asset_documento](/dbzero/documenti/tabelle/tipi_asset_documento) — che genere di asset è
> * [documenti.tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati) — i formati che ogni tipo ammette
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'azienda a cui l'asset appartiene
>
> Approfondimento viste:
>
> * [documenti.vw_template_asset_utilizzabili](/dbzero/documenti/views/vw_template_asset_utilizzabili) — gli asset che si possono usare oggi
>
> Approfondimento funzioni:
>
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — un asset non si cancella
> * [documenti.trgfn_template_asset_protect_file](/dbzero/documenti/funzioni/trgfn_template_asset_protect_file) — il file di un asset non cambia
> * [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — l'azienda presa dalla sessione
> * [documenti.trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso) — un asset nasce in un formato del suo tipo
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — gli asset nella stampa

---

### 🎯 Scopo Principale

`documenti.template_asset` è il catalogo degli **elementi grafici di un'azienda** usati nella stampa:
logo, carta intestata, firma, immagini, fogli di stile. La riga descrive il file (nome, tipo, peso,
impronta SHA-256, chiave nello storage) e il suo ruolo; il file sta nello storage.

---

### Una versione richiama un asset per codice interno

Una versione di template cita un asset col suo `codice_interno`, e il motore lo cerca fra gli asset
**dell'azienda del documento**. La chiave è (azienda, codice interno), unica: al più un asset per
codice e azienda. Il codice interno non si modifica (`E_CODICE_NON_MODIFICABILE`), quindi un asset
rinominato non rompe i template che lo citano.

Per questo i modelli standard, che non hanno azienda, non richiamano asset.

Nessuna FK lega un asset a un template o a una stampa: il legame è il codice scritto nel corpo della
versione.

---

### ⛔ Un asset non cambia file e non si cancella

* Il file di un asset non cambia: chiave nello storage, impronta, peso, tipo e nome sono quelli del
  caricamento ([protect_file](/dbzero/documenti/funzioni/trgfn_template_asset_protect_file)).
* Un asset non si cancella mai, da nessun ruolo (il rifiuto sempre attivo di
  [trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic)).

Insieme fanno dell'asset un'istantanea stabile: la ristampa fedele di un documento ritrova il file di
allora, anche se oggi l'asset è scaduto o spento.

Restano modificabili descrizione, codice, meta, attivo e le date.

---

### Lo stesso file una volta sola per azienda

L'impronta SHA-256 è unica per azienda (`uq_template_asset_emittente_sha256`): lo stesso file non si
carica due volte, nemmeno con due ruoli diversi. Due aziende possono avere lo stesso file.

---

### Attivo e valido: che cosa la stampa può usare

Una stampa nuova e l'anteprima usano solo gli asset attivi e validi oggi; la ristampa fedele usa
l'asset di allora comunque. La regola «utilizzabile oggi» sta in un posto solo, la vista
[vw_template_asset_utilizzabili](/dbzero/documenti/views/vw_template_asset_utilizzabili), per il
render e per il filtro degli asset utilizzabili della lista (il backend ripete ancora la condizione:
lo dice la pagina della vista). `validita` è l'intervallo generato da `valido_dal` e `valido_al`, estremi
compresi, e l'ordine delle date lo verifica il guard comune. Un asset si ritira chiudendo la validità
o spegnendolo.

---

### ⭐ Un logo nuovo è un asset nuovo, e una versione nuova del template

Il codice interno è unico per azienda senza tener conto della validità, e il file non si
sostituisce: il logo nuovo è un asset nuovo con un codice interno nuovo. Le versioni pubblicate, che
non si modificano, continuano a citare il vecchio; per stampare col logo nuovo si pubblica una
versione nuova di ogni template che lo cita. Due asset con lo stesso codice in periodi diversi non
sono ammessi.

È voluto: lo stesso codice interno indica sempre gli stessi byte, ed è ciò su cui si regge la
ristampa fedele, che ritrova il file di allora anche se oggi l'asset è scaduto o spento.

---

### Il formato lo ammette il tipo

Un asset nasce solo in un formato che il suo tipo ammette
([tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati)): un logo in
PNG, JPEG, SVG, WebP o GIF, un foglio di stile in CSS. Il formato non cambia dopo la nascita; il tipo
sì, e il tipo nuovo deve ammettere il formato dell'asset. Il backend legge la stessa lista per
controllare i byte del file.

---

### Codici errore

* `E_DOCUMENTI_ASSET_DELETE_BLOCKED` — cancellazione di un asset.
* `E_DOCUMENTI_ASSET_FILE_IMMUTABILE` — modifica del file di un asset.
* `E_CODICE_NON_MODIFICABILE` — modifica del codice interno.
* `E_DOCUMENTI_FORMATO_NON_AMMESSO` — formato che il tipo dell'asset non ammette.
* `E_DATA_AL_MINORE_DAL` — fine che precede l'inizio.
* Le unicità (codice, codice interno, impronta) arrivano come violazione di vincolo, e il backend le
  traduce per nome.

---

### Test

* `db/pgtap/documenti/test-documenti-template-asset.sql` — unicità dell'impronta, cancellazione
  bloccata, file immutabile, meta modificabile.
* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — il formato ammesso dal tipo, alla
  nascita e al cambio di tipo.
* `db/pgtap/documenti/test-documenti-risoluzione-scarto-asset-v1.sql` — utilizzabile l'asset acceso e
  valido oggi, non quello spento né quello che vale da domani.

---

### Note di migrazione

* 2026-04-29 — nasce la tabella.
* 2026-05-14 — `validita` diventa una colonna generata.
* 2026-11-16 — il formato ammesso dal tipo passa dal backend al database, e la regola «utilizzabile
  oggi» ha la sua vista.

---

{% include-markdown "signature-core.md" %}
