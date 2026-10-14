## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_cliente_chiave_unica`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_clienti_stessa_chiave](/dbzero/anagrafiche/manual/fn_clienti_stessa_chiave)
>
[anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_emittente)
>
Guide:
>
[Un cliente manuale per soggetto, servizio e azienda](/it/guide/gestione-delle-istanze-utility#un-cliente-manuale-per-soggetto-servizio-e-azienda)

---
### 🎯 Scopo Principale
(latest review 14-10-26)

Impedisce di scrivere **due volte la stessa fornitura** quando non c'è un punto di fornitura.

---

### La regola

Decisioni del 2026-10-13: fra i clienti delle istanze fittizie, due clienti con lo stesso
soggetto, lo stesso servizio e la stessa azienda, attivi in periodi che si sovrappongono, sono un
doppione. È la regola sorella di quella sul punto di fornitura (un punto, un cliente alla volta).

Chi occupa la fornitura lo dice
[anagrafiche.fn_clienti_stessa_chiave](/dbzero/anagrafiche/manual/fn_clienti_stessa_chiave): un
sospeso la occupa ancora, un chiuso la libera dalla sua data di chiusura, un annullato o un
pre-contrattuale non la occupano.

---

### Quando si controlla

La fornitura dipende da quattro tabelle (cliente, istanza, billing account, collegamento
all'azienda), e la regola si può rompere da ognuna:

| Che cosa cambia | Chi controlla |
| --- | --- |
| si scrive un cliente (nascita, stato, date) | il controllo sul cliente |
| cambia l'azienda di un billing account | i clienti di quel billing account |
| un'istanza diventa fittizia | i clienti di quell'istanza |
| si sposta l'azienda predefinita | tutti i clienti fittizi dei billing account senza collegamento |

Le altre colonne della fornitura sul cliente (soggetto, servizio, billing account) non si
cambiano: lo impedisce il blocco delle colonne.

Il controllo avviene **alla conferma dell'operazione**: dentro la stessa operazione si può
chiudere il cliente vecchio e aprire il nuovo in qualunque ordine.

---

### Le funzioni sorelle

* `anagrafiche.fn_guard_clienti_chiave_unica_di` — applica il controllo ai clienti di un billing
  account o di un'istanza;
* `anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale` — lo applica a tutti i clienti
  fittizi dei billing account senza collegamento, quando si sposta l'azienda predefinita.

Sono privilegiate per lo stesso motivo del controllo: un cliente fuori dal perimetro di chi
scrive sarebbe invisibile.

---

### Errore

`E_CLIENTE_STESSA_CHIAVE` — *«Per questo soggetto, servizio e azienda esiste già il cliente %s,
attivo nello stesso periodo.»*, col codice del billing account del cliente che esiste già (il
cliente non ha un codice suo).
