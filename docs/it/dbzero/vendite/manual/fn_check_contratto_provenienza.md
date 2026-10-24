## 📘 Documentazione Concettuale – Funzione `vendite.fn_check_contratto_provenienza`

> 👀 **Vedi anche**
>
> • [vendite.trgfn_attivita_guard_contratto](/dbzero/vendite/manual/trgfn_attivita_guard_contratto) — il guard che la legge e solleva
>
> • [vendite.fn_check_listino_provenienza](/dbzero/vendite/manual/fn_check_listino_provenienza) — l'altra metà della provenienza del prezzo (versione e riga di listino)
>
> • [vendite.fn_get_contratto_attivo](/dbzero/vendite/funzioni/fn_get_contratto_attivo) — come il prezzo sceglie il contratto

### 🎯 Scopo Principale

(rev 2026-10-21, richiesta del backend sullo smoke del raggruppamento per contratto, decisione
di Tid D-1)

Dice se il **contratto** citato da una riga di commessa (o dalla sua attività fatturabile) come
provenienza del prezzo è ammesso. Restituisce il codice del motivo per cui non lo è, oppure
`NULL` se va bene.

| Codice | La regola |
| --- | --- |
| `E_ATTIVITA_CONTRATTO_INCOERENTE` | il contratto è del **conto di fatturazione** (billing account) della commessa della riga |

Il prezzo da contratto si trova con `vendite.fn_get_contratto_attivo`, che cerca il contratto
attivo **di quel conto di fatturazione**, per l'utility e la data. Una riga che cita il contratto
di un altro cliente porta un prezzo che il sistema non avrebbe mai potuto calcolare.

---

### Perché basta il conto di fatturazione

* **Utility e fornitura seguono da sole**: un contratto è legato alla coppia (conto, fornitura,
  utility) del suo conto, e un conto ha una utility sola.
* **L'azienda segue da sola**: un conto di fatturazione ha una sola azienda emittente, e il
  contratto è già controllato rispetto al suo conto.
* ⛔ **La regola non confronta l'azienda**: l'azienda «di» un conto non ancora collegato
  dipende da chi sta lavorando, l'uguaglianza fra due conti no. Il presidio lo prova: il
  contratto di un **altro cliente della stessa azienda** è rifiutato.

Il conto si legge dalla **commessa**, per tutte e due le tabelle: il prezzo è stato calcolato per
il conto della commessa, e l'emissione copia proprio quel conto sull'attività fatturabile.

---

### Quando non c'è niente da giudicare

Contratto vuoto: `NULL`. È il prezzo che non viene da un contratto (listino, categoria, promo,
prezzo a mano), gli oneri e le rettifiche.

---

### Perché SECURITY DEFINER

Contratti e commesse hanno la sicurezza per riga (RLS) **per azienda emittente**. Letto con i
permessi di chi scrive, il contratto di un'altra azienda tornerebbe a vuoto, e la regola
giudicherebbe un'assenza invece di un valore. La funzione restituisce solo un codice: non rivela
niente del contratto. `search_path` bloccato, nomi qualificati.

È una *check* e non un *guard* (linee-guida-sql §5): non solleva. Solleva il guard che la legge.

---

### 🧪 Il presidio

`db/pgtap/vendite/test-guard-contratto-provenienza-v1.sql`.

---
{% include-markdown "signature-core.md" %}
