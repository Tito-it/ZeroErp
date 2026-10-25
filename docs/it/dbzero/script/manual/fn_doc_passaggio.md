## 📘 Documentazione Concettuale – Funzione `script.fn_doc_passaggio(regclass, bigint, bigint)`

> 👀 **Vedi anche**
>
> [script.fn_guard_passaggio](/dbzero/script/funzioni/fn_guard_passaggio) ·
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §6

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §7, decisione M-3)

**La riga del passaggio.** Per una testata e una coppia di stati (da, a) rende la
riga viva della sua matrice, con le due cose che il modello ci legge:

* `manuale`: `false` vuol dire passaggio **di processo**, che fa il sistema come
  conseguenza di un'altra operazione (la bolla che passa a «Reso» quando si
  conferma il reso di tutta la sua merce). Non si chiede a mano;
* `azione_processo_codename`: l'**azione** che il passaggio chiede. Vuoto: basta il
  permesso sul documento, che controlla il backend.

Nessuna riga: il passaggio non è nella matrice. Lo rifiuta il guard di
transizione del documento, quando si prova a scriverlo.

### Chi la legge

È il **lettore unico** della riga: la prima riga del verbo
(`script.fn_guard_passaggio`), le capability di bolla e reso (il bottone si
nasconde a chi non ha l'azione) e il backend, per rispondere 403 prima della
transazione. Tre lettori, una sede: non possono rispondere in modo diverso.

### Regole

* Un documento non ancora portato al modello (la sua matrice non ha la colonna
  dell'azione) o una tabella fuori mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA`.
* L'azione si dichiara nel CSV della matrice, per codice (`permission_codename`).
