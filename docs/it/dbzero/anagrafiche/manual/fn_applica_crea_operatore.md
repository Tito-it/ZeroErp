## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_applica_crea_operatore`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore) — il verbo che la chiama, col permesso
> * [anagrafiche.fn_crea_primo_amministratore](/dbzero/anagrafiche/funzioni/fn_crea_primo_amministratore) / [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) / [dbops.fn_pgtap_fixture_crea_operatore](/dbzero/dbops/funzioni/fn_pgtap_fixture_crea_operatore) — gli altri chiamanti
> * [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana) / [anagrafiche.fn_crea_auth_user](/dbzero/anagrafiche/funzioni/fn_crea_auth_user) — i passi interni
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — l'assunzione
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §7.4, le primitive che l'app non esegue

---

### 🎯 Scopo Principale

Crea un operatore in una transazione: la credenziale (o il riuso col consenso), il soggetto, la risorsa umana,
la veste `OPERATORE` spenta, il legame SUPER_ADMIN se richiesto, gli indirizzi. Ha tutte le regole della
creazione, raccontate nella pagina del verbo
[fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore), ma **non chiede permessi**: il verbo chiede
il SUPER_ADMIN, e poi chiama lei.

Firma, risultato e rifiuti sono quelli del verbo, tranne `E_PERMESSO_NEGATO`. I testi d'errore portano il nome
del verbo, quello che il backend e l'operatore conoscono.

---

### ⛔ Chi la esegue

Solo il proprietario. L'applicazione non ha `EXECUTE`, e nemmeno `PUBLIC`: se l'avesse, il permesso
del verbo si aggirerebbe chiamando lei. La postura sta nelle tre sedi del loop dei grant (linee guida
SQL §11.8, `v_fn_riservate`).

È `SECURITY INVOKER`: gira dentro una funzione `SECURITY DEFINER` del proprietario.

La chiamano, senza un SUPER_ADMIN in sessione:

* il primo amministratore, quando un SUPER_ADMIN non c'è ancora per costruzione;
* il provisioning di sviluppo, lanciato dal comando del backend senza utente;
* la fixture dei pgTAP `dbops.fn_pgtap_fixture_crea_operatore`, solo dove sono ammessi i dati di sviluppo.

Test: `db/pgtap/anagrafiche/test-fn-crea-operatore.sql`, `db/pgtap/config/test-porta-tabelle-accesso-v1.sql`.
