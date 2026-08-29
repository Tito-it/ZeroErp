## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_contratto_attivo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_tipo_utenza_fornitura](/dbzero/vendite/funzioni/fn_get_tipo_utenza_fornitura)

---
### 🎯 Scopo Principale
(latest review 30-08-2026)

Risponde a una domanda sola: **«quale contratto è in vigore per questa fornitura,
a questa data?»**

Una fornitura è la coppia *cliente da fatturare* + *utility*
(`billing_account_id`, `utility_id`). Nel tempo può avere più contratti — uno
chiuso, uno nuovo, uno annullato. Questa funzione dice **quale vale adesso**, o
meglio: quale valeva **alla data che le si passa**.

---

### Perché esiste come funzione a sé

⭐ **Non introduce niente di nuovo: estrae qualcosa che già c'era.**

Lo stesso identico predicato — «contratto di questa fornitura, valido a questa
data, in stato `ATTIVO`» — viveva **scritto a mano dentro il nucleo del calcolo
prezzi**. Serviva anche altrove, e riscriverlo una seconda volta avrebbe creato
due definizioni di «contratto attivo» destinate a divergere in silenzio: basta che
un giorno qualcuno aggiunga uno stato, o cambi il modo di leggere la validità, e
le due risposte smettono di coincidere senza che nulla protesti.

> ⚠️ **L'estrazione è stata verificata sul comportamento, non sulla lettura**: 47
> esiti di calcolo prezzi confrontati prima e dopo, identici su tutti i campi, e
> il contratto scelto dal pricing coincidente con quello che ritorna questa
> funzione.

---

### Regole principali

* **Tutti e tre i parametri sono obbligatori.** Con uno mancante non c'è una
  domanda da porre, e la funzione ritorna `NULL` invece di indovinare.
* Il contratto deve avere lo stato con `codice_interno = 'ATTIVO'`.
* La validità si legge dal periodo del contratto: **deve contenere la data**
  passata.
* ⚠️ **La data è un parametro, mai `CURRENT_DATE`.** Su un documento di sei mesi
  fa la domanda è «quale contratto valeva allora», non «quale vale oggi».
* Se ne trova più d'uno, ritorna **il più recente** in modo deterministico.
* Ritorna `NULL` se non c'è nessun contratto attivo: **non è un errore**, è la
  risposta.

---

### Output

L'identificativo del contratto (`bigint`), oppure `NULL`.

---

### Esempio d'uso

```sql
SELECT vendite.fn_get_contratto_attivo(
  p_billing_account_id => :billing_account_id,
  p_utility_id         => :utility_id,
  p_data_riferimento   => :data_documento
);
```

---

{% include-markdown "signature-core.md" %}
