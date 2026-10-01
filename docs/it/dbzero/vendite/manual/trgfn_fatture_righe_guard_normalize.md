## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_righe_guard_normalize`
### 🎯 Scopo Principale
Normalizza i dati di riga fattura su inserimento/aggiornamento:
* eredita `dest_billing_account_id` dalla testata se assente;
* allinea lo snapshot `iva_natura` in base a `config.iva`;
* ⭐ **congela `aliquota_iva`** (dal 2026-08-29);
* ⭐ **riempie `esigibilita` e `split_payment`** (dal 2026-08-30); dal
  2026-10-01 le **riscrive sempre**, chiedendole alla regola unica, che guarda
  anche il **regime dell'emittente** (IVA per cassa).

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
* chiede la coppia `esigibilita` / `split_payment` a
  [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura)
  e la **riscrive a ogni scrittura**. La regola è
  [script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva):
  scissione del cliente, regime dell'emittente (quello **congelato nello
  snapshot** dell'intestazione, se c'è), partita IVA del cliente, inversione
  contabile del codice IVA.

---

### ⭐ Una derivazione pura, tutte e due le colonne (rev 2026-10-01)

Fino al 2026-09-30 le due metà della coppia si comportavano diversamente:
`split_payment` si riscriveva sempre, `esigibilita` fuori dalla scissione
riempiva **solo il vuoto**, perché una `'D'` poteva venire solo da una persona.

Con l'IVA per cassa anche la `'D'` è **dedotta** (dal regime dell'emittente), e
una colonna non sa dire chi l'ha scritta. Il «solo il vuoto» lasciava valori
stantii: `'I'` su una fattura di un emittente passato a RF17 in bozza, `'D'` su
una riga il cui cliente era tornato privato. Ora **tutte e due** si riscrivono
sempre (decisione D-7). Una differita scelta a mano, se mai servirà, avrà una
colonna sua.

> ⛔ **Se il soggetto cliente non si risolve, la coppia esce `NULL`/`NULL`**:
> «non scissa» sarebbe un'**affermazione** su un documento che potrebbe andare a
> una Pubblica Amministrazione; `NULL` dice «non determinato», ed è vero. Prima
> del 2026-10-01 il trigger lasciava i valori che c'erano.

Brief: `brief-db-esigibilita-iva-per-cassa-emittente`.

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

