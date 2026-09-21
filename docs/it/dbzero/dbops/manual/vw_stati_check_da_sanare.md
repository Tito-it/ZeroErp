## 📘 Documentazione Concettuale – View `dbops.vw_stati_check_da_sanare`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.stati_check_dichiarazioni](/dbzero/dbops/manual/stati_check_dichiarazioni)
>
Approfondimenti viste:
>
[dbops.vw_stati_check_scrittori](/dbzero/dbops/manual/vw_stati_check_scrittori)

---
### 🎯 Scopo Principale
(latest review 21-09-2026)

**La lista di lavoro** del controllo sugli stati mai scritti: la misura
(`vw_stati_check_scrittori`) ridotta alle sole righe che chiedono un gesto.
**Deve restare vuota**, e ogni riga dice che cosa fare (`da_fare`).

---

### Le due righe possibili

| `esito` | Che cos'è | Il gesto |
| --- | --- | --- |
| `NON_DICHIARATO` | un valore ammesso che nessuno scrive e nessuno ha guardato | o si scrive chi lo scrive, o la riga entra nel registro con il canale e la ragione |
| `DEBITO_ESTINTO` | una riga di registro che non serve più: il valore è scritto, o non esiste più | si toglie dal registro (dal CSV, con la sua cancellazione) |

---

### ⭐ È un cancello, non un promemoria

La riga di catalogo in `dbops.presidi` la classifica **`CANCELLO`**: il test
`db/pgtap/dbops/test-stati-check-scrittori-v1.sql` la fa rossa in CI, quindi
non entra nel digest — un avviso che ripete ciò che un cancello ha già fermato è
rumore.

⚠️ Il cancello ha **due lati**, e questa vista ne mostra uno. Le righe che il
programma dichiara di scrivere (`DICHIARATO_APPLICAZIONE` nella misura) non
compaiono qui: le verifica il **test del backend**, che cerca il valore nei file
che scrivono quella tabella e diventa rosso se sparisce.

⛔ Non si allarga il filtro per farla tacere: si allarga il **registro**, con la
ragione.

Origine: `docs/it/dev/work-done/brief-db-presidio-stati-mai-scritti.md`.

---

{% include-markdown "signature-core.md" %}
