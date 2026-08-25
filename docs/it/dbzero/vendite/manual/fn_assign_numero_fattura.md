## 📘 Documentazione Concettuale – Funzione `vendite.fn_assign_numero_fattura`

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
La funzione **`vendite.fn_assign_numero_fattura()`** assegna il progressivo
in base al registro e aggiorna `anno`, `serie` e `numero` sulla testata fattura.

---

### Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* Lock sulla riga fattura per coerenza.
* `anno` ricavato da `vendite.fn_get_anno_registro`.
* Numero ottenuto da `vendite.fn_get_next_progressivo`, a cui si passa anche
  `p_fattura_id` — serve al **bersaglio** del cancello di monotonia.
* La **serie** si risolve qui, con `COALESCE(f.serie, r.serie_default, '')`: è il
  punto in cui il sezionale di un documento viene deciso, ed è il motivo per cui
  il `JOIN` su `registri_fatturazione` resta.

---

### Output

Ritorna una riga con:

* `registro_id`
* `anno`
* `serie`
* `numero`

⚠️ **`mese` è uscito dal ritorno il 2026-08-25** — vedi la revisione in fondo.

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_assign_numero_fattura(
  p_fattura_id => 123
);
```

---


---

### 🔄 rev 2026-08-18 — la SETTIMA condizione del guard D-K

Brief: `brief-design-note-credito-resi` (slice **N11**, §12.4-bis.6).

```text
natura = NOTA_CREDITO   ⟺   totale_a_pagare ≤ 0
```

#### Da convenzione a invariante verificato

Con la decisione D-NC-2 il segno della nota di credito **vive nel numero**:
quantità negativa in catena, totale del documento negativo, e nessun consumatore
deve sapere che una riga «RETTIFICA» va sottratta. È una scelta forte, e fin qui
era una **convenzione**: nulla verificava che un documento dichiarato
`NOTA_CREDITO` avesse davvero un saldo non positivo.

⭐ Il guard D-K gira **prima che il progressivo venga consumato** — cioè prima
del punto in cui la guida dice che l'errore diventa irreparabile: *«un numero
fiscale valido su un documento invalido si ripara solo con una nota di
variazione»*. È esattamente il posto dove metterla, e chiude il cerchio con la
FatturaPA, dove lo stesso invariante si legge `TipoDocumento = TD04 ⟺
totale_doc < 0`.

#### ⚠️ Due scelte dentro la condizione

1. **Lo zero è ammesso da entrambe le parti.** L'equivalenza scritta con `≤`
   renderebbe incoerente una fattura a saldo nullo, che è strana ma non
   sbagliata — e vietarla qui sarebbe una regola **inventata da questo guard**
   invece che decisa. Si presidia il **segno**, non l'importo;
2. **La seconda metà dice «diverso da NOTA_CREDITO», non «uguale a FATTURA»**:
   così copre anche `NOTA_DEBITO` senza doverla nominare, ed è letteralmente il
   verso ⟸ dell'equivalenza — un totale negativo può appartenere solo a una nota
   di credito.

#### Cosa questa condizione NON fa

Non verifica che la nota di credito abbia le rate a zero: lo fa già la
**condizione 4** (*«un documento non positivo non si rateizza»*), ed è scritta
`<= 0`, non «assumo positivo». ⭐ Il documento a saldo negativo non è un caso che
qualcuno deve insegnare alla catena — è un caso che la catena **contempla già**.

---

### 🔄 rev 2026-08-25 — il bersaglio del cancello, e via il `mese`

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-8** e **DB-12**).
Due modifiche in un solo `DROP` + `CREATE`, perché la seconda lo richiedeva
comunque.

#### 1. Si passa `p_fattura_id` a `fn_get_next_progressivo`

Dal 2026-08-25 quella funzione ospita il **cancello di monotonia**: rifiuta un
numero a un documento la cui data è anteriore all'ultima già numerata sul
sezionale. L'errore porta un **bersaglio**, e senza questo parametro il primo
elemento — *quale* documento ha rifiutato — non ci sarebbe.

⭐ Non è un dettaglio di comodità. Questa funzione gira **dentro il giro di
lotto**, su molte fatture: la frase del rifiuto dice da quale data ripartire, e
senza il bersaglio nessuno direbbe **su quale documento** è successo.

#### 2. `mese` esce dal `RETURNS TABLE`

Da cinque colonne a quattro. Era calcolato da `reset_policy`, che prometteva tre
comportamenti e ne implementava uno, e non lo leggeva nessuno — il backend drena
il result set, i pgTAP leggono per nome. Con lui è caduta l'ultima lettura di
`reset_policy` in questa funzione.

⛔ **Ma il `JOIN` su `registri_fatturazione` RESTA**, al contrario di quanto fatto
in `fn_numera_fattura_opz_emessa`. Lì portava solo `reset_policy`; qui porta
anche `serie_default`, cioè **il punto in cui la serie di un documento si risolve
davvero**.

⚠️ E quella risoluzione — `COALESCE(f.serie, r.serie_default, '')` — dev'essere
**identica** in tutti e tre i posti che la usano: qui, in
`fn_get_data_minima_numerabile` e nel backfill di `ultima_data`. Se una delle tre
diverge, cerca una riga di contatore che non esiste e risponde «nessun vincolo».
📌 Misurato il 2026-08-25: **tutte** le fatture non ancora numerate hanno
`f.serie IS NULL` e prendono la serie dal registro — quindi è proprio il caso
normale, non un bordo.

#### Adesso prima del numero ci sono DUE cose

| | domanda | dov'è |
| --- | --- | --- |
| guard **D-K** | il documento *merita* un numero? | qui, fuori dal lock |
| **cancello** | la data può stare in fondo alla sequenza? | in `fn_get_next_progressivo`, **sotto l'advisory lock** |

E va bene così: il D-K guarda **la fattura**, il cancello guarda **la sequenza**.
Solo il secondo ha bisogno del lock.

---

{% include-markdown "signature-core.md" %}
