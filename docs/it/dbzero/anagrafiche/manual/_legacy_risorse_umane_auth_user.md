## 📘 Documentazione Concettuale – Tabella `anagrafiche._legacy_risorse_umane_auth_user`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> • [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
Approfondimento viste:
> • [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/views/risorse_umane_auth_user)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

⛔ **Tabella archiviata. Non scrivere qui.**

Era il ponte fra risorsa umana e utente applicativo prima del cutover **multi-face-auth** del
2026-04-19 (§13.3.2). Da allora il legame passa da `anagrafiche.identita_digitali`, e al suo
posto c'è la **vista** `anagrafiche.risorse_umane_auth_user`, che legge da lì e mantiene lo
stesso nome per i consumatori.

Resta per la consultazione storica dei dati **pre-cutover**: 6 righe al 2026-08-21.

---

### ⚠️ Perché non è stata cancellata

Il prefisso `_` dice «archiviata», e la tentazione di droppare una tabella con sei righe è
comprensibile. Non va fatto, per due ragioni concrete:

1. **La vista che la sostituisce ne ha ereditato il nome**, non i dati. Le righe qui dentro
   sono lo stato *precedente* al cutover: se un giorno servisse ricostruire chi era collegato
   a quale utente prima di aprile 2026, questa è l'unica fonte.
2. **È citata da 4 changeSet e da 2 pgTAP** (`test-permessi-strutture-base.sql`,
   `test-user-emittenti-fiscali-immutable.sql`). Toglierla farebbe fallire dei test per un
   motivo che non c'entra con ciò che verificano.

⚠️ Va tenuta distinta dai residui veri del progetto — one-shot di migrazione già consumati e
tabelle di backup — che nessuno nomina e che si lasciano dove sono. Questa **è nominata**, e
non è un residuo: è un archivio.

---

### Come leggerla

La struttura è quella di allora: `risorsa_umana_id`, `auth_user_id`, `attivo`, `meta`, più
audit, `storicizza` e `tx_id`. La colonna `ruolo_sistema` **non c'è più**: l'ha rimossa
`90_end/20260429-19a` durante il cutover, ed è stata la causa di un riferimento morto in un
pgTAP che per mesi non aveva mai eseguito le proprie asserzioni.

⭐ Quella storia vale più della tabella: il test si chiamava «immutable» e la regola che
dichiarava di verificare **non esisteva** nel database. Riparato il riferimento, la prima
asserzione è uscita «no exception thrown», ed è così che è nato il lock su
`config.user_emittenti_fiscali`.

---

{% include-markdown "signature-core.md" %}
