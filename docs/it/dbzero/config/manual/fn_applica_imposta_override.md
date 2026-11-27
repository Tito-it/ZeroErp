## 📘 Documentazione Concettuale – Funzione `config.fn_applica_imposta_override`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) / [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) / [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti) — le tre tabelle che scrive
>
> Approfondimento funzioni:
>
> * [config.fn_imposta_override_aree](/dbzero/config/funzioni/fn_imposta_override_aree) / [config.fn_imposta_override_azioni](/dbzero/config/funzioni/fn_imposta_override_azioni) / [config.fn_imposta_override_oggetti](/dbzero/config/funzioni/fn_imposta_override_oggetti) — i verbi che la chiamano, col permesso
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — l'altro chiamante
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.8 chi scrive gli override, §7.4 le primitive che l'app non esegue

---

### 🎯 Scopo Principale

**Sostituisce le eccezioni di un utente** su una delle tre tabelle (aree, azioni, oggetti) con
l'elenco dato, e ritorna quante ne scrive. Ha le regole dei tre verbi, ma **non chiede permessi**:
è la primitiva sotto di loro, che chiedono il SUPER_ADMIN.

* la tabella è un argomento, e le chiavi ammesse di ognuna stanno nella primitiva: una tabella fuori
  dalle tre si rifiuta (`E_SCRIPT_CHIAMATA_NON_VALIDA`);
* una chiave che la tabella non ammette: `E_CAMPO_NON_AMMESSO`;
* **ogni voce porta un motivo**, anche quella che toglie un permesso (`BLOCCATO`, `abilitata = false`):
  il motivo è il perché dell'eccezione, e senza di lui nessuno sa più spiegarla. Assente, vuoto, di soli
  spazi o non di testo: `E_OVERRIDE_MOTIVO_OBBLIGATORIO`, sul campo `motivo`, con la posizione della
  voce (`indice`, da 0) e la sua chiave nel contesto. Si scrive senza spazi in testa e in coda. Togliere
  una voce, cioè lasciarla fuori dall'elenco, non chiede motivo;
* l'elenco si giudica tutto prima di toccare una riga, prima le chiavi poi il motivo: un rifiuto lascia
  le eccezioni di prima, e il motivo mancante si dice anche se un'altra voce cadrebbe sul catalogo;
* una chiave assente prende il valore di partenza della colonna, una scritta vuota scrive vuoto;
* catalogo, riservati e date li controllano i vincoli e i trigger della tabella.

Gli errori portano il nome del verbo della tabella: chi legge il codice sa da quale schermata viene.

---

### ⛔ Chi la esegue

Solo il proprietario. L'applicazione non ha `EXECUTE`, e nemmeno `PUBLIC`: se l'avesse, il permesso
dei verbi si aggirerebbe chiamando lei. La postura sta nelle tre sedi del loop dei grant (linee guida
SQL §11.8, `v_fn_riservate`).

È `SECURITY INVOKER`: gira dentro una funzione `SECURITY DEFINER` del proprietario. La chiamano i tre
verbi e il provisioning dei dati di sviluppo, che gira senza un SUPER_ADMIN in sessione.

---

### Test

`db/pgtap/config/test-porta-override-permessi-v1.sql`, `db/pgtap/config/test-fn-imposta-override-emittente-attivo-v1.sql`,
`db/pgtap/config/test-override-motivo-obbligatorio-v1.sql` (il motivo, sulle tre tabelle).

---

### Note di migrazione

* 2026-11-27 — nasce dal corpo di `fn_imposta_override_oggetti`, per le tre tabelle: i tre verbi
  avrebbero avuto lo stesso corpo tre volte (brief-db-porte-aperte-dalla-sola-guc, giro 10-quater).
* 2026-11-27 — il motivo diventa obbligatorio, come già diceva la guida dei permessi; le righe scritte
  prima restano, e la loro prossima riscrittura lo chiede (brief-db-motivo-override-obbligatorio).

---

{% include-markdown "signature-core.md" %}
