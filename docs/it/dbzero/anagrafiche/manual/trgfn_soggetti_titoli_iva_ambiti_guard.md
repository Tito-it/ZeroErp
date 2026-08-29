## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — **la regola vive lì**
> • [anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_ambito) — il gemello sul titolo
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti)

---

### 🎯 Scopo Principale

(rev 2026-08-29 — funzione nata il 2026-08-29)

Rifiuta una riga di ambito che rende incoerente il titolo a cui appartiene.

⭐ **Non contiene la regola**: chiama `anagrafiche.fn_check_titolo_iva_ambito` e
solleva il codice del **primo** motivo. Il presidio da mantenere non è «gli esiti
coincidono» ma *«il guard non contiene più il predicato»* — così la regola non può
divergere dal suo gemello sul titolo, perché è scritta in un posto solo.

---

### Contesto di Esecuzione

* **Tipo**: trigger `AFTER INSERT OR UPDATE`
* **Fascia**: `z90`

---

### ⚠️ Perché `AFTER`, contro la convenzione dei guard

La convenzione di casa vuole i controlli in fascia `a10`, cioè **prima** della
scrittura. Qui non si può, e la ragione è concreta: la funzione **conta** le righe di
ambito e confronta gli oggetti coperti, quindi **la riga nuova dev'essere già
scritta**.

⛔ Un `BEFORE` valuterebbe il titolo com'era **prima**, e lascerebbe passare proprio
la riga che crea il conflitto.

---

### I due motivi che può sollevare

| Codice | Motivo |
| --- | --- |
| `E_TITOLO_IVA_AMBITO_NON_AMMESSO` | si aggiunge una voce a un titolo che vale per **tutto** |
| `E_TITOLO_IVA_AMBITO_SOVRAPPOSTO` | **pareggio**: un altro titolo dello stesso tipo, stesso cliente, stesso emittente, periodo sovrapposto, copre lo **stesso oggetto allo stesso livello** |

⚠️ **L'ordine dell'elenco è il contratto**: il guard solleva il primo, e se l'ordine
divergesse il codice sollevato e il motivo mostrato direbbero cose diverse.

⚠️ Titoli su **livelli diversi** non sono un pareggio e non vengono bloccati: vince
il più specifico. Bloccarli rifiuterebbe la configurazione più normale che esista.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10` / `D13`.

---

{% include-markdown "signature-core.md" %}
