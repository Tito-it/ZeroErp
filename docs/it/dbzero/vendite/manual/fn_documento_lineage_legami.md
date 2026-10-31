## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_legami`

> 👀 **Vedi anche**
>
> • [vendite.fn_documento_lineage](fn_documento_lineage.md) — il pannello «Passaggi», che la legge (colonna `is_legame_ritirato`)
> • [vendite.fn_documento_lineage_sintesi](fn_documento_lineage_sintesi.md) — la sintesi delle liste e della barra, che scarta gli archi ritirati
> • [vendite.fn_documento_lineage_nodi](fn_documento_lineage_nodi.md) — la gemella: i nodi danno lo stato, questa il legame
> • [vendite.fn_documento_lineage_archi](fn_documento_lineage_archi.md) — la grammatica degli archi, da cui vengono le lettere

---

### 🎯 Scopo Principale

(nata il 2026-10-13, richiesta R-17/R-18 del backend, dal collaudo)

**Il legame di un arco è ancora vivo?** Un arco della lineage dice due cose
diverse, e prima ne diceva una sola:

* «il documento dall'altra parte è vivo?» — lo dice il **nodo** (`to_is_abortito`);
* «quello che **questo** documento ha portato dall'altra parte è ancora lì?» — lo
  dice questa funzione.

Coincidono quando un documento si annulla. Divergono quando si ritira un
documento da una commessa che resta viva: il preventivo è annullato, le sue
righe di commessa sono annullate, e la commessa continua per gli altri.

Risposta per arco: `true` (ritirato), `false` (vivo), `NULL` per una lettera che
la funzione non conosce: «non so», mai «vivo».

### 🧭 Il censimento, arco per arco

| Arco | Da → a | Ritirato quando | Con i due nodi vivi? |
| --- | --- | --- | --- |
| B, E, F, U | preventivo, ordine, contratto, bolla → commessa | nella commessa non resta nessuna riga del documento con stato diverso da `ANNULLATA` | ✅ sì: il ritiro all'annullo del documento |
| A | preventivo → ordine | nessuna riga **attiva** dell'ordine viene da una riga del preventivo | ✅ sì: l'ordine in bozza perde quelle righe |
| R | bolla → reso | nessuna riga **attiva** del reso viene da una riga della bolla | ✅ sì: il reso in bozza perde le righe |
| H | ordine → bolla | nessuna riga **attiva** della bolla evade una riga dell'ordine | calcolato, ma oggi solo col ritiro della bolla: una riga evasa non si spegne né si cancella |
| C, D | offerta → contratto / ordine | — `false` | ⛔ no: il legame è solo di testata |
| V | revisione d'offerta: madre → figlia (dal 31-10-2026) | — `false` | ⛔ no: il legame è solo di testata (`revisione_padre_id`) |
| G, N, S, T | commessa → fattura, fattura → nota di credito, reso → fattura, reso → riconsegna | — `false` | ⛔ no: l'arco nasce dalle righe di legame e sparisce con loro |

⚠️ **Una riga EMESSA è viva.** Lì il documento è stato fatturato, e quella è
storia viva, non ritirata.

⚠️ **La chiave.** Le righe di commessa portano l'`uid` della testata del
documento (la stessa chiave con cui le legge e le ritira
`fn_documento_legami`), mentre l'arco porta la chiave canonica del nodo (`uid`
per il preventivo, `id` per ordine, contratto e bolla). La funzione le traduce.

### 🧭 Chi la legge, e cosa ne fa (D-15 di Tid, 2026-10-13)

| Chi | Con un legame ritirato |
| --- | --- |
| `fn_documento_lineage` (pannello «Passaggi») | l'arco **resta**, come storia, con `is_legame_ritirato = true`: il frontend lo indica |
| `fn_documento_lineage_sintesi` (liste, barra) | l'arco **si scarta**: non è una destinazione né una sorgente, quindi non conta per frontiera, discendenti, «transitato», sorgenti e radice |
| la barra dei collegamenti (frontend) | il chip non conta, come per un documento annullato |

### ⛔ Perché SECURITY DEFINER

Righe di commessa, di ordine, di bolla e di reso hanno la RLS. Sotto quella di
chi legge, righe vive fuori perimetro sparirebbero, e l'arco direbbe «ritirato»
a torto. La funzione restituisce un booleano per un arco che chi legge ha già:
nessun dato in più.

Presidio: `db/pgtap/vendite/test-lineage-legame-ritirato-v1.sql`. Il test 2
pretende che ogni lettera della grammatica degli archi abbia il suo ramo: un arco
nuovo senza ramo diventa rosso lì.

{% include-markdown "signature-core.md" %}
