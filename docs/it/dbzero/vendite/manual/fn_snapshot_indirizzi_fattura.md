## 📘 Documentazione Concettuale – Funzione `vendite.fn_snapshot_indirizzi_fattura`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatture_indirizzi](/dbzero/vendite/tabelle/fatture_indirizzi) — dove scrive
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) · [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
> **Funzioni:**
>
> • [script.fn_resolve_indirizzo_documento](/dbzero/script/funzioni/fn_resolve_indirizzo_documento) — la catena che invoca
> • [vendite.fn_snapshot_fattura_lotto](/dbzero/vendite/funzioni/fn_snapshot_fattura_lotto) — il wrapper di lotto
> • [vendite.fn_snapshot_intestazione_fattura](/dbzero/vendite/funzioni/fn_snapshot_intestazione_fattura) — la **sorella**, per l'identità fiscale

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`vendite.fn_snapshot_indirizzi_fattura(p_fattura_id)` **congela** sulla fattura
gli indirizzi del cliente, così che il documento resti stampabile identico anche
se l'anagrafica cambia dopo.

Scrive in `vendite.fatture_indirizzi` con `UPSERT` sull'unica per tipo.

---

### 🔑 `fatture_indirizzi` è la collezione degli indirizzi DEL CLIENTE

Non «gli indirizzi della fattura». La differenza sembra sottile e invece decide
la struttura: il vincolo `uq_fatture_indirizzi_uno_per_tipo_` ammette **una sola
riga per tipo**, quindi la tabella non può ospitare insieme la sede dell'emittente
e quella del cliente.

È la ragione per cui l'**identità fiscale delle due parti** vive altrove — in due
colonne di testata, scritte dalla funzione sorella.

---

### 👨‍👦 Risolve dal billing account di TESTATA (D-P)

La fattura si emette sul BA **padre**, quindi gli indirizzi sono i suoi. La
funzione legge il BA di testata, che in gerarchia **è già il padre**: nessun caso
speciale da scrivere, nessun `CASE WHEN`.

⚠️ Il sotto-dettaglio per figlio delle utilities **non può** stare qui (lo
impedisce la unique): va nel corpo del documento.

---

### Quali tipi, e chi lo decide

I tipi ammessi in ambito `FATTURE` arrivano dalla **matrice**
`config.tipi_ruolo_tipi_indirizzo`, non da un elenco nel codice: oggi sono quattro,
di cui `FATT` **obbligatorio**.

Data-driven per scelta: aggiungere un tipo obbligatorio è una riga di seed, non
una migration di funzione.

---

### Assenza di `FATT` = errore

È l'unico caso in cui questa funzione solleva. Gli altri tipi mancanti sono
legittimi e non producono riga.

---

### ♻️ Idempotenza

Rieseguire su una fattura già completa restituisce `(0, 0)`: nessuna scrittura,
nessun effetto. È ciò che rende sicuro il rilancio dello step da parte del
wrapper.

---
{% include-markdown "signature-core.md" %}
