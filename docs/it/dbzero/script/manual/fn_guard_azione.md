## 📘 Documentazione Concettuale – Funzione `script.fn_guard_azione()`

> 👀 **Vedi anche**
>
> **La regola che applica:** [script.fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo) — la stessa funzione che usa il backend
>
> **Chi la chiama:** i verbi di scrittura che applicano un'azione di processo (il primo cantiere è magazzino: `fn_posta_inventario`, `fn_posta_rettifica`)
>
> **Per i test:** [dbops.fn_pgtap_concedi_azione](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione)
>
> **Modello e decisioni:** brief-db-permesso-nel-verbo-di-scrittura (D-1, D-2) · **Piano:** brief-db-magazzino-verbi-con-permesso §2.1

---

### 🎯 Scopo Principale
(scritta il 24-09-2026)

È il guard con cui **il database applica** un'azione di processo. Si chiama
nella prima riga di un verbo di scrittura: se chi agisce non ha l'azione, il
verbo si ferma prima di toccare qualunque cosa.

Fino a questa funzione il database **calcolava** i permessi ma non li
**applicava**: lo faceva solo il backend. Se il backend sbagliava, per esempio con
un permesso dichiarato male su un endpoint, la scrittura passava. Con il guard nel
verbo, lo stesso errore si ferma nel database.

---

### Una regola, due punti in cui si applica

Il guard **non contiene la regola**. Chiede a `script.fn_check_azione_processo`,
la stessa funzione che il backend chiama per decidere se mostrare un'azione e se
accettarla. Dentro quella funzione ci sono già tutti i passi: il contesto (solo
la veste OPERATORE), l'identità attiva, il super admin, le eccezioni del singolo
utente, i profili.

Quindi backend e database **non possono rispondere in modo diverso**: fanno la
stessa domanda alla stessa funzione. Cambia solo chi si ferma quando la risposta
è no.

---

### Cosa risponde

| Situazione | Esito |
| --- | --- |
| L'utente ha l'azione | niente: il verbo prosegue |
| L'utente non ha l'azione | `E_PERMESSO_NEGATO`, lo stesso codice (e la stessa frase) del backend |
| Nessun utente in sessione | `E_PERMESSO_NEGATO`, con `senza_utente = true` nel contesto: chi non dichiara chi è non scrive |
| L'azione non esiste in `config.azioni_processo` | `E_CONFIG_MANCANTE`: è il verbo che nomina un'azione sbagliata, non un permesso mancante |

⚠️ **Perché l'azione inesistente ha un errore suo.** Con un nome sbagliato la
regola risponderebbe «no» a tutti, per sempre. Il verbo direbbe a ogni operatore
«non hai i permessi», e si cercherebbe nei profili un difetto che sta nel codice.

⚠️ **Si controlla che l'azione esista, non che sia attiva**: la regola del
backend non guarda `attivo`, e il guard non deve rispondere diversamente.

---

### Come si usa

L'utente arriva come **parametro**. Il verbo lo legge dalla sessione con la
stessa espressione delle policy RLS (linee-guida-sql §10.4):

```sql
PERFORM script.fn_guard_azione(
    NULLIF(current_setting('app.current_user_id', true), '')::integer,
    'registra_magazzino');
```

⭐ Se il verbo è `SECURITY DEFINER`, la sessione è comunque quella
dell'operatore: le GUC non cambiano con il proprietario della funzione.

---

### Cosa non fa

* **Non controlla il perimetro** (quale emittente): quello resta alle policy RLS
  o, dentro un verbo `SECURITY DEFINER`, al predicato della policy chiamato dal
  verbo.
* **Non controlla il livello d'area.** La forma «livello sull'oggetto» (D-2, D-5)
  nascerà con il suo primo consumatore, il verbo generico del pannello di
  configurazione.
* **Non protegge da un backend manomesso**: l'utente in sessione lo dichiara il
  backend. Protegge da un backend che sbaglia.

---

### Storia

* 2026-09-24 — nasce con il primo cantiere del modello «una scrittura = un verbo» (`20260924-38`).

{% include-markdown "signature-core.md" %}
