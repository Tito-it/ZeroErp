## 📘 Documentazione Concettuale – Funzione `dbops.fn_imposta_accensione_processo()`

> 👀 **Vedi anche**
>
> [dbops.processi_accensione](/dbzero/dbops/manual/processi_accensione) ·
> [dbops.processi](/dbzero/dbops/manual/processi)

### 🎯 Scopo
(16-10-2026 — brief `brief-db-processi-accensione-per-ambiente`)

**Accendere o spegnere a mano la sveglia di un processo** su questa
installazione, oppure tornare al default del catalogo.

| `p_acceso` | Effetto |
| --- | --- |
| `true` | la sveglia è accesa qui, qualunque cosa dica il default; in un'installazione di produzione, non su un processo non accendibile in produzione (dal 18-10-2026) |
| `false` | la sveglia è spenta qui |
| `NULL` | la sveglia torna al default per ambiente; la riga resta, con `acceso` vuoto, chi e perché |

Restituisce lo **stato effettivo** dopo il gesto (`NULL` solo se si è tornati
al default e l'ambiente non è dichiarato).

### Regole

* I limiti (processo senza sveglia, non spegnibile, non accendibile in
  produzione, motivo vuoto) li dice il guard della tabella: il verbo non li
  ripete.
* Codice inesistente: `E_PROCESSO_NON_TROVATO`.
* `SECURITY INVOKER`: **chi** può farlo lo decide il backend, con la stessa
  autorizzazione del drawer dei processi.
* Il motivo è obbligatorio per tutti e tre i gesti, anche per tornare al
  default (17-10-2026).
* Tutti e tre scrivono la riga: la storia dei gesti sta in
  `storico.processi_accensione`. **Chi** e **quando** li scrive l'audit
  automatico (l'utente collegato al backend), non il verbo.

### Test

`db/pgtap/dbops/test-processi-accensione-v1.sql` (test 21–34);
`db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` (il divieto in
un'installazione di produzione, costruita).

---

{% include-markdown "signature-core.md" %}
