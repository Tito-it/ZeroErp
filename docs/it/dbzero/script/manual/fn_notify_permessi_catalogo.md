## 📘 Documentazione Concettuale – Funzione `script.fn_notify_permessi_catalogo()`

> 👀 **Vedi anche**
>
> **Chi la chiama:** [script.trgfn_notify_permessi_catalogo](/dbzero/script/funzioni/trgfn_notify_permessi_catalogo) (i trigger del catalogo permessi) · chi corregge a mano (leva manuale, sotto)
>
> **Guida:** [Architettura permessi](/guide/architettura-permessi-e-autorizzazioni) § 6.1, «La cache fra una richiesta e l'altra»

---

### 🎯 Scopo Principale
(scritta il 04-10-2026)

Avvisa il backend che i permessi sono cambiati, perché svuoti la **cache dei
permessi di tutti gli utenti**. Senza questo avviso, chi cambia il catalogo dei
permessi fuori dall'applicazione (l'aggiornamento del seed, una correzione a
mano) lascerebbe gli utenti a lavorare coi permessi vecchi fino alla scadenza
della cache.

L'avviso è una notifica PostgreSQL sul canale `permessi_catalogo`, con dentro il
nome della tabella cambiata. La raccoglie il processo sempre acceso
`listen_permessi`.

| Cosa succede alla scrittura | Avviso |
| --- | --- |
| la transazione viene confermata | parte, al momento della conferma |
| la transazione viene annullata | non parte |
| più scritture sulla stessa tabella nella stessa transazione | uno solo |

### 🛠️ La leva manuale

Dopo una correzione fatta a mano su una tabella che **non** avvisa da sé (per
esempio l'identità digitale di un operatore, o i suoi override):

```sql
SELECT script.fn_notify_permessi_catalogo('manuale');
```

svuota la cache di tutti. Costa un ricalcolo dei permessi per ogni utente, alla
sua richiesta successiva.

Un nome vuoto o mancante è rifiutato con `E_PARAMETRO_INVALIDO`.

Presidio: `db/pgtap/script/test-notify-permessi-catalogo-v1.sql`.

{% include-markdown "signature-core.md" %}
