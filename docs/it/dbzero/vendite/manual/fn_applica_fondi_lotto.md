## 📘 Documentazione Concettuale – Funzione `vendite.fn_applica_fondi_lotto`

> 👀 **Vedi anche**
>
> **Su cosa si appoggia:**
>
> • [vendite.fn_get_scope_fatture_lotto](/dbzero/vendite/funzioni/fn_get_scope_fatture_lotto) — lo scope del lotto
> • [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) — l'applicazione per fattura, **intatta**
>
> **La sorella:**
>
> • [vendite.fn_genera_fondi_fattura_lotto](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_lotto)
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.3 R-3

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**Applica i fondi disponibili alle fatture di un lotto, in una chiamata sola.**

Ritorna `fatture_count` e `fondi_applicati`. Prende il **codice interno** del
tipo fondo — non l'id — per la stessa ragione della sorella: è ciò che arriva
dalla configurazione del task, e un id costringerebbe il chiamante a una query
di lookup in più.

---

### ⚠️ Perché questa itera sulle FATTURE e la sorella no

Non è un'asimmetria da correggere. Le due madri chiamano funzioni che lavorano su
oggetti diversi:

| | Itera su | Perché |
| --- | --- | --- |
| **generazione** | le **chiavi** | le sorgenti si trovano per chiave, e **non appartengono al lotto**: sono fatture precedenti |
| **applicazione** | le **fatture** | ogni figlia riceve i **suoi** fondi, e cambia il proprio totale |

Deduplicare per chiave qui vorrebbe dire assegnare i fondi a una figlia sola e
lasciare le altre a secco: il contrario di quello che serve.

---

### ⭐ Qui il parziale costa più che altrove

Ogni chiamata riuscita ha già portato una source ad `ASSEGNATO`, creato la riga
in `fatture_fondi_fattura` e **cambiato il totale di una fattura**.

Un giro interrotto a metà lascia un lotto in cui alcune figlie hanno il fondo e
altre no — e nessuna delle due metà è sbagliata *di per sé*, quindi niente lo
segnala: non c'è un invariante che fallisca, non c'è un log che si accenda. Lo si
scopre dal cliente.

Una funzione = uno statement = una transazione chiude il caso **per
costruzione**, comunque il chiamante scriva la query.

---

### Cosa NON cambia

La **chiave a nove elementi**, il **guard di capienza** e il
`FOR UPDATE … SKIP LOCKED` restano dentro
[fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura),
che è l'unico posto in cui il fondo muove denaro. Questa funzione è
orchestrazione: non aggiunge né toglie un controllo.

ℹ️ I cinque parametri di scope restano nella firma della funzione figlia perché
lì fanno da *sanity check* sulla figlia — e qui arrivano dalle colonne della
figlia stessa, quindi il controllo è tautologico e costa niente. Toglierli è
un'altra modifica, con un'altra misura.

---

### ⚠️ Un fondo che non passa non è un errore

Se la sorgente non è più capiente, `fn_applica_fondi_fattura` **non applica** e
il fondo resta `DISPONIBILE`: il conteggio di ritorno sarà più basso, e non
verrà sollevato niente. È voluto — quel fondo non è sbagliato, è solo non più
dovuto **adesso**, e chi deve deciderlo lo trova in
[vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere)
col motivo `NON_PIU_CAPIENTE`.

---

### Esempio d'uso

```sql
SELECT * FROM vendite.fn_applica_fondi_lotto(1234, 'F_F_ADD_ACC');
-- fatture_count | fondi_applicati
--            42 |               5
```

---

{% include-markdown "signature-core.md" %}
