## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_causale_emissione()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
> Guard gemello (stesso momento, stessa forma):
> [vendite.trgfn_ddt_guard_indirizzi_obbligatori](trgfn_ddt_guard_indirizzi_obbligatori.md)
>
> Errori:
> [config.messaggi_errore E_DDT_CAUSALE_OBBLIGATORIA (id=544)](/dbzero/config/tabelle/messaggi_errore)
> [config.messaggi_errore E_DDT_PREZZO_NON_RISOLVIBILE (id=545)](/dbzero/config/tabelle/messaggi_errore)
>
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §4a

---

### 🎯 Scopo Principale

(rev 2026-07-18)

Blocca l'**emissione** di un DDT (transizione a stato `EMESSO`) quando il documento non
dichiara **perché la merce viaggia**, o quando dichiara una vendita ma non ha prezzi con cui
fatturarla.

Applicata dal trigger `trg_ddt_a10_guard_causale_emissione_upd`
(fase `_a10_`, `BEFORE UPDATE OF stato_doc_ddt_id`) — stesso posizionamento del guard
indirizzi.

**Il problema che risolve.** Il DDT ammette per progetto righe senza prezzo (*«solo
trasporto»*: campionature, trasferimenti, conto lavoro). Ma senza una dichiarazione esplicita,
un DDT senza prezzi è ambiguo: è una scelta o una dimenticanza? Il sistema, non sapendolo, lo
avrebbe proposto «da fatturare» con prezzo vuoto. Invece di **inferire** l'intento
dall'assenza di prezzo, lo si fa **dichiarare a monte** con il campo che l'operatore già
compila — la causale di trasporto.

---

### Le due regole

**R1 — la causale è obbligatoria all'emissione.**
`ddt.causale_trasporto_id` è nullable, ma dall'emissione in poi non è più ammesso: senza
causale il documento resterebbe ambiguo per la fatturazione. In **bozza il NULL resta
legittimo** — la causale si compila prima di emettere, esattamente come l'indirizzo.

> Conseguenza voluta a valle: il lister e i cruscotti **non devono trattare il NULL** in modo
> speciale, perché un DDT senza causale non raggiunge mai uno stato in cui verrebbe guardato.

**R2 — se la causale è fatturabile, ogni riga attiva deve avere un prezzo *risolvibile*.**
Risolvibile significa: prezzo proprio della riga DDT **oppure** ereditato dalla riga d'ordine
via `ordini_righe_fulfillment`. È la stessa `COALESCE` che usano il lister e i cruscotti.

> ⚠️ **Prezzo risolvibile ≠ prezzo presente**: una riga da evasione **senza** prezzo proprio è
> perfettamente legittima, purché l'ordine glielo fornisca. Pretendere il prezzo sulla riga DDT
> bloccherebbe un caso valido — vale per questo guard come per il frontend.
>
> ⚠️ `vw_ddt_righe_iva_base` **non è riusabile** per questo controllo: filtra
> `prezzo_unitario IS NOT NULL`, cioè perde esattamente le righe da esaminare.

Con causale **non fatturabile** i prezzi sono irrilevanti: nessun controllo, il documento è
solo trasporto.

Il risultato è che **il prezzo dimenticato diventa un errore all'emissione**, invece di un
documento silenziosamente mal classificato che poi genererebbe attività senza prezzo.

---

### Errori sollevati

| Codice | Quando | Contesto |
|---|---|---|
| `E_DDT_CAUSALE_OBBLIGATORIA` (544) | R1: emissione senza causale | `ddt_id`, `numero` |
| `E_DDT_PREZZO_NON_RISOLVIBILE` (545) | R2: causale fatturabile + riga senza prezzo risolvibile | `ddt_id`, `numero`, **`riga_id`** — nomina la riga colpevole |

---

### Esempio d'uso

```sql
-- Emissione bloccata: manca la causale.
UPDATE vendite.ddt SET stato_doc_ddt_id = <EMESSO> WHERE id = 123;
-- ERRORE: DDT DDT0000123: causale di trasporto obbligatoria per l'emissione.

-- Dichiarando "solo trasporto" l'emissione passa, prezzi o non prezzi.
UPDATE vendite.ddt
   SET causale_trasporto_id = (SELECT id FROM config.causali_trasporto WHERE codice='CAMPIONATURA')
 WHERE id = 123;
```

---

### Note operative

* **Quale causale è fatturabile lo dice il vocabolario**, non il codice:
  `config.causali_trasporto.fatturabile`. Oggi solo `VENDITA` è `true`. I casi ambigui — per
  esempio l'omaggio, che qualcuno fattura a sconto 100% — si risolvono cambiando **una cella di
  seed**, senza toccare questa funzione (stesso pattern di `tipi_reso.riapre_residuo`).
* **Ordine di scatto**: questo guard e quello sugli indirizzi sono entrambi in fase `_a10_` su
  `BEFORE UPDATE OF stato_doc_ddt_id`. Se un documento viola entrambe le condizioni, l'operatore
  vedrà prima l'uno e poi l'altro — comportamento normale dei guard fail-fast, ma da sapere
  quando si legge un errore soltanto.
* **Impatto sulle fixture di test**: qualunque test che porti un DDT a `EMESSO` deve ora
  valorizzare la causale prima della transizione. È il motivo per cui le fixture pgTAP della
  slice assegnano `VENDITA` prima di emettere.
* Test: `db/pgtap/vendite/test-ddt-solo-trasporto-causale-v1.sql`.

---

{% include-markdown "signature-core.md" %}
