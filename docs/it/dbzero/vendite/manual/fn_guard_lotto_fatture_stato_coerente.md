## 📘 Documentazione Concettuale – Funzione `vendite.fn_guard_lotto_fatture_stato_coerente()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)
>
Approfondimento funzioni:
> • [vendite.trgfn_lotto_fatture_guard_stato_coerente](/dbzero/vendite/funzioni/trgfn_lotto_fatture_guard_stato_coerente)
>
Vista di lavoro correlata:
> • [vendite.vw_lotti_fatture_incoerenti](/dbzero/vendite/views/vw_lotti_fatture_incoerenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-08-04)

**Contiene la regola** dell'invariante «lo stato fiscale delle fatture coincide con quello del
lotto che le contiene». Il dispatcher `trgfn_lotto_fatture_guard_stato_coerente` risolve quali
lotti verificare e delega qui: la regola vive in un posto solo, i punti da cui può essere
violata sono tre.

Riceve un `lotto_id`, e o passa in silenzio o solleva.

---

### Le fatture `critical` sono escluse

Una fattura marcata critica è un'anomalia **già nota e già segnalata**: il suo stato può
legittimamente divergere da quello del lotto, perché è stata messa da parte. È l'unica
eccezione, ed è viva.

⚠️ `COALESCE(f.critical, FALSE)`: una `critical` nulla vale «non critica» e la fattura
**entra** nel controllo. Nel dubbio si presidia.

`IS DISTINCT FROM` e non `<>`: con `<>` una fattura o un lotto con stato `NULL` non
risulterebbe mai diverso, e l'incoerenza peggiore — quella dove lo stato manca — sfuggirebbe.

---

### ⚠️ Tre uscite silenziose, e una è un limite dichiarato

La funzione ritorna **senza controllare nulla** in tre casi:

1. **`p_lotto_id` nullo o `<= 0`** — qui, a differenza delle altre funzioni del progetto,
   *non* solleva `E_PARAMETRO_INVALIDO`: esce e basta. È coerente col fatto che il chiamante è
   un trigger, non una persona;
2. **lotto non trovato** — ⭐ necessario: essendo il check **differito**, il lotto può essere
   stato cancellato nella stessa transazione, e al `COMMIT` la riga non c'è più. Sollevare qui
   farebbe fallire una cancellazione legittima;
3. **`stato_doc_fiscale_id` del lotto è `NULL`** — senza uno stato di riferimento il confronto
   non significa niente.

Il terzo è un **limite documentato**, e va saputo: `vendite.fatturazione_lotti.stato_doc_fiscale_id`
è una colonna **nullable**, quindi un lotto senza stato **non viene mai verificato** — le sue
fatture possono divergere liberamente, e nessun errore lo segnala.

Misurato il 2026-08-21: **zero lotti su 45** hanno stato nullo, quindi oggi il buco non ha
occupanti. Ma è la colonna ad ammetterlo, non i dati a escluderlo.

---

### Il messaggio porta il dettaglio, ma **troncato**

Il conteggio riportato è **completo**; l'elenco delle fatture disallineate è invece limitato a
**20 righe** (`LIMIT 20`, ordinate per `fattura_id`).

⚠️ Su un lotto molto disallineato il messaggio mostra quindi una parte, non il tutto: il
numero e l'elenco possono non tornare, ed è voluto. Per la lista completa si usa
`vw_lotti_fatture_incoerenti`.

---

### ⚠️ Una nota storica

Fino al 2026-08-04 c'erano due predicati su `lf.esclusa` e il campo `esclusa` nel JSONB di
diagnostica. Il flag era **morto**: diceva sempre `false`, quindi occupava spazio nel
messaggio senza informare. Rimossi. La stessa bonifica ha toccato `fn_accoda_stampe_lotto`.

---

{% include-markdown "signature-core.md" %}
