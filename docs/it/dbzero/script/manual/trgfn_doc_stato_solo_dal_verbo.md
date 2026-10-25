## 📘 Documentazione Concettuale – Trigger `script.trgfn_doc_stato_solo_dal_verbo()`

> 👀 **Vedi anche**
>
> [script.fn_doc_scrivi_stato](/dbzero/script/funzioni/fn_doc_scrivi_stato) ·
> [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5 ·
> guida [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) §7.4

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §7, decisione S-1 b)

**La porta.** Lo stato di un documento sul modello si cambia **solo dal suo
verbo**. Il verbo protegge solo se non si può aggirare: una testata
l'applicazione la scrive anche per i campi ordinari, quindi non le si toglie la
scrittura sulla tabella. Si chiude la sola colonna di stato, e con un trigger:
un permesso sulla singola colonna non regge, perché il giro dei permessi di ogni
rilascio rimette quelli di tabella.

Un cambio della colonna di stato passa solo se sono vere **insieme**:

* la variabile di transazione `zeroerp.doc_cambio_stato` porta questa testata e
  questo documento (la scrive `script.fn_doc_scrivi_stato`);
* chi scrive è il proprietario della tabella (`script.fn_is_proprietario_tabella`):
  un verbo `SECURITY DEFINER`, non l'applicazione che accende la variabile da sé.

Altrimenti `E_DOC_STATO_SOLO_DAL_VERBO` (tecnico: nessuna maschera cambia lo stato
con una modifica diretta). Un aggiornamento che riscrive lo stesso stato passa.

### Dove è montato

`trg_<tabella>_a05_stato_solo_dal_verbo_upd`, `BEFORE UPDATE OF` la colonna di
stato, fascia `_a05_` (il rifiuto che parla per primo), su **bolla e reso**: i
documenti portati al modello. Gli altri lo ricevono nel giro del loro documento.
La colonna la dice la mappa (`script.fn_doc_stato_modello`): nessun argomento.

### Regole

* Prende il posto delle due porte del registro di magazzino di bolla e reso, che
  chiudevano solo i passaggi che muovono merce (`E_DDT_STATO_SOLO_DA_VERBO`,
  `E_RESO_STATO_SOLO_DA_VERBO`, ritirati). La porta dei documenti interni di
  magazzino resta loro: non hanno un vocabolario degli stati in tabella.
* Nessun altro trigger `BEFORE` scrive la colonna di stato di bolla e reso: per
  questo `UPDATE OF` è la forma giusta (linee guida trigger).

### Presidio

`db/pgtap/script/test-doc-verbo-comune-e-porta-v1.sql`: montaggio dal catalogo,
rifiuto dell'`UPDATE` diretto (anche con la variabile accesa dall'applicazione),
il verbo con e senza l'azione, il passaggio di processo, le capability.
