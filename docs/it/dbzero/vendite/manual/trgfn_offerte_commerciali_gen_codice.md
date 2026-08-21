## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_gen_codice()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> • [vendite.trgfn_contratti_gen_codice](/dbzero/vendite/funzioni/trgfn_contratti_gen_codice)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna il **codice dell'offerta commerciale** quando non viene fornito, delegando a
`script.fn_generate_codice('offerta_commerciale')`. Stesso pattern dei `gen_codice` di
anagrafiche, pratiche e contratti: riconoscere il campo vuoto e chiedere il valore al
generatore centrale.

Configurazione in `config.sistema_codici`, riga
`codice_interno = 'offerta_commerciale'`: prefisso `OFC`, separatore `-`, numero a 7 cifre
(`OFC-0000123`).

---

### Aggancio

Trigger `trg_offerte_commerciali_a10_gen_codice_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE` su `vendite.offerte_commerciali`.

---

### Regole applicate

1. Se `NEW.codice` è `NULL` o vuoto dopo `btrim`, viene valorizzato con
   `script.fn_generate_codice('offerta_commerciale')`.
2. Un codice già presente non viene mai sovrascritto.

---

### Il codice è immutabile — ma lo è solo dal 2026-08-21

Accanto a questo trigger agisce `trg_offerte_commerciali_a10_lock_columns_upd`
(`script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')`), generato
dall'automazione `LOCK_COLUMNS` dalla riga `vendite / offerte_commerciali / codice` di
`dbops.automation_lock_columns`. I `BEFORE ROW` scattano in **ordine alfabetico**, quindi
`gen_codice` gira *prima* di `lock_columns`: chi azzera `codice` in un `UPDATE` ne ottiene
uno nuovo, che il lock intercetta subito dopo come modifica e rifiuta.

⚠️ **Fino al 2026-08-21 quel lock non c'era**, ed è l'unico motivo per cui vale la pena
raccontarlo qui. Questa tabella aveva il `gen_codice` agganciato anche in `UPDATE` ma nessun
lock, a differenza delle sette gemelle (`soggetti`, `billing_account`, `fornitori`,
`istanze_utilities`, `vettori`, `contratti`, `pratiche`). Un `UPDATE` che azzerava il codice
ne rigenerava quindi uno **nuovo**, consumando la sequenza, e l'offerta cambiava identità per
chiunque la citasse per codice — senza GUC, senza manutenzione, senza nessun errore.

Il percorso applicativo non era esposto (`codice` non compare in `_OFFERTA_UPDATE_COLS` del
repository), l'`UPDATE` diretto sì. Classificata come dimenticanza, non come scelta, e chiusa
aggiungendo la riga di configurazione. Presidio: `test-offerte-commerciali-codice-lock.sql`.

⚠️ Con `SET LOCAL zeroerp.allow_lock_columns_override = 'on'` il lock si spegne e si torna
esattamente al comportamento di prima: in manutenzione, svuotare `codice` **cambia davvero
l'identità dell'offerta**.

---

### ⚠️ Questa funzione è **generata**, non scritta a mano

Il corpo compresso su una riga sola non è una svista di formattazione. La funzione, la
sequenza e il trigger che la invoca sono creati con DDL dinamico da
`script.trgfn_config_sistema_codici_sync_gen_codice` — il trigger
`AFTER INSERT OR UPDATE OR DELETE` di `config.sistema_codici`. Basta la riga
`codice_interno = 'offerta_commerciale'` con `schema_tabella`, `nome_tabella`, `nome_colonna` valorizzati
e `usa_sequenza = true`, e i tre oggetti nascono da soli.

È il motivo per cui **tutte** le `trgfn_*_gen_codice` del progetto hanno corpo identico: non
sono sette funzioni simili, sono la stessa funzione parametrizzata sette volte.

Conseguenze pratiche:

* **Modificarla a mano non serve a niente.** Il loader del CSV `sistema_codici` è
  `runOnChange`, quindi ripassa a ogni migrate: la funzione viene riscritta col template e
  qualunque ritocco locale sparisce senza lasciare traccia.
* **Non si spegne con un `DROP`, si spegne dalla configurazione.** Portando `usa_sequenza`
  a `false` il trigger di sync cancella da sé trigger e funzione; un `DROP` manuale li fa
  ricomparire al primo migrate.
* **Cambiare `schema_tabella`/`nome_tabella`/`nome_colonna` sposta gli oggetti**: il sync
  fa `DROP` di quelli vecchi e ricrea altrove. Nessun errore, nessun avviso.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_SEQUENZA_NON_CONFIGURATA` | `script.fn_generate_codice` | Nessuna riga `codice_interno = 'offerta_commerciale'` in `config.sistema_codici` |

La funzione non solleva errori propri.

---

{% include-markdown "signature-core.md" %}
