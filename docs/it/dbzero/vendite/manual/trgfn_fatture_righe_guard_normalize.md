## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_righe_guard_normalize`
### 🎯 Scopo Principale
Normalizza i dati di riga fattura su inserimento/aggiornamento:
* eredita `dest_billing_account_id` dalla testata se assente;
* allinea lo snapshot `iva_natura` in base a `config.iva`;
* ⭐ **congela `aliquota_iva`** (dal 2026-08-29);
* ⭐ **riempie `esigibilita` e `split_payment`** dal soggetto **cliente**
  (dal 2026-08-30).

> ⚠️ **Le ultime due voci non c'erano in questo manuale**, ed è il genere di
> assenza che inganna: chi leggeva pensava che quelle colonne le riempisse il
> backend, e nessuno le riempiva affatto — erano `NULL` su **tutte** le righe.

---

### Regole principali

* se `NEW.dest_billing_account_id` e` `NULL`, usa `fatture.billing_account_id`;
* se `NEW.iva_id` e` valorizzato, copia in `NEW.iva_natura` il codice
  da `config.iva_natura` collegato alla master IVA;
* in UPDATE, se cambia manualmente `iva_natura` a parita` di `iva_id`,
  riallinea comunque lo snapshot dalla master;
* se `NEW.iva_id` e` valorizzato, scrive in `NEW.aliquota_iva` la percentuale
  risolta per lo **stato dell'emittente**. ⚠️ Lo fa a **ogni** scrittura: non e`
  uno snapshot «una volta», e diventa una fotografia solo quando il documento
  smette di essere scritto;
* legge `split_payment` dal soggetto **cliente** (dal `billing_account` della
  testata, non dall'emittente) e da li` deriva la coppia
  `split_payment` / `esigibilita`.

---

### ⚠️ Le due meta` della coppia si comportano diversamente, **apposta**

* **`split_payment`** e` una *derivazione pura*: non esiste una scelta legittima
  per riga, quindi il trigger la **riscrive sempre**. Una riga che dissentisse dal
  proprio cliente e` un errore, non un'eccezione.
* **`esigibilita`** no. Con la scissione, `'S'` e` **imposta**; senza, restano
  `'I'` (immediata) e `'D'` (**differita**) — e la differita e` una **scelta del
  documento** che nessuna colonna sa dedurre. Fuori dalla scissione il trigger
  riempie percio` **solo il vuoto**: sovrascrivere cancellerebbe in silenzio una
  `'D'` scelta da qualcuno.

> ⛔ **Se il soggetto cliente non si risolve, non scrive nulla** e le due colonne
> restano `NULL`. «Non scissa» sarebbe un'**affermazione** su un documento che
> potrebbe andare a una Pubblica Amministrazione; `NULL` dice «non determinato»,
> ed e` vero.

### ⭐ Perche` questi campi stanno qui e non nel chiamante

`vendite.fatture_riepiloghi_iva` **raggruppa** per
`(iva, natura, esigibilita, split)`. Se due righe della stessa fattura portassero
valori diversi, la stessa aliquota si spezzerebbe in **due riepiloghi** e la
fattura direbbe due cose sul proprio regime. Derivandoli dall'unico cliente della
testata, sono costanti **per costruzione** — e il valore non dipende da quale
percorso del backend ha scritto la riga.

---

### Effetto trigger

* trigger `BEFORE INSERT OR UPDATE` su `vendite.fatture_righe`;
* mantiene coerenza tra testata/riga e snapshot natura IVA.

---

{% include-markdown "signature-core.md" %}

