## 📘 Documentazione Concettuale – Funzione `script.fn_is_proprietario_tabella()`

> 👀 **Vedi anche**
>
> **Chi la chiama:** [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) · [magazzino.trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata) · [ui.trgfn_lista_definizione_guard_multi_emittente](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_multi_emittente)
>
> **I guard che chiedono chi agisce (non chi esegue):** [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) · [script.fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Risponde a una domanda sola: **chi sta eseguendo questa istruzione è il
proprietario della tabella?**

È il modo in cui un guard capisce da dove arriva una scrittura. Nel modello «una
scrittura = un verbo» l'app non scrive direttamente sulle tabelle protette:
chiama un verbo, cioè una funzione che gira con i privilegi del proprietario.
Dentro il verbo chi esegue è il proprietario, e la risposta è sì. Quando è l'app
a scrivere da sola, la risposta è no.

⚠️ Non va confusa con `fn_guard_azione` e `fn_guard_super_admin`. Quelle guardano
**la persona** che agisce (l'utente dichiarato dal backend). Questa guarda **il
ruolo del database** che esegue: dice se la scrittura passa da un verbo, non chi
l'ha chiesta.

---

### Cosa risponde

| Situazione | Esito |
| --- | --- |
| dentro un verbo del proprietario, oppure durante il migrate | `true` |
| un superuser | `true` |
| l'app che scrive direttamente | `false` |
| tabella `NULL` o inesistente | `false`: nel dubbio, no |

È una **check**: risponde e non blocca. Chi la usa decide cosa fare del no, di
solito sollevando il proprio codice di errore.

Il proprietario non è scritto da nessuna parte: si legge dal catalogo, perché
cambia da un database all'altro (chi migra è il proprietario).

⛔ Deve restare **SECURITY INVOKER**. Se girasse con i privilegi del suo
proprietario, vedrebbe sempre il proprietario come esecutore e direbbe sì a
chiunque. Il pgTAP lo controlla.

In un trigger si passa la tabella su cui è montato:

```sql
IF NOT script.fn_is_proprietario_tabella(TG_RELID) THEN
    -- rifiuto
END IF;
```

---

### Cosa non protegge

Il limite è quello del modello: protegge da un backend **che sbaglia**, non da uno
manomesso, e non ferma il proprietario. Un amministratore del database che scrive
come proprietario passa. È voluto (brief-db-permesso-nel-verbo-di-scrittura §4.4).

---

### Storia

* 2026-09-25 — nasce con la decisione D-V1 (`20260925-37`,
  brief-db-magazzino-verbi-con-permesso). Era la seconda occorrenza della stessa
  regola: la prima stava nel guard di `ui.lista_definizione.multi_emittente`, che
  nello stesso giro passa da qui (`20260925-39`).

{% include-markdown "signature-core.md" %}
