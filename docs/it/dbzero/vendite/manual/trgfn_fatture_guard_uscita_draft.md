## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_fatture_guard_uscita_draft`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) · [vendite.fatture_indirizzi](/dbzero/vendite/tabelle/fatture_indirizzi)
>
> **Funzioni:**
>
> • [script.fn_indirizzi_obbligatori_mancanti](/dbzero/script/funzioni/fn_indirizzi_obbligatori_mancanti) — il building block che interroga la matrice
> • [vendite.fn_snapshot_intestazione_fattura](/dbzero/vendite/funzioni/fn_snapshot_intestazione_fattura) — chi produce ciò che qui si verifica

---
### 🎯 Scopo Principale
(latest review 12-11-2026)

Impedisce a una fattura di **lasciare la bozza** finché non è completa. La bozza
è lo stato marcato `iniziale` nel vocabolario
[`config.stati_doc_fiscale`](/dbzero/config/manual/stati_doc_fiscale) (oggi `DRAFT`):
il guard legge la colonna, non il codice. Completa vuol dire:
indirizzi obbligatori presenti **e** intestazione fiscale congelata, con dentro
la **sede legale del cedente** (dal 21-10-2026, brief-db-modelli-documento-standard
§10.7 R-5).

Codice: **`E_FATTURA_NON_EMETTIBILE_INCOMPLETA` (575)**, mappato **409** dal
backend — è uno stato della risorsa, non un input malformato.

Un codice solo per entrambi i casi: chi lo riceve rilancia comunque lo step DRAFT,
e il dettaglio (`indirizzi_mancanti` / `intestazione_mancante` /
`intestazione_incompleta`) sta nel payload.

### La sede legale del cedente

Lo snapshot dell'emittente porta la sede (`emittente_snapshot.sede`) quando
l'azienda ce l'ha: la cerca sul ruolo e poi sul soggetto, come l'indirizzo del
cliente. Senza sede la chiave manca. Il guard la pretende **dentro** un'intestazione
che c'è: messaggio «intestazione incompleta: manca la sede legale
dell'emittente», contesto `intestazione_incompleta`. Il rimedio è anagrafico:
inserire la sede legale dell'azienda e rieseguire lo step DRAFT, che riscrive lo
snapshot. Una sede a `{}` non vale, per lo stesso motivo dell'intestazione
(sotto).

---

### Quattro scelte da non ri-discutere

**1. Presidia l'USCITA dalla bozza, non ogni avanzamento.** Oltre la bozza il
presidio è del guard di congelamento. Allargarlo darebbe una **seconda occasione
di fallire** su un documento già emesso — cioè trasformerebbe un errore prevenuto
in un errore subito.

**2. Solo `UPDATE`.** L'unico creatore applicativo,
`fn_get_or_create_fattura_header`, inserisce **sempre** in bozza, e una fattura
nasce solo nello stato iniziale (trigger della nascita): la porta è già chiusa a
monte.

**3. Lo stato abortito è esente.** Una bozza incompleta deve restare
**chiudibile**: non si può costringere qualcuno a completare un documento solo per
poterlo annullare.

**4. 🔴 Nessun bypass GUC**, a differenza del resto della famiglia. Il reset lotto
*rientra* nella bozza, non ne esce: un bypass qui sarebbe una **porta di servizio
sull'emissione** in cambio di nulla.

---

### 🔤 Il nome ordina, e l'ordine è sostanza

Si chiama `..._guard_uscita_draft` perché deve ordinare **dopo** `guard_stato`.

Se scattasse prima, una transizione **illegale** verrebbe respinta come «documento
incompleto» invece che come transizione vietata — la diagnosi sbagliata su un
problema diverso. C'è un test dedicato a presidiare quest'ordine.

---

### Data-driven, non cablato

Gli indirizzi obbligatori si leggono dalla **matrice**
`config.tipi_ruolo_tipi_indirizzo` tramite `script.fn_indirizzi_obbligatori_mancanti`
— lo stesso building block di `fn_check_ddt_emittibile`. Nessun `FATT` scritto nel
codice: rendere obbligatorio un altro tipo è una riga di seed.

---

### ⚠️ L'intestazione si verifica con `jsonb_typeof`, non con `IS NULL`

`jsonb_strip_nulls` fa arrivare uno snapshot vuoto come **`{}`**, e un test sul
solo `IS NULL` lo dichiarerebbe **presente**.

È una dipendenza reale fra due file: chi togliesse lo `strip_nulls` dalla funzione
di snapshot romperebbe questo guard.

---

### 🧬 Nato già completo

Questo guard **assorbe** il passo 2.5 del piano («`FATT` obbligatorio»), che non
è mai stato scritto separatamente: il criterio era stato allargato — indirizzi
*e* intestazione — prima che 2.5 arrivasse. Si è preferito farlo nascere completo
invece di scriverlo e riaprirlo dopo pochi giorni.

---
{% include-markdown "signature-core.md" %}
