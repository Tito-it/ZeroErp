## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_billing_account()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/manual/fn_crea_cliente) ·
> [script.fn_scrivi_riga_da_jsonb](/dbzero/script/manual/fn_scrivi_riga_da_jsonb)

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 5)

**Aprire il conto di fatturazione (billing account) di un cliente per una
utility.** In un'operazione sola:

1. l'**istanza utility** fittizia del soggetto, se non se ne indica una
   esistente;
2. il **billing account**;
3. se chiesto, il **legame del BA a un'azienda emittente**.

Un BA può esistere anche senza la riga del cliente: è la catena minima che i
documenti pretendono. Per il cliente completo c'è
[fn_crea_cliente](/dbzero/anagrafiche/manual/fn_crea_cliente), che usa questa.

### I campi

* **Il BA**: la categoria del cliente (obbligatoria: non ha un default, come
  vuole il listino), e facoltativi il codice (altrimenti generato), la modalità
  di fatturazione degli ordini, il conto padre, la valuta.
* **L'istanza nuova**: facoltativi il codice e l'indirizzo. Nasce sempre
  fittizia: un'istanza vera nasce dal motore delle pratiche. Con un'istanza
  esistente questi campi non si passano.
* Un campo diverso è rifiutato col suo nome (`E_CAMPO_NON_AMMESSO`).

### Il legame all'azienda

* **Con un operatore collegato**, il legame lo scrive il sistema, verso
  l'azienda su cui l'operatore lavora. Se si chiede un'azienda diversa, è un
  errore.
* **Senza nessuno collegato** (il provisioning, le fixture di test), il legame
  lo scrive questa funzione, se l'azienda è indicata.

⚠️ **Un limite di oggi.** Un'istanza ha i BA di una sola azienda, e il
controllo scatta quando il BA nasce, prima del legame chiesto. Senza nessuno
collegato, quindi, un secondo BA su un'istanza esistente con un'azienda
indicata diversa da quella di default non passa. Con un operatore collegato
non succede.

### Che cosa non controlla

Il permesso, il caso «amministratore senza azienda scelta», la coerenza fra il
soggetto e l'istanza: li dicono i controlli della tabella e il backend.

### Test

`db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
