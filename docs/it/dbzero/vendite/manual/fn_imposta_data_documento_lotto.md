## 📘 Documentazione Concettuale – Funzione `vendite.fn_imposta_data_documento_lotto`

> 👀 **Vedi anche**
>
> [vendite.fn_get_data_minima_numerabile_lotto](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto)
> [vendite.fn_calcola_data_documento](/dbzero/vendite/funzioni/fn_calcola_data_documento)
> [vendite.trgfn_fatture_guard_data_numerata](/dbzero/vendite/funzioni/trgfn_fatture_guard_data_numerata)
> [vendite.fn_genera_scadenze_fattura](/dbzero/vendite/funzioni/fn_genera_scadenze_fattura)
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)

---

### 🎯 Scopo Principale

**Dichiara la data documento di un lotto** — l'atto che l'operatore compie
davvero: *«questo lotto lo dato al 31 luglio»*.

```sql
SELECT * FROM vendite.fn_imposta_data_documento_lotto(4212, '2026-07-31');
-- aggiornate | saltate_numerate | rate_rigenerate
--         12 |                2 |              12
```

---

### ⭐ È una funzione MADRE

Quattro scritture e una sola lettura, **atomica per costruzione**
(`linee-guida-sql` §5b). Non è una comodità: farle in sequenza dal backend
lascerebbe uno stato intermedio con **una data nuova e le rate vecchie**.

Cosa fa, nell'ordine:

1. verifica il **pavimento** del sezionale (vedi sotto);
2. scrive la data **sul lotto**;
3. la propaga alle fatture **non ancora numerate**;
4. **rigenera i piani rate** di quelle fatture.

---

### ⛔ Il punto 4 non è opzionale

Le scadenze si calcolano **da `f.data`** (`v_data_rata := f.data + offset`) nello
step EMESSA, cioè **prima** che il numero venga assegnato. E il guard D-K
verifica che la **somma** delle rate quadri col totale.

La somma **non cambia** quando cambia la data: cambiano le **date** delle rate.
Quindi una data nuova con rate vecchie **passerebbe in silenzio** — nessun errore,
un piano di pagamento sbagliato.

⚠️ **Ma si rigenera solo dove un piano esiste già.** Su una fattura DRAFT senza
totali, `fn_genera_scadenze_fattura` alzerebbe `E_SCADENZE_BASE_NON_PRONTA` e
farebbe fallire l'intera dichiarazione su un caso perfettamente legittimo. Se il
piano non c'è ancora, lo step EMESSA lo creerà con la data nuova.

---

### ⚠️ Le fatture già numerate si saltano — e si contano

Non fanno fallire il lotto. Il caso **«lotto numerato a metà» esiste nei dati**
(lotti 4212 e 4213, con fatture numerate in giorni diversi): rifiutare l'intero
lotto renderebbe irrisolvibile proprio la situazione per cui questa funzione
esiste.

⛔ **Il filtro è `numero IS NULL`, non lo stato.** Una fattura viene numerata
*mentre* è in EMESSA, quindi una soglia scritta sugli stati lascerebbe passare
una fattura già numerata — e il guard
[`trgfn_fatture_guard_data_numerata`](/dbzero/vendite/funzioni/trgfn_fatture_guard_data_numerata)
la rifiuterebbe, facendo fallire tutto. Lo stato serve comunque, ma per un'altra
cosa: non toccare documenti oltre la finestra in cui le rate sono rigenerabili.
La finestra è «non ancora congelata»: `congela_fiscale` falso nel vocabolario
[`config.stati_doc_fiscale`](/dbzero/config/manual/stati_doc_fiscale), letto dalla
colonna e non da un elenco di codici.

---

### ℹ️ Il guard sul pavimento è un'anticamera, non un secondo presidio

Solleva lo **stesso codice** del cancello
(`E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO`) **qui e subito**, invece che a metà
giro di numerazione. La lettura è fail-open sotto RLS (vedi
[`fn_get_data_minima_numerabile_lotto`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto)):
se qualcosa sfugge, a rifiutare sarà il cancello vero.

Il **bersaglio dell'errore è il LOTTO**, perché è la cosa che l'operatore ha
davanti.

---

### ℹ️ Perché torna TRE numeri e non due

| colonna | significato |
|---|---|
| `aggiornate` | fatture che hanno preso la data nuova |
| `saltate_numerate` | fatture già numerate, lasciate com'erano |
| `rate_rigenerate` | piani rate ricostruiti |

`rate_rigenerate` c'è perché senza di esso il **punto 4 sarebbe invisibile al
backend** — ed è la conseguenza *meno attesa* dell'atto appena compiuto. Un
operatore che dichiara una data non si aspetta di aver toccato le scadenze: il
numero glielo dice.

---

### Note operative

* Guard di parametro: `p_lotto_id` obbligatorio e maggiore di zero.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-11.


### ⭐ rev 2026-08-26 — il guard guarda due pavimenti, e sceglie fra due frasi

Brief: `brief-db-limite-emissione-e-data-verificata` (**DB-9**).

Il pavimento arriva **già composto** da
[`fn_get_pavimento_lotto`](/dbzero/vendite/funzioni/fn_get_pavimento_lotto),
che torna anche l'**origine**: qui non si riscrive nessuna regola, si sceglie la
frase.

| origine | codice | perché è una frase diversa |
|---|---|---|
| `SEQUENZA` | `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` | si rimedia risalendo alla fattura che porta quel numero |
| `EMISSIONE` | `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE` | si rimedia solo avvicinando la data a oggi |

Dire la prima quando vale la seconda manda a cercare la cosa sbagliata. A parità
di data vince `SEQUENZA`, perché la sua frase può portare un **bersaglio**.

⭐ **La data nella frase è sempre il pavimento EFFETTIVO**, non quello di
`origine`: nominarne un altro direbbe all'operatore di scegliere una data che
verrebbe rifiutata di nuovo.

### ⭐ Qui il controllo è SEVERO, e non per caso

Questa è la porta da cui una **persona** dichiara una data, e qui il sistema ha
in mano il **lotto** — quindi la competenza vera. Il cancello di
[`fn_get_next_progressivo`](/dbzero/vendite/funzioni/fn_get_next_progressivo)
riceve solo il documento e la sua data, e la **deduce** dalla data stessa.

| dove | cosa sa | quanto è severo |
|---|---|---|
| **qui** (dove si sceglie la data) | il lotto, quindi la competenza vera | severo: confronta con la competenza |
| **assegnazione del numero** (dove non si può aggirare) | il documento e la sua data | deduce il mese dalla data |

⛔ Sono **due severità diverse, ed è voluto**: chi confronta le due funzioni non
deve leggere la differenza come un difetto. Il residuo — un fine-mese dichiarato
sul mese sbagliato — si può produrre solo scrivendo direttamente nel database.

---

{% include-markdown "signature-core.md" %}
