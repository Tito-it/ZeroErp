## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_provisiona_dati_di_sviluppo()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, R-4, 2b-3)

**Creare, o rimettere a posto, gli utenti e i dati di prova** di
un'installazione di sviluppo. La chiama il comando del backend; in un
database di produzione non parte.

### Che cosa crea

* due aziende emittenti di prova (`DEVA`, `DEVB`), ciascuna col suo magazzino
  predefinito;
* i clienti di prova 1, 2 e 3 sull'azienda A e il cliente B sull'azienda B,
  ciascuno col suo conto di fatturazione;
* il fornitore di prova 1;
* gli operatori `dev.smoke` (super admin), `dev.lettura`, `dev.bloccato`
  (senza accesso ai contratti), `dev.emittente` (solo l'azienda A),
  `dev.multiveste`, ciascuno con la sua persona;
* gli utenti dei portali `dev.portale1`, `dev.portale2` (clienti 1 e 2),
  `dev.fornitore` (fornitore 1), e il portale di `dev.multiveste` (cliente 3).

Tutto ciò che crea porta l'etichetta di prova.

### Le regole

* **Si può rilanciare.** Una seconda corsa ritrova ogni utente e soggetto
  dalla sua etichetta e lo rimette a posto: accessi accesi, profili (su tutte
  le aree che ci sono in quel momento), aziende, eccezioni, azienda attiva.
* **Un omonimo nato altrove non si adotta**: se uno username o una sigla
  dell'elenco esistono già senza etichetta, il provisioning si ferma.
* **Le password** arrivano già cifrate dal comando. Se manca, un utente
  nuovo non può entrare finché non la si dà; uno esistente tiene la sua.
* **Il secondo fattore** lo configura il comando dopo: il provisioning dice
  solo chi deve averlo (`dev.smoke`).
* Un cliente ha un solo accesso al portale: per questo `dev.multiveste` ha un
  cliente suo.

Restituisce una riga per ogni utente e soggetto: che cos'è, la chiave,
l'identificativo, se è stato creato o rimesso a posto.

### Test

`db/pgtap/anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
