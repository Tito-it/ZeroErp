## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_attivita_proietta_stato_preventivo`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_preventivo_proietta_stato_smistamento](/dbzero/vendite/funzioni/fn_preventivo_proietta_stato_smistamento) — la regola  

---

### 🎯 Scopo Principale
(2026-10-12, brief-db-annullo-a-valle-riapre-a-monte, D-10)

Una riga di commessa **di un preventivo** nasce, cambia `stato_emissione` o
sparisce: lo stato del preventivo si riproietta (`ACCETTATO ↔ EVASO`).

---

### Perché un trigger

Lo stato dell'ordine dalle bolle lo riproiettano le funzioni madri che scrivono
i legami. L'invio in commessa invece **non ha una madre nel DB**: lo orchestra il
backend, che scrive le righe una per una. La riga di commessa è l'unico punto del
DB che vede **ogni strada**:

* l'invio singolo e quello batch (che prima lasciava il preventivo `ACCETTATO`);
* il ritiro all'annullo di un documento;
* l'annullo della commessa;
* la cancellazione di una riga.

---

### Montaggio

| Trigger | Quando |
| --- | --- |
| `trg_commesse_attivita_z90_proietta_stato_preventivo_ins_dlt` | `AFTER INSERT OR DELETE` |
| `trg_commesse_attivita_z90_proietta_stato_preventivo_upd` | `AFTER UPDATE`, sul cambio di `stato_emissione` |

Le righe senza sorgente e quelle delle altre sorgenti escono subito. Il
preventivo si trova dal suo uid (`sorgente_uid`).

---

### Note operative

* Durante un invio di N righe il preventivo diventa `EVASO` una volta sola,
  all'ultima: la proiezione scrive solo se lo stato cambia.
* Costo: per ogni riga di un preventivo la proiezione rilegge il residuo delle
  righe del preventivo (decine di letture sull'indice del segmento).
* Test: `db/pgtap/vendite/test-annullo-commessa-v1.sql` (casi B, D, J).

---

{% include-markdown "signature-core.md" %}
