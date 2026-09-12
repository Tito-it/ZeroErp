## 📘 Documentazione Concettuale – View `dbops.vw_audit_log_scrittori_fuori_perimetro`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.audit_log](/dbzero/dbops/tabelle/audit_log) ·
[dbops.presidi](/dbzero/dbops/manual/presidi)
>
Approfondimenti funzioni:
>
[dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once)
>
Guida: [Messaggi di audit — Chi può scrivere](/guide/messaggi-audit)

---
### 🎯 Scopo Principale
(latest review 12-09-2026)

Elenca le **funzioni che scrivono nel registro di audit** e che stanno **fuori
dagli schemi ammessi**: oggi `dbops` e `maintenance`, e l'elenco sta scritto
dentro la vista stessa.

> ⛔ È un **cancello**: deve restare **vuota**. Una riga fa fallire il controllo
> automatico, non un promemoria.

---

### ⭐ Perché esiste, detto sul modello

`dbops.audit_log` è il **registro tecnico** delle automazioni e degli strumenti
di amministrazione del database: lo scrivono le funzioni di `dbops`, lo legge
l'area di amministrazione. **Non deve poter contenere dati di dominio** —
i parametri di una fattura, l'esito di un'operazione su un cliente.

La tentazione era proteggerlo come si proteggono le tabelle di storico: una
regola di visibilità per riga. ⛔ Sarebbe stata la risposta sbagliata alla
domanda sbagliata: il registro non ha una «riga madre» da cui prendere il
perimetro, e un filtro per riga su un log si paga a ogni lettura. La domanda
giusta è *«questo registro deve poter contenere dati di dominio?»* — e la
risposta, decisa il 2026-09-11, è **no**. Quindi il rischio si toglie **alla
fonte**: nessuna funzione di `vendite`, `anagrafiche`, `pagamenti` può scriverci,
e se un giorno una lo facesse, questa vista la nomina.

---

### Che cosa guarda, e che cosa no

| Conta come «scrive» | Non conta |
| --- | --- |
| `INSERT INTO` / `UPDATE` / `DELETE FROM dbops.audit_log` nel corpo (`come_scrive = DML_DIRETTO`) | una lettura del registro (`SELECT … FROM dbops.audit_log`) |
| una chiamata a `fn_audit_log_once`, `fn_audit_begin`, `fn_audit_end` (`come_scrive = VIA_FN_AUDIT`) | i commenti di riga: il sorgente si legge **senza** i `-- …`, così un esempio commentato non fa scattare il cancello |
| | le tre funzioni di audit stesse: sono la porta, e stanno in `dbops` |

Legge solo il catalogo (`pg_proc`), con `security_invoker`: non tocca dati.

---

### Se compare una riga

Due esiti possibili, e nessuno dei due è «aggiungere lo schema all'elenco senza
pensarci»:

1. la funzione **non doveva** scrivere l'audit — è il caso atteso: si toglie la
   chiamata, e quel che voleva registrare va nel posto suo (l'`error_log` per un
   errore, una tabella di dominio per un fatto di dominio);
2. il perimetro deve **davvero** allargarsi (per esempio se `script` dovesse un
   giorno scrivere l'audit): è un changeSet su **questa vista**, firmato e
   motivato — non una riga che passa in silenzio.

---

### Esempio d'uso

```sql
-- Deve tornare zero righe. Se no, la prima colonna dice chi e la terza come.
SELECT funzione, schema_funzione, come_scrive
FROM dbops.vw_audit_log_scrittori_fuori_perimetro;
```

Presidio: `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` (in CI),
che oltre a pretendere la vista vuota costruisce una funzione temporanea che
chiama la porta e verifica che venga vista e classificata. A catalogo in
`dbops.presidi` con natura `CANCELLO`.
Origine: `docs/it/dev/work-done/brief-db-rls-storico-scope-congelato.md` §8.3, §8.6.

---

{% include-markdown "signature-core.md" %}
