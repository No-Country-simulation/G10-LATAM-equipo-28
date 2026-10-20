# Guía Git para el equipo

Instrucciones básicas para subir cambios al repositorio del equipo desde Git Bash.

**Flujo del equipo (importante):** cada quien trabaja en su **rama personal**
(`feature/<nombre>-<tema>`, `fix/<tema>`, `docs/<tema>`) y abre un **Pull Request
a `dev`**. Los merges a `main` salen de `dev`. **Nunca** se commitea directo a
`main` ni a `dev`.

---

## Cómo hacerlo desde Git Bash

### 1. Abrir Git Bash en la carpeta del repo

Opción rápida: en el Explorador de Windows, entra a la carpeta del proyecto, click derecho → "Open Git Bash here".

O desde una terminal ya abierta:

```bash
cd "/c/Users/<tu-usuario>/ruta/al/G10-LATAM-equipo-28"
```

(En Git Bash, `C:\` se escribe como `/c/` y se usan `/` no `\`. Reemplaza la ruta
por la de tu propia máquina.)

### 2. Ver qué cambió

```bash
git status
```

Te dice qué archivos son nuevos (untracked), cuáles modificaste, y cuáles ya están en el "staging area" listos para commit.

### 3. Añadir archivos al staging

```bash
git add archivo1.py archivo2.md          # archivos específicos (recomendado)
git add .                                # todo lo que hay en la carpeta actual
```

Prefiere nombrar los archivos: evita subir cosas por error (secretos, basura temporal, etc.).

### 4. Crear el commit

```bash
git commit -m "Mensaje descriptivo del cambio"
```

El mensaje debe explicar el *por qué* del cambio, no solo el *qué*.

### 5. Subir al repositorio del equipo

```bash
git push
```

La primera vez en una rama nueva Git te pedirá `git push -u origin nombre-rama` (el `-u` deja esa rama "trackeada" para que después, en esa misma rama, baste con `git push`).

### 6. Bajar cambios de otros compañeros

Antes de empezar a trabajar en el día, o antes de un push si otros están comiteando:

```bash
git checkout dev          # pararte sobre la rama de integración
git pull                  # traer lo último que el equipo mergeó a dev
```

Esto trae los commits de `dev` a tu local. Si quieres esas novedades en tu rama
personal, mézclalas desde ahí (`git merge dev` estando en tu rama).

---

## Flujo típico del día

```bash
git checkout dev                 # pararte en la rama de integración
git pull                         # traer lo último del equipo
git checkout mi-rama-personal    # volver a tu rama de trabajo
git merge dev                    # traer las novedades a tu trabajo
# ...trabajas, editas archivos...
git status                       # revisar qué cambió
git add archivo1 archivo2        # marcar lo que quieres subir
git commit -m "Descripción"      # crear el commit local
git push                         # subir tu rama personal al remoto
```

Después de eso, abres el Pull Request de tu rama personal hacia `dev` en GitHub.

---

## Recomendaciones importantes para trabajo en equipo

- **Nunca hagas `push --force` sobre `main` ni sobre `dev`** — puede sobrescribir el trabajo de otros.
- **Haz `git pull` antes de `git push`** — si otro compañero subió algo antes, Git te pedirá integrar sus cambios primero.
- **No trabajes directo en `main` ni en `dev`.** Crea una rama para cada feature:

  ```bash
  git checkout -b nombre-de-la-feature   # crear y cambiarte a nueva rama
  # trabajas, comiteas normal...
  git push -u origin nombre-de-la-feature
  ```

  Luego abres un Pull Request en GitHub para mergear a `dev`. Así el equipo puede revisar antes de que entre a `dev`, y de ahí sale el merge a `main`.
- **Revisa qué estás subiendo** con `git status` y `git diff --staged` antes del commit — evita subir archivos `.env` con contraseñas, tokens, etc.
