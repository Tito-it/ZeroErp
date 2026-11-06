## 📘 Documentazione Concettuale – Funzione `dbops.fn_nome_qualificato`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_fusione_figlie](/dbzero/dbops/funzioni/fn_fusione_figlie) — la usa nei messaggi e per l'ordine
> * [dbops.fn_fusione_righe_doppie](/dbzero/dbops/funzioni/fn_fusione_righe_doppie) — la usa nel SQL dinamico
> * [dbops.fn_fusione_ripunta_figlie](/dbzero/dbops/funzioni/fn_fusione_ripunta_figlie) — la usa nel SQL dinamico e nelle chiavi del riepilogo

---

### 🎯 Scopo Principale

Dà il nome di una tabella (o di un indice, di una vista) **sempre con il suo schema**:
`schema.nome`, con le virgolette dove servono. Lo legge dal catalogo, quindi non dipende da chi lo
chiede.

---

### ⚠️ Perché non basta `regclass::text`

`regclass::text` toglie lo schema quando lo schema sta nel `search_path` di chi chiama. Lo stesso
oggetto si scrive allora in due modi: `anagrafiche.indirizzi_dettaglio` per chi non ha
`anagrafiche` nel percorso, `indirizzi_dettaglio` per l'applicazione, che ce l'ha. Ne seguono due
guai:

* una chiave o un messaggio composti col nome cambiano a seconda di chi lancia la funzione;
* un nome senza schema rimesso in un SQL dinamico si risolve col `search_path` di chi chiama: una
  tabella temporanea con lo stesso nome, che viene prima nel percorso, prenderebbe il posto di
  quella vera.

Dove un nome si scrive o si rimette in un SQL, si usa questa funzione.

---

### Che cosa restituisce

Il nome qualificato, oppure niente (`NULL`) se l'identificativo non è una relazione. Per una
tabella temporanea lo schema è quello temporaneo della sessione (`pg_temp_N`).

---

### Test

`db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 6, 10 e 27: le righe doppie, la riga
d'audit e il riepilogo del ripuntamento nominano le tabelle con lo schema anche col `search_path`
dell'applicazione.

---

{% include-markdown "signature-core.md" %}
