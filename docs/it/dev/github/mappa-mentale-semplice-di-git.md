# Mappa mentale semplice di Git

> **Ultimo aggiornamento**: 24 ottobre 2026
>
> **Destinatari**: chi lavora sui branch di ZeroERP e vuole un promemoria dei comandi
>
> **Vedi anche**:
>
> * [Configurazione GitHub](/dev/github/configurazione) — il flusso dei branch, i workflow della CI, le impostazioni del repository
> * [Trappole: cosa non fare](/dev/trappole) — fra le altre, il branch cancellato da GitHub dopo il merge

---

## 1. Git ha solo tre posti

| Posto                 | Che cos'è                                 |
| --------------------- | ----------------------------------------- |
| **Working directory** | i file che stai modificando               |
| **Repository locale** | i commit salvati sul tuo computer         |
| **Remoto (`origin`)** | la copia su GitHub                        |

**Regola d'oro**: GitHub vede solo quello che è stato **pushato**. Un merge fatto in locale e non
pushato, per GitHub non esiste.

---

## 2. I comandi fondamentali

```bash
git fetch origin        # scarica le novità del remoto, non tocca i tuoi file
git status              # dove sono, cosa ho cambiato: il punto di partenza di ogni dubbio
git push                # manda su GitHub i commit locali
```

«N in uscita» in VS Code vuol dire **N commit locali non ancora pushati**: non file modificati.

Un branch è solo un **puntatore a un commit**, e `HEAD` è il punto in cui ti trovi adesso. Cambiare
branch non duplica il codice: sposta il puntatore.

---

## 3. Il flusso di ZeroERP

```text
dev/db-tid ──────┐  PR
                 ├──────►  Tito-dev  ──── PR ────►  main
dev/backend-tid ─┘         (integrazione)           (rilascio)
```

* `dev/db-tid` = lavoro sul database, `dev/backend-tid` = backend e frontend;
* `Tito-dev` = il centro: le foglie **non** si aggiornano fra loro, passano sempre dal centro;
* `main` = il rilascio.

Si integra **sempre con una pull request**, mai con un push diretto su `Tito-dev` o `main`. Il
perché, e che cosa controlla la CI in ogni passaggio, è in [Configurazione GitHub](/dev/github/configurazione).

---

## 4. La giornata

### 4.1 Prima di lavorare: riallineati al centro

```bash
git checkout dev/db-tid            # oppure dev/backend-tid
git fetch origin
git rebase origin/Tito-dev
git push --force-with-lease        # solo se il rebase ha riscritto commit già pushati
```

`--force-with-lease`, mai `--force`: rifiuta il push se sul remoto c'è qualcosa che non hai visto.

⚠️ Durante il rebase i file sul disco cambiano. Se nello stesso albero sta girando qualcosa — una
suite pgTAP, un'altra sessione di lavoro — legge file a metà. Si fa il rebase ad albero fermo.

### 4.2 Hai finito: porta il lavoro nel centro

```bash
git status                         # controlla che cosa stai per committare
git add <file> <file>              # per nome: nell'albero possono esserci file di un altro lavoro
git commit
git push origin dev/db-tid
gh pr create --base Tito-dev --head dev/db-tid   # oppure dalla pagina del repository
```

Prima di premere «Merge», guarda le corse della CI sulla PR: il repository non ha branch protetti,
quindi un rosso **non** impedisce il merge (vedi [Configurazione GitHub](/dev/github/configurazione)).
Dopo il merge, si torna al punto 4.1.

### 4.3 Il rilascio: `Tito-dev` → `main`

Si apre la PR `Tito-dev → main`. Se GitHub dice che ci sono conflitti, `main` ha qualcosa che
`Tito-dev` non ha: lo si porta dentro.

```bash
git checkout Tito-dev
git fetch origin
git merge origin/main
git push origin Tito-dev
```

⚠️ «Automatically delete head branches» deve restare **spento**: al merge di questa PR
cancellerebbe `Tito-dev` ([Trappole](/dev/trappole)).

---

## 5. Quando una PR dice «This branch has conflicts»

Vuol dire: il branch della PR non contiene l'ultima versione del branch **di destinazione**.

| PR                     | Che cosa portare dentro | Comando, sul branch della PR |
| ---------------------- | ----------------------- | ---------------------------- |
| `dev/*` → `Tito-dev`   | `Tito-dev`              | `git rebase origin/Tito-dev` (punto 4.1) |
| `Tito-dev` → `main`    | `main`                  | `git merge origin/main` (punto 4.3)      |

Poi si risolvono i conflitti nei file, si aggiungono **per nome** (`git add <file>`), si
continua (`git rebase --continue` oppure `git commit`) e si fa push. La PR si aggiorna da sola.

Git non sceglie al posto tuo: in un conflitto decidi tu che cosa tenere.

---

## 6. I tre messaggi classici

| Messaggio                       | Che cosa vuol dire                                         |
| ------------------------------- | ---------------------------------------------------------- |
| 🔴 «Your branch has diverged»   | locale e remoto hanno commit diversi: `git fetch`, poi rebase o merge |
| 🟡 «This branch has conflicts» | vedi il punto 5                                            |
| 🟢 «Everything up-to-date»      | sei allineato                                              |

---

## 7. Controlli rapidi

```bash
git merge-base --is-ancestor origin/Tito-dev HEAD; echo $?   # 0 = il mio branch contiene Tito-dev
git log --oneline HEAD..origin/Tito-dev                      # cosa mi manca di Tito-dev
git log --oneline origin/Tito-dev..HEAD                      # cosa ho in più di Tito-dev
```

---

{% include-markdown "signature-core.md" %}
