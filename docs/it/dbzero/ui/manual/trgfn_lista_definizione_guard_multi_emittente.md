## 📘 Documentazione Concettuale – Funzione Trigger `ui.trgfn_lista_definizione_guard_multi_emittente`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione)
>
Approfondimenti views:
>
[dbops.vw_liste_multi_emittente_non_certificate](/dbzero/dbops/manual/vw_liste_multi_emittente_non_certificate)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Impedisce che il contrassegno `multi_emittente` di una lista venga acceso
**dall'applicazione**. Si dichiara solo aggiornando la configurazione, cioe'
insieme a una migrazione.

---

### Cosa dichiara quel contrassegno

Un si'/no per ogni lista: **«questa schermata sa dire da quale emittente arriva
ogni riga»**.

E' una **capacita' del software**, non una preferenza di chi la usa. E una
capacita' non si dichiara per stanchezza: si guadagna facendo il lavoro che la
rende vera, cioe' mostrando l'emittente nelle righe.

Se diventasse un interruttore comodo, il primo che lo trova fastidioso lo
accende — e da quel momento la lista mescola emittenti senza dirlo, con
l'etichetta «collaudato» addosso. Sarebbe il difetto che il contrassegno doveva
impedire, aggravato dalla rassicurazione.

---

### Perche' un trigger e non un permesso

Il piano iniziale era togliere all'applicazione il **diritto** di scrivere quella
colonna: e' la difesa piu' forte, perche' non si aggira scrivendo codice.

⛔ **Non tiene.** Esiste una procedura che, a ogni aggiornamento del sistema,
riconsegna all'applicazione un mazzo di permessi completo su ogni tabella. Il
diritto tolto verrebbe **restituito**.

E cede nel modo peggiore: sull'ambiente di sviluppo la revoca sopravvive fino al
successivo aggiornamento, quindi **sembra funzionare a lungo**; sul server di
prova non funziona **mai**, perche' il database viene ricostruito da zero e i
permessi vengono riconsegnati nello stesso giro.

Un trigger invece non lo tocca nessuno.

---

### Come distingue chi puo' da chi non puo'

Confronta chi sta scrivendo con il **proprietario della tabella**, letto dal
catalogo di sistema. L'aggiornamento del sistema gira come proprietario e passa;
l'applicazione no.

⚠️ Il nome del ruolo **non e' scritto a mano**: uno scritto a mano sarebbe giusto
su questa installazione e falso sulla prossima.

Dal 25-09-2026 la domanda la fa il building block
[script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella)
(`20260925-39`): questo guard era la prima copia della regola, e i guard dei
documenti interni di magazzino sarebbero stati la seconda. Il comportamento non
cambia; il contesto dell'errore non porta più `owner_atteso`.

⚠️ **Non c'e' nessun interruttore di disattivazione**, e non e' una dimenticanza:
la condizione e' su *chi sei*, e non c'e' niente da accendere.

---

### Il baratto, dichiarato

Il trigger sorveglia **una** colonna e non copre quelle future, mentre il
permesso — sulla carta — le avrebbe coperte tutte. Ma quella copertura **oggi
non esiste**. Si e' scelta una difesa che tiene su una colonna invece di una che
sembra coprirle tutte e non ne copre nessuna.
