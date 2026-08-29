## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_registro_documento`

> 👀 **Vedi anche**
>
> [vendite.fn_lookup_registro_id](/dbzero/vendite/funzioni/fn_lookup_registro_id) — la ricerca del sezionale
> [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key) — chi la usa per SCRIVERE
> [vendite.vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) — chi la usa per LEGGERE
> [vendite.fn_calcola_data_documento](/dbzero/vendite/funzioni/fn_calcola_data_documento)
> [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)

---

### 🎯 Scopo Principale

**Su quale sezionale nascerà un documento, e con quale politica di data.**

È la catena completa, dagli ingressi grezzi: dal billing account della riga fino
al registro, alla serie e alla politica della data.

```sql
SELECT * FROM vendite.fn_resolve_registro_documento(
    p_billing_account_id_riga => 173,
    p_tipo_doc_fiscale_id     => 1,
    p_natura_doc_id           => 1);
```

⭐ **La usano in due, ed è tutto il punto**: chi **scrive** la fattura
(`fn_build_fattura_key`) e chi la **mostra in lista** (le viste della Dashboard
Competenza, per la colonna «data prevista»). La previsione a video e il documento
vero non coincidono perché due implementazioni si comportano uguale — coincidono
perché **è la stessa funzione**.

---

### ⛔ I due ancoraggi

È il motivo per cui questa funzione esiste. La catena legge **due cose da due
billing account diversi**:

| Cosa | Da dove |
| --- | --- |
| il **billing account di fatturazione** | dal **PADRE**, quando c'è (altrimenti la riga stessa) |
| la **utility** | dalla **RIGA** |

⚠️ **Chi ricopia la catena a occhio li scambia, e il difetto è silenzioso**: la
lista mostrerebbe un sezionale e la fattura ne prenderebbe un altro. Nessun
errore, nessun segnale — solo un documento sul registro sbagliato.

> ⭐ È la ragione della regola di questo cantiere: *si condivide la funzione, non
> una copia della sua logica*.

#### Dove il rischio è vero, e dove non lo è

| Asse | Padre e figlio possono differire? | |
| --- | --- | --- |
| **emittente** | ⛔ **no** | `anagrafiche.fn_guard_albero_ba_emittente` lo impone — due trigger, verso il padre **e** verso i figli, e nessun interruttore per disattivarlo |
| **utility** | ✅ **sì** | `billing_account.utility_id` è obbligatoria ma **nessun vincolo** la lega fra padre e figlio |

⇒ Il rischio vive **sulla utility**, non sull'emittente. Ed è uno dei due assi
con cui si sceglie il sezionale: è lì che scambiare gli ancoraggi cambia
davvero la risposta.

---

### ⛔ Il parametro si chiama `p_billing_account_id_riga` apposta

Dev'essere il billing account **della riga**, perché è da lì che esce la utility.
Il padre lo calcola la funzione.

⚠️ Chi legge la firma e passa il `ba_fatturazione_id` — che la vista gruppi
espone già, a portata di mano — ottiene una previsione **plausibile e sbagliata**
esattamente sui billing account con padre, cioè nei casi non banali. Il nome è
l'unico presidio possibile contro quell'errore.

---

### Cosa restituisce

| Colonna | |
| --- | --- |
| `ba_fatturazione_id` | il padre, quando c'è |
| `utility_id` | quella della riga |
| `emittente_soggetto_ruolo_id` | risolto dal billing account di fatturazione |
| `registro_id`, `serie` | il sezionale e l'eventuale override di serie |
| `politica_data_documento` | *quando* il documento sarà datato |

⭐ **Gli anelli intermedi escono di proposito.** A `fn_build_fattura_key` servono
per comporre la chiave del documento e per il collegamento al reseller: senza,
dovrebbe ricalcolarseli — e i due ancoraggi tornerebbero a essere scritti in due
posti, cioè il difetto che questa funzione toglie, spostato di un metro.

---

### ⛔ Non ferma sui dati

Tipo documento assente, natura non risolvibile, sezionale non mappato, billing
account non raggiungibile: **tutto esce vuoto**. È ciò che la rende utilizzabile
da una vista.

I cancelli restano dove serve fermare, cioè sul percorso di **scrittura**: è
`fn_build_fattura_key` a richiamare le funzioni che sollevano quando emittente o
registro non si risolvono — e a pagare quella seconda risoluzione **solo quando
si sta già andando in errore**.

L'unica eccezione è il **controllo sul parametro**: un billing account vuoto o
non positivo non lo produce nessuna interfaccia, quindi è un guasto di programma
e si ferma subito, con un codice tecnico.

#### ⛔ Billing account non visibile: si ferma, non ripiega

`anagrafiche.billing_account` ha le regole di visibilità per riga, e questa
funzione gira **con i permessi di chi la chiama**: per un operatore fuori
perimetro quella riga **non c'è**.

⚠️ Se in quel caso tirasse dritto, utility ed emittente sarebbero entrambi vuoti,
e la gerarchia a quattro livelli ripiegherebbe sul registro «di chiunque» —
restituendo un sezionale plausibile e sbagliato.

> ⭐ **«Non lo so» è una risposta. «Il registro generico» è una bugia.**

---

### Note operative

- **`STABLE`**, e onestamente: legge e basta, e tutte le funzioni che chiama lo
  sono a loro volta. Serve perché finisce dentro `vw_dash_competenza_attivita`,
  che è la base di altre quattro viste.
- **L'emittente si legge con il lettore puro** (`script.fn_get_ba_emittente_sr_id`)
  e non con l'involucro che solleva. ⚠️ Le due **non** sono intercambiabili in
  generale: l'involucro conserva un ripiego proprio per il caso *senza* billing
  account, che la delegata corto-circuita. Qui la divergenza non si presenta —
  il controllo sul parametro ha già rifiutato il vuoto — ma chi riusa questa
  funzione altrove deve saperlo.
- **Torna sempre una riga**, anche tutta vuota: chi la usa in una vista non deve
  preoccuparsi di perdere righe.

---

### Come la usa la lista

La vista attività la aggancia **solo dove il documento non esiste ancora**
(`af.fattura_riga_id IS NULL`): accanto a una fattura che ha già la sua data,
mostrare cosa succederebbe rifatturando sarebbe una mezza verità.

⚠️ Il discriminante è la **riga di fattura**, non lo stadio: su
`EMESSA_NON_FATTURATA` il documento non c'è ancora, e lì la previsione **serve** —
è lo stadio in cui finiscono le attività rimaste orfane di una fattura
eliminata, cioè lavoro da ri-emettere.

> 📎 Piano e decisioni: `brief-db-registro-e-data-prevista-in-competenza`, DB-1.
