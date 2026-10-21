## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_guard_contratto`

> 👀 **Vedi anche**
>
> • [vendite.fn_check_contratto_provenienza](/dbzero/vendite/manual/fn_check_contratto_provenienza) — la check
>
> • [vendite.commesse_attivita](/dbzero/vendite/manual/commesse_attivita) e [vendite.attivita_fatturabili](/dbzero/vendite/manual/attivita_fatturabili) — le due tabelle che lo montano
>
> • [vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga) — il gemello sull'altra metà della provenienza

### 🎯 Scopo Principale

(rev 2026-10-21, decisione di Tid D-1)

Una riga di commessa e la sua attività fatturabile portano il **contratto** da cui è venuto il
prezzo (`contratto_id`). Questo guard rifiuta la scrittura quando il contratto non è del conto di
fatturazione della commessa, con il codice di `vendite.fn_check_contratto_provenienza`:

| Codice | Quando |
| --- | --- |
| `E_ATTIVITA_CONTRATTO_INCOERENTE` | il contratto è di un altro conto di fatturazione (un altro cliente, della stessa azienda o di un'altra) |

Qui resta solo il **quando**; il predicato è nella check.

---

### Quando scatta

* **Trigger**: `AFTER INSERT OR UPDATE`, per riga, su `vendite.commesse_attivita` e
  `vendite.attivita_fatturabili` (`trg_*_a10_guard_contratto_ins_upd`).
* **Due tabelle**: il contratto nasce sulla riga di commessa e l'emissione lo copia
  sull'attività fatturabile; ma sull'attività esiste anche la modifica diretta, quindi il guard
  sta su entrambe.
* **AFTER**, perché giudica la riga **finale**, dopo ogni trigger `BEFORE`.
* Senza contratto non fa niente. In `UPDATE` controlla solo se cambiano il contratto o la
  commessa: le scritture dell'emissione e degli stati riscrivono lo stesso valore.
* Fra gli `AFTER` della stessa fase viene prima del guard della riga di listino: su una riga
  che sbaglia tutte e due le provenienze parla il contratto, che è la scelta più a monte.

---

### Il codice

`E_ATTIVITA_CONTRATTO_INCOERENTE` è **tecnico**: il contratto non lo sceglie l'operatore, lo
scrive il programma dal calcolo del prezzo. Una riga così è un difetto di chi scrive. La frase è
chiusa (non nomina il contratto): può essere di un'azienda che l'operatore non vede. Il contesto
dell'errore porta tabella, riga, commessa e contratto, per chi fa la diagnosi.

---

### 🧪 Il presidio

`db/pgtap/vendite/test-guard-contratto-provenienza-v1.sql` (8 casi): la forma, il contratto
giusto che passa, il contratto di un altro cliente della stessa azienda e quello di un'altra
azienda rifiutati, l'attività fatturabile emessa che porta il contratto e quella spostata su un
altro cliente rifiutata, il codice registrato.

---
{% include-markdown "signature-core.md" %}
