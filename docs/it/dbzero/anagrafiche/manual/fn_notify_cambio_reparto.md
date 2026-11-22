## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_notify_cambio_reparto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro, che porta il reparto
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste operatore da cui si risale alla credenziale
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — i reparti
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_risorse_umane_notify_cambio_reparto](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_notify_cambio_reparto) — il trigger che la chiama
> * [script.fn_get_auth_user_id_for_risorsa_umana](/dbzero/script/funzioni/fn_get_auth_user_id_for_risorsa_umana) — dalla risorsa umana alla sua credenziale
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — il rapporto di lavoro e la veste operatore

---

### 🎯 Scopo Principale

`anagrafiche.fn_notify_cambio_reparto` invia sul canale `cambio_reparto` l'avviso che una risorsa umana ha cambiato
reparto, con la credenziale a cui il backend deve ricalcolare i permessi.

Non scrive dati: pubblica un evento. Il backend lo riceve da un processo che ascolta il canale, e toglie dalla sua
memoria temporanea i permessi di quella credenziale.

---

### Che cosa porta l'avviso

Il rapporto di lavoro, il reparto di prima e quello nuovo (ciascuno può essere vuoto), e la credenziale della
persona. La credenziale la trova `script.fn_get_auth_user_id_for_risorsa_umana`, che passa dalla veste `OPERATORE`
sullo stesso ruolo del rapporto: se ce n'è più d'una sceglie quella accesa, poi la più recente. Una risorsa umana
senza veste operatore manda l'avviso con la credenziale vuota, e il backend lo ignora: non ci sono permessi da
ricalcolare.

L'avviso parte quando la transazione si conferma, non quando la funzione gira.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il rapporto non è indicato, o non è un id valido. Chiamata dal suo trigger non succede:
  il trigger passa sempre l'id della riga.

---

### Test

* `db/pgtap/anagrafiche/test-notify-cambio-reparto.sql` — la funzione gira senza errori con due reparti, coi reparti
  vuoti e su una risorsa umana senza veste.

Nessun test verifica il contenuto dell'avviso, né il rifiuto di un id non valido.

---

### Note di migrazione

* 2026-09-12 — la credenziale si trova dalla veste operatore; prima si leggeva dalla tabella ponte
  `risorse_umane_auth_user`, poi diventata una vista e ritirata.

---

{% include-markdown "signature-core.md" %}
