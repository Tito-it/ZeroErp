## 📘 Documentazione Concettuale – Tabella `config.azioni_riga`

> 👀 **Vedi anche**
>
> [vendite.vw_lotti_gruppi_azioni](/dbzero/vendite/views/vw_lotti_gruppi_azioni) ·
> [linee guida SQL](/linee-guida-sql) §12.5 ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §6

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15.10, D-N1, F-5, Q-F5)

**Il registro delle azioni di riga.** Un pulsante su una riga di elenco (togliere un documento dal
giro di un lotto, attivare una versione di listino, e domani le azioni per riga degli altri
documenti) ha tre pezzi che devono dire la stessa cosa:

* la **funzione che esegue l'azione** (`verbo`), che la rifiuta col primo motivo della sua `fn_check`;
* la **vista** che il frontend legge (`superficie`), con una riga per riga dell'elenco e le due colonne
  che dicono perché il pulsante è spento;
* la **`fn_check`**, che entrambe chiamano.

Il registro scrive il legame; il presidio pgTAP `db/pgtap/config/test-azioni-riga-registro-v1.sql` lo
verifica, riga per riga. Il frontend legge dal registro quali colonne mostrare: un solo componente per
il pulsante di riga, non uno per azione.

### Le colonne

| Colonna | Cosa contiene |
| --- | --- |
| `codice_interno` | il nome dell'azione (`ESCLUDI_DOCUMENTO_DA_GIRO`) |
| `superficie` | la vista, `schema.nome` |
| `colonna_motivo`, `colonna_motivo_chiave` | le colonne della vista col motivo e la sua chiave di traduzione; `NULL` nella riga = azione viva |
| `fn_check` | la funzione dei motivi, `schema.fn_check_…` |
| `verbo` | la funzione che esegue l'azione, `schema.nome` |

⚠️ **Testo, non `regclass` o `regprocedure`.** Un tipo `reg*` salva l'OID: segue una rinomina senza
dirlo e, se l'oggetto sparisce, mostra un numero senza errore. Che i nomi puntino a oggetti vivi lo
dice il presidio; i `CHECK` della tabella controllano solo la forma.

### Il presidio verifica, per ogni riga attiva

1. la superficie è una vista viva, `security_invoker`;
2. ha le due colonne del motivo, di tipo `text`;
3. `fn_check` e verbo esistono, con un nome solo;
4. la vista **dipende** dalla `fn_check`;
5. il verbo **chiama** la `fn_check`.

### Come si aggiunge un'azione

Una riga nel CSV `80_data/sql/config/azioni_riga.csv`, con la sua vista già scritta. Una colonna di
blocco composta dal backend non si iscrive: il motivo per riga sta in una vista del database.

---

{% include-markdown "signature-core.md" %}
