## 📘 Documentazione Concettuale – Funzione `vendite.fn_snapshot_intestazione_fattura`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — colonne `emittente_snapshot` e `cliente_snapshot`
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) · [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)
>
> **Funzioni:**
>
> • [vendite.fn_snapshot_indirizzi_fattura](/dbzero/vendite/funzioni/fn_snapshot_indirizzi_fattura) — la **sorella**, per gli indirizzi
> • [script.fn_resolve_indirizzo_documento](/dbzero/script/funzioni/fn_resolve_indirizzo_documento) — usata per la sede

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`vendite.fn_snapshot_intestazione_fattura(p_fattura_id)` congela in testata
l'**identità fiscale delle due parti** — emittente e cliente — nelle colonne
`emittente_snapshot` e `cliente_snapshot`.

Serve alla **ristampa conforme**: una fattura emessa deve poter essere ristampata
identica anche dopo che l'anagrafica è cambiata.

---

### 👭 È una funzione SORELLA, non un'estensione

Poteva essere un pezzo in più dentro `fn_snapshot_indirizzi_fattura`. Non lo è, e
la ragione è dei **contatori**: quella funzione conta indirizzi scritti. Aggiungerci
l'intestazione avrebbe fatto **mentire il contatore** — un numero che dice
«3 indirizzi» mentre ha scritto tre indirizzi e un'intestazione non è più una
misura, è un'approssimazione.

Il wrapper di lotto tiene infatti un **sesto contatore** dedicato,
`intestazioni_scritte`.

---

### 🔴 Gli id sono provenienza, non contenuto

Di ogni entità referenziata si congela il **valore**, tenendo l'id accanto solo
come indicazione di origine.

Uno snapshot che porta solo `forma_giuridica_id` **non è uno snapshot**: se
domani cambia la descrizione di quella forma giuridica, la ristampa cambia di
nuovo — che è esattamente ciò che lo snapshot doveva impedire.

---

### La sede usa la stessa catena del cliente

Non una query dedicata: `fn_resolve_indirizzo_documento` con istanza `NULL` e tipo
`SEDELEG`.

Misurato: **zero** emittenti hanno un indirizzo sul layer RUOLO — la sede si
risolve tutta dal layer SOGGETTO. È il caso che dimostra perché la catena deve
avere due layer e non uno.

---

### `jsonb_strip_nulls`, e perché è una promessa

Lo snapshot non contiene chiavi a `null`.

Non è pulizia estetica: è la proprietà su cui si appoggia il guard di uscita da
DRAFT, che verifica l'intestazione con `jsonb_typeof` e **non** con `IS NULL` —
perché uno snapshot vuoto arriva come `{}`, e un test sul solo NULL lo
dichiarerebbe presente.

Chi togliesse lo `strip_nulls` romperebbe un guard che sta in un altro file.

---

### Determinismo senza `LIMIT`

Tre `LEFT JOIN` deterministiche **per vincolo**, non per fortuna: nessun
`LIMIT 1` a chiudere gli occhi su un possibile secondo candidato.

---

### ♻️ Idempotenza

Rieseguire non riscrive. ⚠️ Nel verificarlo non basta controllare il contatore a
zero: si verifica **anche** che le due colonne siano rimaste quelle. Contatore e
colonne possono mentire in modi diversi.

---
{% include-markdown "signature-core.md" %}
