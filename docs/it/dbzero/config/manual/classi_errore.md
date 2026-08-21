## 📘 Documentazione Concettuale – Tabella `config.classi_errore`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
> • [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento viste:
> • [config.vw_codici_errore](/dbzero/config/views/vw_codici_errore)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Vocabolario di **che cosa è** un errore, detto in lingua di dominio: il *tipo di rifiuto*, non
il suo trasporto. Dieci voci — `DATO_ERRATO`, `CONFLITTO_STATO`, `NON_TROVATO`, `TECNICO`,
`NON_PERMESSO`, `NON_ESEGUIBILE`, `NON_DISPONIBILE`, `AVVISO`, `NON_AUTENTICATO`,
`ERRORE_ESTERNO` — che rispondono alla domanda «di che natura è questo rifiuto?».

È il primo dei **tre lati** del modello degli errori:

| Lato | Dove | Risponde a |
|---|---|---|
| **classe** | `config.classi_errore` | che *tipo* di errore è |
| **identità** | `config.codici_errore` | quale errore è, ed è ancora in servizio? |
| **frase** | `config.messaggi_errore` | che cosa legge l'operatore, in che lingua |

---

### ⚠️ La mappa verso HTTP **non** è qui

`classi_errore` non conosce gli stati HTTP. La traduzione classe → status → azione UI vive
nel backend, in `apps/core/services/error_policies.py`, ed è deliberato: il database dice di
che natura è il rifiuto, il trasporto lo decide chi espone l'API.

Conseguenza pratica: **aggiungere una classe qui non basta**. Finché il backend non la mappa,
gli errori di quella classe finiscono nel comportamento di default. Il registro del debito su
questo è `dbops.codici_errore_senza_policy`.

---

### Deprecare, non cancellare

La colonna è `obsoleto_dal`, non `attivo`. È il pattern del progetto per le voci di catalogo:
una classe deprecata resta, perché i codici che la referenziano continuano a esistere e a
comparire nei log storici. `obsoleto_dal` è l'asse «selezionabile per il nuovo», non
«esistente».

Cancellare una classe romperebbe la FK da `config.codici_errore.classe`.

---

### Popolamento

Seed `80_data`, dal CSV `80_data/sql/config/classi_errore.csv`, tramite il loader mirror
`runOnChange` `20260614-08` — lo stesso che carica, **nell'ordine**, `classi_errore` →
`codici_errore` → `messaggi_errore`.

⚠️ L'ordine non è casuale: `codici_errore.classe` ha una FK verso qui, e un loader che
arrivasse prima troverebbe la tabella vuota. Chi aggiunge una classe la aggiunge **al CSV**,
mai con un `INSERT` a parte.

---

{% include-markdown "signature-core.md" %}
