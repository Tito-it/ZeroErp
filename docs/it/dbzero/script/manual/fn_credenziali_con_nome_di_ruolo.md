## 📘 Documentazione Concettuale – Funzione `script.fn_credenziali_con_nome_di_ruolo`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare) — chiamante: il motivo `NOME_DI_RUOLO_DB`
>
> Approfondimento funzioni:
>
> * [dbops.fn_ruolo_del_migratore](/dbzero/dbops/funzioni/fn_ruolo_del_migratore) — la domanda che un nome così inganna

---

### 🎯 Scopo Principale

Elenca le credenziali dell'applicazione (`django.auth_user`) il cui username è `SEED` o il nome di un
ruolo del database, senza distinguere maiuscole e minuscole.

Una credenziale così inganna il riconoscimento delle righe di seed. Quando il runner del seed di
primo impianto iscrive una tabella, una riga col suo nome in `user_insert` sembrerebbe nata dal
seed, e il CSV ne prenderebbe possesso.

---

### Perché una funzione e non un pezzo della vista

È l'accessore di [vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare): una vista
che nominasse `django.auth_user` dipenderebbe dallo schema `django` già alla creazione, e su un
database ricostruito da zero lo schema non c'è ancora. Il corpo `plpgsql` risolve il nome solo
quando gira.

---

### Test

Nessun pgTAP diretto: il motivo `NOME_DI_RUOLO_DB` si legge sulla vista, dove su un database pulito
vale zero.

---

### Note di migrazione

* 2026-11-17 — nasce, con il terzo motivo del presidio delle credenziali
  (`brief-db-seed-primo-impianto-non-si-riscrive`, Q17).

---

{% include-markdown "signature-core.md" %}
