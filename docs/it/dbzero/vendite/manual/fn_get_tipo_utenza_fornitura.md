## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_tipo_utenza_fornitura`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_contratto_attivo](/dbzero/vendite/funzioni/fn_get_contratto_attivo)
> • [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga)
>
**Approfondimento tabelle:**
>
• [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)
> • [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)

---
### 🎯 Scopo Principale
(latest review 30-08-2026)

Dice **a che uso è destinata una fornitura** a una certa data: domestico,
industriale, agricolo… Il tipo d'uso è ciò che, in alcuni settori, cambia
l'aliquota IVA a parità di merce.

È l'anello che mancava fra la fornitura e il suo trattamento fiscale.

---

### Il problema che risolve, in una frase

Il tipo d'uso **non sta sulla fornitura**: sta sul **contratto** che la governa
(`vendite.contratti_utilities.tipo_utenza_id`). Ma nessuna testata di documento —
DDT, ordine, preventivo, fattura — porta un riferimento al contratto: portano
invece la terna *cliente / fornitura / utility*.

> ⭐ **Ecco perché la firma è `(billing_account, utility, data)` e non
> `contratto_id`.** Una firma che pretendesse il contratto avrebbe obbligato ogni
> chiamante a trovarselo da solo — cioè a riscrivere il predicato «contratto
> attivo» in cinque posti diversi. Qui il passaggio dal contratto è un
> **dettaglio interno**, e il chiamante passa quello che ha già in mano.

---

### Regole principali

* Trova il contratto in vigore alla data con
  `vendite.fn_get_contratto_attivo`, poi ne legge il tipo d'uso.
* ⚠️ **La data è un parametro, mai `CURRENT_DATE`**: su un documento vecchio conta
  l'uso di allora.
* Ritorna `NULL` quando non c'è un contratto attivo, **oppure** quando quel
  contratto non dichiara un tipo d'uso. ⭐ Le due cose non si distinguono di
  proposito: per chi chiama significano la stessa cosa — «da qui non arriva
  nessuna risposta».
* Sola lettura.

---

### ℹ️ Non tutte le forniture hanno un tipo d'uso, ed è corretto

La dimensione tipo/classe esiste **se e solo se** quella utility ha dei tipi
d'uso a catalogo. Dove non li ha, il contratto non li dichiara e questa funzione
ritorna `NULL` — non è un dato mancante, è una fornitura di specie diversa.

---

### Output

L'identificativo del tipo d'uso (`integer`), oppure `NULL`.

---

### Esempio d'uso

```sql
SELECT vendite.fn_get_tipo_utenza_fornitura(
  p_billing_account_id => :billing_account_id,
  p_utility_id         => :utility_id,
  p_data_riferimento   => :data_documento
);
```

---

{% include-markdown "signature-core.md" %}
