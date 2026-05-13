# Installing and Using Typst on Windows with winget

## Install Typst

Open PowerShell or Command Prompt and run:

```powershell
winget install --id Typst.Typst -e
```

## Verify Installation

Check that Typst was installed correctly:

```powershell
typst --version
```

## Create a Typst File

Create a new file named `main.typ` with this content:

```typst
= Hello, Typst!

This is my first Typst document.
```

## Compile a Typst File

Compile the file into a PDF:

```powershell
typst compile main.typ
```

This will generate:

```text
main.pdf
```

## Live Preview While Editing

Automatically rebuild the PDF when the file changes:

```powershell
typst watch main.typ
```

## Helpful Links

- https://typst.app
- https://github.com/typst/typst
