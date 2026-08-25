## 📘 Documentazione Concettuale – Funzione `vendite.fn_numera_fattura_opz_emessa`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)  
> • [vendite.fn_get_anno_registro](/dbzero/vendite/funzioni/fn_get_anno_registro)  
>
### 🎯 Scopo Principale
(latest review 09-02-2026)
La funzione **`vendite.fn_numera_fattura_opz_emessa()`** assegna il numero
fattura in modo **idempotente** e, opzionalmente, imposta lo stato documento
**EMESSA** usando `codice_interno`.

---

### Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* Lock solo sulla riga fattura (minima concorrenza).
* Se la fattura e` gia` numerata, ritorna i valori correnti.
* Il numero e` assegnato tramite `vendite.fn_assign_numero_fattura`.
* Se `p_set_emessa = true`, imposta lo stato documento `EMESSA`.

---

### Output

Ritorna una riga con:

* `registro_id`
* `anno`
* `serie`
* `numero`

⚠️ **`mese` è uscito dal ritorno il 2026-08-25** — vedi la revisione in fondo.

---

### Esempi d’uso

```sql
SELECT *
FROM vendite.fn_numera_fattura_opz_emessa(
  p_fattura_id => 123
);
```

```sql
SELECT *
FROM vendite.fn_numera_fattura_opz_emessa(
  p_fattura_id => 123,
  p_set_emessa => true,
  p_codice_interno_emessa => 'EMESSA'
);
```

---


### ⛔ Il riferimento fiscale deve esistere prima (rev 2026-08-21)

Un documento che **rettifica** le righe di un'altra fattura non si può numerare
finché quella fattura non ha un numero: `E_FATTURA_RETTIFICATA_SENZA_NUMERO`.

⚠️ **Non è una questione di cronologia.** Una nota di credito deve citare numero
e data del documento corretto nel blocco `DatiFattureCollegate` della fattura
elettronica (TD04): con il padre ancora senza numero quel blocco **non è
compilabile**, e la nota nascerebbe già inadatta a partire verso lo SDI. Il
rifiuto arriva **prima** di consumare un numero, che è l'unica cosa che non si
torna indietro.

**Il predicato è per riga, non per documento**: una nota può rettificare righe di
fatture *diverse*, e basta che **una** sia senza numero perché il blocco fiscale
resti incompleto.

⭐ **E non guarda la natura del documento.** Sarebbe stato naturale scrivere «se
natura = NOTA_CREDITO allora…», ed è sbagliato per due motivi: una nota di
**debito** che rettifica ha lo stesso identico problema, e una fattura ordinaria
non ha righe con `riga_rettificata_id` — quindi il predicato sulle righe copre
tutti i casi senza mai bloccare quelli normali.

⛔ **Fail-closed sulla visibilità.** `vendite.fatture` e `vendite.fatture_righe`
hanno la RLS e la funzione è `SECURITY INVOKER`: una fattura rettificata fuori
dal perimetro emittente di chi opera si legge come «non c'è». I JOIN sono quindi
`LEFT` e la riga senza padre visibile **conta come bloccante** — il predicato non
è «risulta non numerata», è «non posso dimostrare che sia numerata».

⚠️ **La guardia sta dopo il ritorno idempotente**: un documento già numerato
continua a rispondere con i suoi valori, anche se il padre perdesse il numero
dopo. Bloccarlo romperebbe ciò che il primo giro ha già fatto bene.

📌 **Chi chiama deve numerare prima i padri.** Il giro di lotto è **fail-fast**:
una fattura che rifiuta ferma l'intero step. Oggi regge per un motivo
strutturale — il backend ordina per `f.id` e la fattura rettificata è sempre più
vecchia della nota, perché la merce deve essere già stata fatturata perché
l'accredito sia possibile — ma è un **invariante implicito**, non una garanzia
scritta. ⛔ Il caso *cross-lotto* invece **deve** fermarsi, ed è la ragione di
questa guardia: se il padre sta in un lotto ancora in bozza, il suo numero non
esiste.

Verifica: `db/pgtap/vendite/test-numera-nota-credito-riferimento-v1.sql`.

---

### 🔄 rev 2026-08-25 — via il `mese` dal ritorno

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-12**).

Il `RETURNS TABLE` passa da cinque colonne a **quattro**: `mese` non c'è più.

**Perché non era mai servito.** Era calcolato da
`registri_fatturazione.reset_policy`, che ammetteva `NESSUNA | ANNUALE | MENSILE`
e ne implementava **una sola**: la chiave del contatore porta `mese = 0` fisso e
`uq_fatture_numero` il mese non lo contiene, quindi `NESSUNA` si comportava come
`ANNUALE` e `MENSILE` pure. ⛔ Un catalogo che promette tre comportamenti e ne fa
uno è peggio di uno con una voce sola: prima o poi qualcuno sceglie `MENSILE` e
un'implementazione a metà finisce in violazione di `UNIQUE`.

✅ **E non lo leggeva nessuno**, verificato uno per uno prima di toglierlo: il
backend drena il result set (due punti in `pipeline_repository.py`, uno scalare e
uno con `fetchall`), i pgTAP leggono **per nome di colonna** o fanno `PERFORM`.
Nessuno legge per posizione.

Con `mese` sono caduti anche la variabile del reset, la data — che serviva solo
al suo `CASE` — e il **JOIN su `registri_fatturazione`**, che portava soltanto
`reset_policy` (era `INNER` e in teoria filtrava; in pratica mai, perché
`registro_id` è `NOT NULL` con una FK).

⚠️ **Cambiare il tipo di ritorno ha richiesto `DROP` + `CREATE`.** E l'ordine
rispetto alla funzione chiamata non è arbitrario: **questa va ricreata PRIMA** di
`fn_assign_numero_fattura`. Togliendo `mese` prima dalla chiamata, ci sarebbe un
istante in cui questa fa `SELECT t.mese FROM fn_assign_numero_fattura(…)` su una
colonna che non esiste più — errore a runtime. Nell'ordine giusto la chiamante
seleziona quattro colonne su cinque, che è legittimo.

---

{% include-markdown "signature-core.md" %}
