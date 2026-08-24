## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_lotto_fatture_guard_stato_coerente()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
>
Approfondimento funzioni:
> • [vendite.fn_guard_lotto_fatture_stato_coerente](/dbzero/vendite/funzioni/fn_guard_lotto_fatture_stato_coerente)
>
Vista di lavoro correlata:
> • [vendite.vw_lotti_fatture_incoerenti](/dbzero/vendite/views/vw_lotti_fatture_incoerenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Presidia un'invariante che coinvolge **tre tabelle insieme**: lo stato fiscale di una fattura
deve restare coerente con quello del lotto che la contiene. Un lotto passato a DEFINITIVA con
dentro fatture ancora provvisorie — o il contrario — è un lotto che dichiara una cosa e ne
contiene un'altra, e da lì in avanti ogni conteggio è sbagliato.

Questa funzione **non contiene la regola**: è il dispatcher. Riconosce da quale tabella è
stata invocata, ricava **quali lotti** sono impattati dalla riga che si è mossa e delega la
verifica vera a `vendite.fn_guard_lotto_fatture_stato_coerente(lotto_id)`.

La regola vive quindi in un posto solo, mentre i punti da cui può essere violata sono tre.

---

### Aggancio: tre `CONSTRAINT TRIGGER` differiti

| Trigger | Tabella | Evento |
|---------|---------|--------|
| `trg_fatturazione_lotti_def_guard_stato_fatture_coerente_upd` | `vendite.fatturazione_lotti` | `AFTER UPDATE OF stato_doc_fiscale_id` |
| `trg_fatture_def_guard_stato_lotto_coerente_ins_upd` | `vendite.fatture` | `AFTER INSERT OR UPDATE OF stato_doc_fiscale_id, critical` |
| `trg_fatturazione_lotti_fatture_def_guard_stato_coerente_ins_upd` | `vendite.fatturazione_lotti_fatture` | `AFTER INSERT OR UPDATE OR DELETE` |

Tutti e tre `DEFERRABLE INITIALLY DEFERRED`, `FOR EACH ROW`.

---

### ⚠️ `DEFERRED` è il punto centrale, non un dettaglio

Un guard immediato qui **non funzionerebbe**. Portare un lotto a uno stato nuovo significa
aggiornare il lotto e le sue fatture: fra i due `UPDATE` esiste per forza un istante in cui
l'invariante è violata. Un trigger immediato bloccherebbe quell'istante, cioè bloccherebbe
l'operazione legittima.

Essendo differiti, i tre trigger si accodano e vengono valutati **alla fine della
transazione** (`COMMIT`, o `SET CONSTRAINTS ALL IMMEDIATE`). Quello che conta è lo stato
finale, non il transitorio.

Due conseguenze operative:

* **l'errore arriva al `COMMIT`**, non allo statement che l'ha causato. Nello stack non c'è
  la riga colpevole: per trovarla si usa `vw_lotti_fatture_incoerenti`;
* **nei pgTAP il preambolo `SET CONSTRAINTS ALL IMMEDIATE` cambia il comportamento**: con
  quello attivo la verifica torna immediata e un transitorio legittimo diventa un rosso. È
  la ragione per cui un test che manipola lotti e fatture insieme va scritto sapendo che
  questo guard esiste.

---

### Come risolve i lotti impattati

**Da `fatturazione_lotti`** — il lotto si è mosso: verifica `NEW.id`.

**Da `fatture`** — la fattura si è mossa: cicla su **tutti** i lotti che la contengono,
leggendo il ponte `fatturazione_lotti_fatture`. Lo schema del ponte ammette 1:N anche se
oggi il legame è di fatto 1:1, e il codice segue lo schema, non l'uso corrente.

**Da `fatturazione_lotti_fatture`** — è cambiato il legame stesso (aggancio, sgancio,
esclusione), quindi cambia il **perimetro** dell'invariante. Prende `OLD.lotto_id` sul
`DELETE`, `NEW.lotto_id` altrimenti — e su `UPDATE` che sposta la riga da un lotto all'altro
verifica **entrambi**: quello di destinazione e quello di provenienza, che potrebbe essere
appena diventato incoerente per sottrazione.

`RETURN NULL` è corretto e ininfluente: in un trigger `AFTER` il valore di ritorno è ignorato.

---

### Codici errore

Nessuno sollevato qui: gli errori vengono da
`vendite.fn_guard_lotto_fatture_stato_coerente`, che contiene la regola e il codice.

---

{% include-markdown "signature-core.md" %}
