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
| `true` | la sveglia è accesa qui, qualunque cosa dica il default |
| `false` | la sveglia è spenta qui |
| `NULL` | la scelta a mano si toglie: vale di nuovo il default per ambiente |

Restituisce lo **stato effettivo** dopo il gesto (`NULL` solo se si è tolta la
scelta e l'ambiente non è dichiarato).

### Regole

* I limiti (processo senza sveglia, non spegnibile, motivo vuoto) li dice il
  guard della tabella: il verbo non li ripete.
* Codice inesistente: `E_PROCESSO_NON_TROVATO`.
* `SECURITY INVOKER`: **chi** può farlo lo decide il backend, con la stessa
  autorizzazione del drawer dei processi.
* La scelta tolta (`NULL`) non lascia traccia nella tabella: la tiene il
  registro delle operazioni del backend.

### Test

`db/pgtap/dbops/test-processi-accensione-v1.sql` (test 21–30).

---

{% include-markdown "signature-core.md" %}
