## 📘 Documentazione Concettuale – Funzione `script.fn_doc_lock_colonna_bloccata()`

> 👀 **Vedi anche**
>
> • [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — il lettore del montaggio, dove sta il quadro intero

---

### 🎯 Scopo Principale

(nata il 2026-10-10, brief `brief-db-testata-dopo-emissione`, fase 1)

**La decisione** dei due lock «si tocca solo in bozza»: con il documento in questo stato,
quale di queste colonne il montaggio non lascia cambiare? Risponde con la prima che ferma,
o con niente se tutte passano. La usano il lock quando qualcuno scrive e la capability
quando deve spegnere un pulsante: per questo non possono rispondere in due modi.

* **In bozza** passa tutto, tranne le colonne di testata **ferme sempre** (rev 2026-10-18).
* **Righe**, fuori bozza: aggiungere o togliere una riga non passa mai. Una modifica passa
  solo negli stati dell'eccezione del montaggio, e solo se ogni colonna che cambia è fra
  quelle ammesse (o fra quelle che scrive l'audit). Una colonna nuova nasce chiusa.
* **Testata**, fuori bozza: si ferma la prima colonna nominata dal montaggio, nel suo
  ordine, che cambia e che in quello stato non è aperta. Le colonne che il montaggio non
  nomina sono libere.
* Un montaggio sbagliato non lascia passare niente.

### 🔄 rev 2026-10-18 — la colonna ferma sempre (brief-db-indirizzi-documento-seguono-il-cliente §8.7)

Una colonna di testata ferma sempre (la terna con `-`, vedi
[script.fn_doc_lock_regola](/dbzero/script/funzioni/fn_doc_lock_regola)) si ferma in ogni stato,
bozza compresa. Per questo «in bozza passa tutto» non chiude più la decisione prima dei due
lock: lo dice ciascuno dei due. Per le righe non cambia niente.

> 📎 changeSet `20261018-66`.
