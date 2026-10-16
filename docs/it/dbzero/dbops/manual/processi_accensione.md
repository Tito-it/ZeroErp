## 📘 Documentazione Concettuale – Tabella `dbops.processi_accensione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi](/dbzero/dbops/manual/processi)
> • [dbops.installazione](/dbzero/dbops/manual/installazione)
>
**Approfondimento funzioni:**
>
• [dbops.fn_imposta_accensione_processo](/dbzero/dbops/manual/fn_imposta_accensione_processo)
> • [maintenance.fn_sveglia_accesa](/dbzero/maintenance/manual/fn_sveglia_accesa)
>

### 🎯 Scopo Principale
(16-10-2026 — brief `brief-db-processi-accensione-per-ambiente`)

**La scelta a mano di questa installazione** sulla sveglia di un processo
automatico: «qui lo spengo» (o «qui lo accendo»), e perché.

Il catalogo [dbops.processi](/dbzero/dbops/manual/processi) dice il default
per ambiente: acceso o spento in sviluppo, acceso o spento in produzione. Una
riga qui lo **scavalca** su questa macchina. Nessuna riga = vale il default.

È un dato di **macchina**, come `processi_identita`: nessun seed, la scrive
l'operatore dal drawer dei processi, attraverso il verbo
[fn_imposta_accensione_processo](/dbzero/dbops/manual/fn_imposta_accensione_processo).

---

### I limiti (guard `trgfn_processi_accensione_guard`)

| Cosa si chiede | Risposta |
| --- | --- |
| una scelta su un processo senza sveglia (`CODA`, ritirato) | rifiutata: `E_PROCESSO_SENZA_SVEGLIA` |
| spegnere un processo **non spegnibile** | rifiutato: `E_PROCESSO_NON_SPEGNIBILE` |
| confermare acceso un non spegnibile | ammesso (non cambia niente) |
| una scelta senza motivo | rifiutata: `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO` |

⚠️ Se il catalogo rende un processo non spegnibile **dopo** che una riga l'ha
spento, il processo non resta spento: la regola ignora la scelta a mano su un
non spegnibile.

---

### ⚠️ Cosa non c'è

Le automazioni del database (audit, tx_id, storico) non coprono lo schema
`dbops`. La riga dice l'**ultima** scelta, con chi e quando (`data_update` e
`user_update` li scrive il verbo) e il motivo. Una storia di tutte le scelte,
se servirà, è un cantiere a parte.

---

{% include-markdown "signature-core.md" %}
