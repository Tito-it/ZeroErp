## 📘 Documentazione Concettuale – Funzione Trigger `vendite.trgfn_listini_righe_guard_stato`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) — la regola ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) — la riga nuova ·
> [vendite.vw_listini_righe_azioni](/dbzero/vendite/manual/vw_listini_righe_azioni) — la riga che c'è ·
> [config.azioni_riga](/dbzero/config/manual/azioni_riga) ·
> [config.stati_doc_listino_versioni](/dbzero/config/manual/stati_doc_listino_versioni)

---

### 🎯 Scopo Principale

Il guard delle righe di listino secondo lo stato della versione: rifiuta la scrittura di una riga
che la versione non ammette. **La regola non sta qui**: sta in
[`script.fn_check_listino_riga_scrivibile`](/dbzero/script/manual/fn_check_listino_riga_scrivibile),
e il guard ne solleva il primo motivo (`script.fn_raise_primo_motivo_se_presente`). Le stesse
risposte le danno le superfici che il frontend legge, quindi il pulsante e l'errore non possono
dire due cose diverse (linee guida SQL §12.5.2).

---

### Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT OR UPDATE OR DELETE`, per riga, su `vendite.listini_righe`
* **Nome trigger**: `trg_listini_righe_a10_guard_stato_ins_upd_dlt`
* **Fase**: `_a10_` (guard)
* Sull'INSERT la domanda è la riga nuova della versione (`NEW.listino_versione_id`); su UPDATE e
  DELETE la riga che c'è (`OLD`).

---

### Che cosa ammette

| Versione | Riga nuova | Riga che c'è |
| --- | --- | --- |
| in bozza (lo stato `iniziale` del vocabolario) | sì | sì |
| `ATTIVA` | sì: è una rettifica | sì, finché il suo prezzo non è stato usato da un documento (`E_RIGA_LISTINO_PROPAGATA`) |
| `CHIUSA` | no (`E_RIGA_LISTINO_VERSIONE_CHIUSA`) | no (`E_RIGA_LISTINO_VERSIONE_CHIUSA`) |

Una riga è **propagata** quando la cita (`listino_riga_id`) una riga di commessa, un'attività
fatturabile, o una riga principale o un componente di preventivo, ordine, contratto, DDT od
offerta, anche in bozza: le dodici tabelle stanno nella check. Per cambiare il prezzo di una riga
propagata si fa una versione nuova del listino.

---

### Il verbo nel registro

Le righe di listino si scrivono direttamente (il backend fa `INSERT`, `UPDATE`, `DELETE`), e non
c'è una funzione che esegua l'azione: chi la rifiuta è questo guard. Per questo è il `verbo` delle
azioni `AGGIUNGI_RIGA_LISTINO` e `MODIFICA_RIGA_LISTINO` in
[`config.azioni_riga`](/dbzero/config/manual/azioni_riga), e il presidio del registro verifica che
chiami la check.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_RIGA_LISTINO_VERSIONE_CHIUSA` | una riga nuova, una modifica o un'eliminazione in una versione CHIUSA |
| `E_RIGA_LISTINO_PROPAGATA` | la modifica o l'eliminazione, fuori dalla bozza, di una riga il cui prezzo è stato usato |

---

### Test

* `db/pgtap/vendite/test-listino-riga-scrivibile-v1.sql` — la check, le due superfici e il guard
  rispondono uguale, con la marca `iniziale` spostata.
* `db/pgtap/vendite/test-provenienza-prezzo-push-v1.sql` (test 13) — le dieci tabelle dei
  documenti nella check.

---

{% include-markdown "signature-core.md" %}
