## 📘 Documentazione Concettuale – Tabella `pagamenti.sepa_mandati`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

I **mandati SEPA** (schemi `CORE` e `B2B`): l'autorizzazione con cui il debitore permette al
creditore di addebitare il proprio conto. Senza un mandato valido un addebito diretto non si
può disporre — è il documento che rende l'incasso legittimo.

Ogni mandato lega un **conto di ruolo** (`soggetto_ruolo_conto_id`, `NOT NULL`) a un
perimetro, e porta l'`umr` — *Unique Mandate Reference*, il codice che identifica il mandato
verso la banca.

---

### ⚠️ Oggi è **vuota**

Misurato il 2026-08-21: **zero righe**. Il ciclo incassi non è ancora in esercizio; la
struttura è pronta, i mandati no.

---

### Il perimetro è a **due livelli, entrambi opzionali**

`billing_account_id` e `istanza_utility_id` sono **entrambi nullable**, e la combinazione dice
quanto è largo il mandato:

| BA | Istanza | Significato |
|---|---|---|
| nullo | nullo | mandato **generale** del conto |
| valorizzato | nullo | limitato a un billing account |
| valorizzato | valorizzato | limitato a una singola utenza |

⚠️ Nessun vincolo impedisce **istanza senza BA**: una combinazione che il modello non prevede
ma che il database accetta. Da tenere presente prima di dare per scontato che ogni riga con
`istanza_utility_id` abbia anche il suo billing account.

---

### Il ciclo di vita è nelle date, non solo nello stato

`stato` nasce `'IN_VALIDAZIONE'`, ma la storia vera la raccontano le tre date:
`data_firma`, `data_attivazione`, `data_revoca` — tutte nullable.

⚠️ Stato e date sono **due assi separati**, senza un vincolo che li tenga allineati: un
mandato può risultare attivo per stato e avere `data_revoca` valorizzata. Chi verifica se un
mandato è utilizzabile dovrebbe guardare **entrambi**, o la coerenza andrebbe imposta con un
CHECK quando il dominio entrerà in esercizio.

`creditor_id` è l'identificativo del creditore SEPA, nullable perché tipicamente è unico per
gestore e configurato altrove.

---

{% include-markdown "signature-core.md" %}
