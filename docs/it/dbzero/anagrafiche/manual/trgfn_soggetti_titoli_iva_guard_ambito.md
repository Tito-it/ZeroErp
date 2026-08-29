## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — **la regola vive lì**
> • [anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_ambiti_guard) — il gemello sulle righe figlie
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)

---

### 🎯 Scopo Principale

(rev 2026-08-29 — funzione nata il 2026-08-29)

La stessa regola dell'ambito, applicata quando a cambiare è il **titolo** invece
delle sue righe.

---

### 🔴 Perché non è un doppione — ed è il lato che si dimentica

Due titoli diventano sovrapposti anche **senza che nessuno tocchi le righe di
ambito**:

* si allarga `valido_al` o si anticipa `valido_dal`;
* si **riattiva** un titolo che era spento;
* si cambia il **tipo**, o il cliente, o l'emittente.

In nessuno di questi casi la tabella figlia viene scritta, quindi il guard che sta lì
**non scatta**. Un controllo scritto su una sola delle due tabelle sarebbe cieco
metà del tempo — e la metà cieca è quella che capita nell'uso quotidiano, perché
prolungare la validità di un titolo è un gesto normale.

⭐ È il motivo per cui la regola sta in una **funzione pura** che entrambi i trigger
**chiamano**: un test che confrontasse due predicati proverebbe che *oggi*
coincidono; così invece si prova che non possono divergere.

---

### Contesto di Esecuzione

* **Tipo**: trigger `AFTER UPDATE OF valido_dal, valido_al, attivo, ambito, tipo_titolo_iva_id, soggetto_id, emittente_fiscale_id`
* **Fascia**: `z90`

⚠️ `AFTER`, perché la funzione legge la riga **com'è dopo** la modifica.

⚠️ L'elenco delle colonne sorvegliate è quello che entra nella chiave
dell'ambiguità **più** la finestra di validità: toccarne una qualsiasi può creare
una sovrapposizione che prima non c'era.

⚠️ Non scatta in inserimento, e non serve: un titolo appena creato non ha ancora
righe di ambito, quindi non può essere in conflitto con nessuno **per ambito**. Le
sovrapposizioni fra titoli che valgono per tutto le chiude un vincolo di database.

---

### Codici errore

Gli stessi del gemello — `E_TITOLO_IVA_AMBITO_NON_AMMESSO` e
`E_TITOLO_IVA_AMBITO_SOVRAPPOSTO` — perché la funzione che li nomina è la stessa.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10` / `D13`.

---

{% include-markdown "signature-core.md" %}
