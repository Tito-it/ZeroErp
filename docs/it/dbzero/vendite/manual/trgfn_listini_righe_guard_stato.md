## 📘 Documentazione Concettuale – Funzione Trigger `vendite.trgfn_listini_righe_guard_stato`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) — la regola ·
> [script.fn_check_listino_riga_rettificabile](/dbzero/script/manual/fn_check_listino_riga_rettificabile) — la rettifica ·
> [vendite.fn_rettifica_riga_listino](/dbzero/vendite/manual/fn_rettifica_riga_listino) — il verbo della rettifica ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) ·
> [vendite.vw_listini_righe_azioni](/dbzero/vendite/manual/vw_listini_righe_azioni) ·
> [config.azioni_riga](/dbzero/config/manual/azioni_riga) ·
> [config.stati_doc_listino_versioni](/dbzero/config/manual/stati_doc_listino_versioni)

---

### 🎯 Scopo Principale

Il guard delle righe di listino secondo lo stato della versione: **le righe si scrivono solo in
bozza**. La regola non sta qui: sta in
[`script.fn_check_listino_riga_scrivibile`](/dbzero/script/manual/fn_check_listino_riga_scrivibile),
e il guard ne solleva il primo motivo (`script.fn_raise_primo_motivo_se_presente`). Le stesse
risposte le danno le superfici che il frontend legge, quindi il pulsante e l'errore non possono
dire due cose diverse (linee guida SQL §12.5.2).

---

### Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT OR UPDATE OR DELETE`, per riga, su `vendite.listini_righe`
* **Nome trigger**: `trg_listini_righe_a10_guard_stato_ins_upd_dlt`
* **Fase**: `_a10_` (guard)

---

### Che cosa ammette

| Versione | Riga nuova, modifica, eliminazione | Rettifica del prezzo (dal verbo) |
| --- | --- | --- |
| in bozza (lo stato `iniziale` del vocabolario) | sì | no: si modifica (`E_RIGA_LISTINO_RETTIFICA_IN_BOZZA`) |
| `ATTIVA`, in vigore oggi | no (`E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA`) | sì, finché il prezzo non è stato usato (`E_RIGA_LISTINO_PROPAGATA`) |
| `ATTIVA`, non ancora iniziata o già finita | no (`E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA`) | no (`E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE`) |
| `CHIUSA` | no (`E_RIGA_LISTINO_VERSIONE_CHIUSA`) | no (`E_RIGA_LISTINO_VERSIONE_CHIUSA`) |

### La porta della rettifica

La sola scrittura di una riga fuori dalla bozza è la rettifica, che passa dal verbo
[`vendite.fn_rettifica_riga_listino`](/dbzero/vendite/manual/fn_rettifica_riga_listino) (motivo
obbligatorio, traccia in `meta`). Il verbo apre la porta per una riga (variabile di transazione
`zeroerp.listino_riga_rettifica` = id della riga); il guard la onora solo dal proprietario della
tabella, e solo per un UPDATE che cambia il prezzo e `meta`. Lì risponde
[`script.fn_check_listino_riga_rettificabile`](/dbzero/script/manual/fn_check_listino_riga_rettificabile).
Una porta aperta che cambia altro ricade sulla regola di sempre. È la stessa forma della porta di
`valido_al` di una versione attiva.

---

### Il verbo nel registro

Le righe si aggiungono, si modificano e si eliminano direttamente (il backend fa `INSERT`,
`UPDATE`, `DELETE`): chi le rifiuta è questo guard. Per questo è il `verbo` delle azioni
`AGGIUNGI_RIGA_LISTINO` e `MODIFICA_RIGA_LISTINO` in
[`config.azioni_riga`](/dbzero/config/manual/azioni_riga): un'aggiunta, una modifica o
un'eliminazione tocca sempre una riga, e il guard la giudica.

La variazione percentuale no: è un gesto della versione, che può non prendere nessuna riga (un
filtro che non trova articoli, una versione senza righe attive), e lì il guard non scatterebbe. Ha
il suo verbo,
[`vendite.fn_varia_prezzi_versione_listino`](/dbzero/vendite/manual/fn_varia_prezzi_versione_listino),
che chiede la stessa regola per la versione prima di toccare le righe. Le righe che scrive passano
comunque da qui.

---

### Test

* `db/pgtap/vendite/test-listino-riga-scrivibile-v1.sql` — la check, le superfici e i tre guard
  rispondono uguale, con la marca `iniziale` spostata.
* `db/pgtap/vendite/test-listino-rettifica-riga-v1.sql` — il verbo, la porta, la superficie della
  rettifica.

---

{% include-markdown "signature-core.md" %}
