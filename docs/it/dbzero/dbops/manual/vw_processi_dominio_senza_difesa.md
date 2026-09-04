## 📘 Documentazione Concettuale – View `dbops.vw_processi_dominio_senza_difesa`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi_bersagli](/dbzero/dbops/manual/processi_bersagli)
>
Approfondimenti funzioni:
>
[script.trgfn_guard_emittente_scope](/dbzero/script/manual/trgfn_guard_emittente_scope)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Elenca le tabelle di dominio in cui **si sa dove sta l'emittente, ma nessuno lo
usa per filtrare**: né una policy di row level security, né un guard di
scrittura.

> ⚠️ È un **debito dichiarato**, non un allarme. Deve **calare**, non essere
> vuoto entro sera.

---

### ⭐ La differenza con la vista gemella, che è il motivo per cui sono due

| Vista | Che cosa manca |
| --- | --- |
| `vw_processi_dominio_senza_emittente` | **l'informazione**: non si sa di chi è la riga |
| **questa** | l'informazione c'è, **manca chi la applica** |

⛔ Fonderle sarebbe stato comodo e sbagliato: sono due lavori diversi, con due
tempi diversi e due sedi diverse. Il primo si chiude scrivendo una riga di
censimento o aggiungendo una colonna; il secondo scrivendo una **policy**, che
è una decisione di sicurezza e va presa con calma.

⇒ Un elenco che mescola «da compilare» e «da proteggere» diventa un elenco di
niente: nessuno sa quali righe siano urgenti.

---

### Le prime righe attese

* `vendite.listini*` — il listino è stato dichiarato di dominio, il percorso
  all'emittente c'è (passa dal listino padre), ma **nessuna policy lo applica**.
* `config.email_outbox` — compare qui solo quando avrà la colonna emittente:
  finché non ce l'ha, sta nell'altra vista.

⚠️ Nessuno dei due è un guasto introdotto da questo cantiere: erano scoperti
**prima**, ed erano invisibili perché nessuno faceva la domanda.

---

### Che cosa vuol dire «senza difesa», in pratica

Che qualunque utente collegato all'applicazione — anche uno di un'altra azienda
— può leggere e scrivere quelle righe. Non serve un errore, non serve un
attacco: basta un'operazione normale fatta dalla persona sbagliata.

---

### Esempio d'uso

```sql
-- Il debito, e quanto è grande oggi
SELECT schema_tabella, nome_tabella, processo_codice
FROM dbops.vw_processi_dominio_senza_difesa
ORDER BY schema_tabella, nome_tabella;
```

Origine: `docs/it/dev/work-in-progress/brief-db-processi-automatici-identita-e-perimetro.md` §8.

---

{% include-markdown "signature-core.md" %}
