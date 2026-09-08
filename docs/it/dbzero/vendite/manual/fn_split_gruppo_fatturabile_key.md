## 📘 Documentazione Concettuale – Funzione `vendite.fn_split_gruppo_fatturabile_key`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — **la gemella, da leggere insieme**
> • [vendite.fn_riferimento_gruppo_fatturabile](/dbzero/vendite/funzioni/fn_riferimento_gruppo_fatturabile)
> • [vendite.fn_get_sorgente_documento_ref](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Il **verso inverso** di
[`fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key):
da una chiave di gruppo torna ciò da cui è stata costruita.

| Chiave | Torna |
| --- | --- |
| `<codice_interno>:<uid>` | la coppia `(sorgente_tipo_id, sorgente_uid)` |
| `MAN:<commessa_id>` | la commessa |
| qualsiasi altra cosa | tre `NULL` |

---

### Perché esiste

Chi legge una **segnalazione** ha in mano solo la chiave: `gruppo_key` è tutto
ciò che `vendite.fatturazione_lotti_log` e `vendite.fatturazione_lotti_esiti`
contengono. Per mostrare il **numero** del documento bisogna tornare alla
sorgente, e prima del 2026-09-08 quella strada non c'era.

---

### ⛔ Le due funzioni sono gemelle e si leggono insieme

Il prefisso `MAN` e la forma della chiave sono decisi **nella funzione che
costruisce**. Qui si **rileggono**.

⚠️ È una duplicazione che nessun occhio può presidiare, quindi non la presidia
l'occhio: il presidio è un pgTAP di **andata e ritorno** —
`split(build(x)) = x` su entrambe le forme. Se la forma cambia da una parte e
non dall'altra, quel test diventa rosso.

> Ed è lo stesso argomento che la doc della gemella usa per vietare la
> scorciatoia opposta: *«non derivarla da `segment_key`: i prefissi sono una
> convenzione di leggibilità, non un contratto — ricavarne il gruppo con
> `split_part` creerebbe un accoppiamento a una regola di formattazione che
> nessuno si è impegnato a mantenere»*. Vale identico al contrario, e per questo
> lo split è una funzione **dichiarata** invece che una riga sparsa.

---

### Regole

* ⛔ **Non solleva mai.** La chiama una lista: una chiave storta deve produrre un
  ripiego, non una lista rotta. Torna **sempre una riga**, con tre `NULL` quando
  non riconosce la forma;
* ⚠️ usa `substr` e non `split_part` sul resto della chiave: una chiave
  malformata con un secondo `:` verrebbe **troncata in silenzio**, e un
  troncamento silenzioso è peggio di un ripiego dichiarato;
* l'aggancio della sorgente è su **`codice_interno`** (immutabile), mai su
  `codice` (linee-guida-sql §6c/§6d): al primo rename fatto dall'utente la
  risoluzione smetterebbe **senza dire niente**;
* nessun filtro su `attivo`: un documento nato da una sorgente poi disattivata
  resta quel documento, e la segnalazione che lo nomina va letta comunque;
* `STABLE`, `SECURITY INVOKER`.

---

### ⚠️ Non risale a `commesse_attivita`, ed è una scelta

Sembra la via ovvia: cercare la riga di commessa la cui chiave combacia. Ma la
`gruppo_key` scritta su una segnalazione è un **fatto storico**, e quel lavoro
può essere già fatturato, annullato o uscito dal giro: la risoluzione si
svuoterebbe **proprio dopo** — e una segnalazione si legge dopo.

⭐ Spacchettare la chiave dipende solo dal **documento**, che resta.

---

### Esempio d'uso

```sql
SELECT * FROM vendite.fn_split_gruppo_fatturabile_key(
    'ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626');
-- sorgente_tipo_id | sorgente_uid                         | commessa_id
--               12 | 01a06ce4-35a6-721a-9cd8-9da48bf77626 | NULL

SELECT * FROM vendite.fn_split_gruppo_fatturabile_key('MAN:42');
-- NULL | NULL | 42
```

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md` §6.2.

---

{% include-markdown "signature-core.md" %}
