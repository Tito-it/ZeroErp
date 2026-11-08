## 📘 Documentazione Concettuale – Tabella `pagamenti.sepa_mandati`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — il conto del debitore da addebitare
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il primo livello del perimetro del mandato
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il secondo livello, la singola utenza
> * [dbops.rls_perimetro_debito](/dbzero/dbops/tabelle/rls_perimetro_debito) — dove è registrato il perimetro ancora da decidere
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_sepa_mandati_guard](/dbzero/anagrafiche/funzioni/trgfn_sepa_mandati_guard) — stato `ATTIVO` con data di attivazione, normalizzazione di UMR e IBAN

---

### 🎯 Scopo Principale

La tabella **`pagamenti.sepa_mandati`** registra i **mandati SEPA** (schemi `CORE` e `B2B`):
l'autorizzazione con cui il debitore permette al creditore di addebitare il proprio conto.

Senza un mandato valido un addebito diretto non si può disporre: è il documento che rende
l'incasso legittimo. Ogni mandato lega un **conto di ruolo** del debitore
(`soggetto_ruolo_conto_id`) a un perimetro, e porta l'`umr`, la *Unique Mandate Reference* che
identifica il mandato verso la banca.

---

### ⚠️ Una struttura senza scrittori

Nessuna funzione del database e nessun servizio del backend scrive questa tabella: il ciclo
degli addebiti diretti non è ancora costruito. La struttura c'è, il modello d'uso no, e le
regole che seguono vanno rilette quando quel cantiere si apre.

---

### Il perimetro è a due livelli, e almeno uno c'è

`billing_account_id` e `istanza_utility_id` sono facoltativi uno per uno, ma
`chk_sepa_mandati_perimetro` ne vuole **almeno uno**: un mandato «generale del conto», senza
billing account e senza utenza, non è ammesso.

| BA | Istanza | Significato |
| --- | --- | --- |
| valorizzato | nullo | il mandato vale per un billing account |
| valorizzato | valorizzato | il mandato vale per una singola utenza |
| nullo | valorizzato | ⚠️ ammesso dal vincolo, ma il modello non lo prevede |

⚠️ Il terzo caso, **utenza senza billing account**, il database lo accetta: prima di dare per
scontato che ogni riga con `istanza_utility_id` abbia anche il suo billing account, va
verificato.

Per ogni schema c'è **al più un mandato `ATTIVO`** per billing account e al più uno per utenza
(due indici unici parziali).

---

### 🔒 Il perimetro di lettura non è ancora deciso

La tabella non ha row security. Il predicato che sembra ovvio, il conto, è sbagliato: il
`soggetto_ruolo_conto_id` è il conto del **cliente** da addebitare, non quello dell'azienda,
quindi il perimetro giusto è il billing account. Ma il billing account è facoltativo, e un
mandato senza resterebbe fuori da qualunque policy costruita su quella chiave: prima si decide se
quel nulla sia ammesso davvero. Il debito è registrato in `dbops.rls_perimetro_debito`.

---

### Il ciclo di vita sta nello stato e nelle date, tenuti insieme solo in parte

`stato` nasce `IN_VALIDAZIONE` e vale uno fra `IN_VALIDAZIONE`, `ATTIVO`, `SOSPESO`, `REVOCATO`,
`SCADUTO`. Le tre date `data_firma`, `data_attivazione`, `data_revoca` sono facoltative.

Che cosa il database tiene allineato:

* le date sono in ordine: firma ≤ attivazione ≤ revoca, quando ci sono (`chk_sepa_mandati_date`);
* un mandato `ATTIVO` ha la data di attivazione (il guard, `E_DATA_ERRATA`).

⚠️ Che cosa **non** tiene allineato: nessun vincolo lega `REVOCATO` a `data_revoca`, e nessuno
impedisce a un mandato `ATTIVO` di avere `data_revoca` valorizzata. Chi verifica se un mandato è
utilizzabile guarda **entrambi** gli assi, finché la coerenza non sarà imposta quando il dominio
entra in esercizio.

`creditor_id` è l'identificativo del creditore SEPA; è facoltativo perché di norma è unico per
gestore e configurato altrove. `iban_snapshot` e `intestatario_snapshot` fotografano il conto al
momento del mandato; UMR e IBAN vengono ripuliti dagli spazi, e l'IBAN portato in maiuscolo, prima
della scrittura.

---

### Codici errore

* `E_DATA_ERRATA` — un mandato `ATTIVO` senza `data_attivazione` (dal guard).

---

### Test

Nessun file pgTAP presidia la tabella direttamente: compare in
`db/pgtap/dbops/test-stati-check-scrittori-v1.sql` come tabella esente dal censimento degli
scrittori di stato, perché scrittori non ne ha.

---

### Note di migrazione

* 2026-08-21 — la tabella risulta vuota: la struttura è pronta, i mandati no.
* 2026-09-09 — il perimetro di lettura entra nel registro del debito RLS.
* 2026-09-21 — i valori di `stato` sono dichiarati esenti dal censimento degli scrittori: la
  tabella è candidata a un'analisi sui dati senza modello, da decidere a parte.

---

{% include-markdown "signature-core.md" %}
