## 📘 Documentazione Concettuale – Funzione `vendite.fn_elimina_fattura_da_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids)  
> • [script.fn_check_fattura_eliminabile_da_lotto](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto)  
> • [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft)  
> • [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft)  

---
### 🎯 Scopo Principale
(latest review 04-08-2026)  
Toglie **una sola fattura** da un lotto **cancellandola**, senza toccare il lotto né le
altre fatture. È il verbo per il caso in cui un documento è sbagliato e va rifatto,
mentre il resto del giro è sano.

> ⚠️ **Rinominata il 2026-08-04** da `fn_elimina_fattura_da_lotto_draft`. Il «draft» era
> riferito al **lotto**, che non deve più essere in bozza: ora basta che sia
> pre-fiscale. Un nome che non dice più la verità è un bug che aspetta — è la terza
> rinomina della famiglia per questa stessa ragione.

---

### Il perimetro: pre-fiscale, non «bozza»

Sia il **lotto** sia la **fattura** devono essere `DRAFT` o `EMESSA`, cioè non ancora
numerati. È lo stesso confine delle due sorelle che lavorano sul lotto intero.

Fino al 2026-08-04 il lotto doveva essere in `DRAFT`. Era il perimetro sbagliato, e si
vedeva in-app: il drawer proponeva la voce di riga su qualunque lotto con una fattura
pre-fiscale — quindi anche sui lotti `EMESSA` — e lì la chiamata **falliva**. Il caso che
motiva l'azione è proprio quello: la fattura critica rimasta indietro in un lotto emesso.

---

### 🔴 Togliere vuol dire cancellare (RD-7)

Non esiste un modello «reperto»: la fattura non viene staccata e conservata, viene
**eliminata** insieme a righe, riepiloghi, note, log e collegamento al lotto. Le sue
attività tornano libere e rientreranno nel giro successivo.

La ragione è la coerenza: riportare in bozza un lotto **intero** cancella già le sue
fatture emesse. Sarebbe strano che la stessa operazione, fatta su **una** riga, lasciasse
in archivio un documento vuoto.

> ⚠️ **La cancellazione non lascia traccia del contenuto.** `vendite.fatture` non è
> storicizzata (il flag è spento di default e nessuno lo accende): dopo l'operazione non
> è più possibile sapere cosa diceva quel documento. Resta la riga del **ponte**, quella
> sì storicizzata, che registra «la fattura X era in questo lotto ed è uscita».

---

### Regole principali

* `p_lotto_id` e `p_fattura_id` obbligatori e `> 0`.
* Le precondizioni **non sono scritte qui**: arrivano da
  `script.fn_check_fattura_eliminabile_da_lotto`, che è anche la sorgente dei messaggi.
  Si solleva il codice del **primo** motivo, con l'elenco completo nel contesto.
* La pulizia è **tutta** di `vendite.fn_cleanup_fatture_by_ids`: questa funzione decide
  *cosa* si toglie, non *come* si ripulisce.
* ⚠️ Alla primitiva si passa **`NULL`** come `lock_batch_id` (C-22): passando quello del
  lotto si libererebbero anche le attività delle **altre** fatture, che invece restano
  dove sono.
* **Non** modifica lo stato del lotto.

---

### Errori

| Codice | Quando |
| --- | --- |
| `E_LOTTO_NON_PRE_FISCALE` (831) | il lotto è oltre il pre-fiscale |
| `E_FATTURA_NON_COLLEGATA_AL_LOTTO` (832) | la fattura non appartiene a quel lotto |
| `E_FATTURA_GIA_FISCALE` (833) | la fattura è oltre il pre-fiscale |
| `E_FATTURA_GIA_NUMERATA` (834) | la fattura ha già un numero |
| `E_LOTTO_NON_TROVATO` / `E_FATTURA_NON_TROVATA` | identificativi inesistenti |
| `E_PARAMETRO_INVALIDO` | parametri assenti o `<= 0` |

---

### Output

Ritorna una riga con quattro contatori:

* `updated_attivita` — attività sbloccate
* `deleted_fatture`
* `deleted_righe`
* `riemesse_attivita` — attività di commessa tornate `NON_EMESSA`

Il quarto è separato dal primo di proposito: un numero unico direbbe «dieci cose fatte»
senza distinguere le attività sbloccate da quelle rimesse in coda, che per il cockpit
sono fatti diversi.

---

### Esempio d'uso

```sql
SELECT *
FROM vendite.fn_elimina_fattura_da_lotto(
  p_lotto_id => 123,
  p_fattura_id => 456
);
```

---

{% include-markdown "signature-core.md" %}
