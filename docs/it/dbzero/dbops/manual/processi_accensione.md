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
riga qui lo **scavalca** su questa macchina.

| La riga | Che cosa dice |
| --- | --- |
| `acceso = true` / `false` | acceso o spento a mano, al posto del default |
| `acceso = NULL` | qualcuno l'ha **rimesso al default**: vale il default, e la riga dice chi, quando e perché |
| nessuna riga | nessuno l'ha mai toccato: vale il default |

(17-10-2026) «Torna al default» non cancella la riga: la riscrive con `acceso`
vuoto e il motivo, come gli altri due gesti.

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

### La storia dei gesti
(17-10-2026 — S-1 del brief)

La riga è l'**ultimo** gesto. Tutti i gesti restano nella gemella
`storico.processi_accensione`: la tabella è nell'ambito delle automazioni del
database e nel registro dello storico, quindi ogni modifica lascia una
versione (chi, quando, acceso, motivo).

**Chi** è la persona, non il ruolo del database: `user_insert` e `user_update`
li scrive l'audit automatico, che legge l'utente collegato al backend
(`app.jwt_user`). Fino al 16-10-2026 li scriveva il verbo, e dal backend
risultava sempre `zeroerp_app`.

⚠️ I trigger dell'audit e dello storico nascono dalle automazioni (`ci_apply`
in CI e a ogni installazione; su un database di sviluppo, dai job notturni
`automations_*`). Fra la migrazione e il loro primo giro la tabella non ha
storia.

---

{% include-markdown "signature-core.md" %}
