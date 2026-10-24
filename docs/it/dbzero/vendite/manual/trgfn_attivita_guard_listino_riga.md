## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_guard_listino_riga`

> 👀 **Vedi anche**
>
> • [vendite.fn_check_listino_provenienza](/dbzero/vendite/manual/fn_check_listino_provenienza) — la check
>
> • [vendite.commesse_attivita](/dbzero/vendite/manual/commesse_attivita) e [vendite.attivita_fatturabili](/dbzero/vendite/manual/attivita_fatturabili) — le due tabelle che lo montano
>
> • [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — l'altra regola sulla riga di listino citata («propagata»)

### 🎯 Scopo Principale

(rev 2026-10-15, D-1 di Tid; rev 2026-10-16, §6 del brief)

Una riga di commessa e la sua attività fatturabile portano la **provenienza del prezzo**: la
**riga di listino** che l'ha dato (`listino_riga_id`) e, la commessa, la **versione** sotto cui
è registrata (`listino_versione_id`). Questo guard rifiuta la scrittura quando la provenienza
non è ammessa, con il codice del primo motivo di `vendite.fn_check_listino_provenienza`:

| Codice | Quando |
| --- | --- |
| `E_ATTIVITA_LISTINO_RIGA_INCOERENTE` | la riga di listino non è dello stesso articolo, della stessa unità di misura o (sulla commessa) della stessa versione della riga |
| `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO` | il listino è di un'altra azienda rispetto alla commessa |
| `E_ATTIVITA_LISTINO_VERSIONE_BOZZA` | la versione è in bozza: mai un prezzo da una bozza |

Qui resta solo il **quando**; il predicato è nella check.

---

### Quando scatta

* **Trigger**: `AFTER INSERT OR UPDATE`, per riga, su `vendite.commesse_attivita` e
  `vendite.attivita_fatturabili` (`trg_*_a10_guard_listino_riga_ins_upd`).
* **AFTER**, perché giudica la riga **finale**, dopo ogni trigger `BEFORE`: articolo e unità di
  misura non devono poter cambiare per una strada che un `UPDATE OF` non vede.
* Senza riga di listino **e** senza versione non fa niente: la riga con la sola versione (il
  push la scrive così) si giudica per emittente e bozza. In `UPDATE` controlla solo se cambia la
  riga di listino, l'articolo, l'unità di misura, la versione o la commessa: le scritture
  dell'emissione e degli stati non rileggono il listino.
* La versione si legge **per nome**: `attivita_fatturabili` non ce l'ha, e lì emittente e bozza
  si giudicano sulla versione della riga di listino.

---

### Chi scrive la riga di listino

Non l'operatore: il **programma**, dal risolutore dei prezzi, che la cerca proprio con articolo,
unità di misura e versione della riga. Scrivono la colonna la madre del push
(`vendite.fn_upsert_commessa_attivita`), il riallineamento del prezzo nel backend (un `UPDATE`
diretto su commessa e attività fatturabile) e l'emissione, che la copia. Il guard sta sulla
**tabella** proprio perché li copre tutti, test compresi.

---

### Il codice

Tutti e tre in classe **TECNICO**: la provenienza la scrive il programma dal risolutore, che
sceglie già i listini dell'azienda e (dal 2026-10-16) non dà prezzi da una bozza. Una riga
rifiutata qui è un difetto di chi scrive, non qualcosa che l'operatore corregge a video. Nessun
bersaglio; il contesto porta tabella, riga, commessa, versione e riga di listino per chi
diagnostica. Il primo codice dice nel messaggio quale riga di listino; gli altri due sono frasi
chiuse, perché il listino può essere di un'azienda che l'operatore non vede.

Sulla commessa, la riga di listino senza la versione la rifiuta già il vincolo
`chk_commesse_attivita_listino_riga_con_versione`.

Il lato della **riga di listino** (articolo, unità di misura e versione non cambiano dopo
l'inserimento) lo tiene il blocco di colonna, con il codice `E_LISTINO_RIGA_IDENTITA_IMMUTABILE`:
vedi [vendite.listini_righe](/dbzero/vendite/manual/listini_righe).

---

### 🧪 Il presidio

`db/pgtap/vendite/test-guard-listino-riga-coerente-v1.sql` (15 casi): la forma (check
`SECURITY DEFINER`, trigger sulle due tabelle), la riga coerente che passa, i tre rifiuti di
coerenza (articolo, versione, unità di misura), la versione tolta che il vincolo rifiuta,
l'attività fatturabile coerente e quella spostata su un'altra unità di misura, il blocco di
colonna sulla riga di listino, il listino di un'altra azienda (con la riga e con la sola
versione), la versione in bozza, e il risolutore con la versione preferita in bozza e attiva.

---
{% include-markdown "signature-core.md" %}
