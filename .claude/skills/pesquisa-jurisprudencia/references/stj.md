# STJ — rota de pesquisa

## O bloqueio que você precisa conhecer

O portal do STJ é servido por dois hosts com o mesmo conteúdo:

| Host | Situação |
|---|---|
| `scon.stj.jus.br` | **Bloqueado.** Desafio Cloudflare ("Confirme que é humano") que reprova clientes automatizados, e HTTP 403 no acesso direto. Nenhum cookie de liberação é emitido, mesmo quando uma pessoa clica na caixa. |
| `processo.stj.jus.br` | **Aberto.** Serve a mesma aplicação sem desafio algum. |

Use sempre `processo.stj.jus.br`. Há uma armadilha: o formulário HTML da página inicial tem o atributo `action` **fixo** apontando para `scon.stj.jus.br`. Se você preencher o campo e enviar pelo formulário, a busca é despachada para o host bloqueado e falha silenciosamente, voltando para a home. Por isso o caminho confiável é montar a URL de busca você mesmo — que é o que o script faz.

Nunca tente resolver o desafio anti-bot, nem peça ao usuário que resolva: ele falha de qualquer modo neste ambiente, e completar verificação anti-bot não é algo que se faça.

## Caminho recomendado: o script

```bash
python3 scripts/stj_busca.py '"responsabilidade civil do estado" e omissiv$' --max 50 --json stj.json
```

Retorna, para cada julgado: processo, relator, órgão julgador, datas de julgamento e publicação, **ementa integral limpa**, link do inteiro teor e marcadores de precedente qualificado.

A ementa vem de um `<textarea>` que o portal usa no botão "copiar ementa" — é texto já sem marcação, ideal para transcrição literal. Não é preciso abrir o PDF do inteiro teor só para ter a ementa.

### Detecção de precedente qualificado

O SCON emite um comentário HTML com flags booleanas explícitas para Repetitivo, IAC, Afetação e Admissão, além de um campo `CAMPO TEMA` com número e situação do tema. O script lê essas flags.

Isso importa: procurar as palavras "recurso repetitivo" no texto gera falso positivo, porque ementas frequentemente **citam** repetitivos alheios sem serem elas próprias repetitivas. Se você inspecionar o HTML manualmente, use as flags, não o texto corrido.

## Operadores da expressão de busca

`"termo exato"` · `e` · `ou` · `nao` · `adj` (adjacente) · `prox` (próximo) · `mesmo` (mesmo parágrafo) · `com` (mesmo campo) · `$` (truncamento).

Exemplos que funcionam bem:

```
"responsabilidade civil do estado" e (omissiv$ ou omissao)
"dano moral" prox5 "inscricao indevida"
usucapiao e (extraordinari$ ou tabelar) nao rural
```

Acentos são opcionais — a base normaliza. Prefira escrever sem acento na expressão para evitar problemas de codificação.

## Inteiro teor

O link vem pronto no resultado, no formato:

```
https://processo.stj.jus.br/SCON/GetInteiroTeorDoAcordao?num_registro=<digitos>&dt_publicacao=<dd/mm/aaaa>
```

Esse endpoint devolve o PDF e **funciona por script** (curl, WebFetch). Para ler o texto:

```bash
python3 scripts/extrair_texto_pdf.py acordao.pdf
```

Baixe o inteiro teor quando precisar do voto, da distinção fática ou do placar — a ementa sozinha não revela voto vencido.

## Bases além dos acórdãos

O parâmetro `--base` aceita outros acervos do SCON. `ACOR` (padrão) para acórdãos; `SUMU` para súmulas. As súmulas do STJ são autoridade forte e valem uma busca dirigida sempre que o tema for consolidado.

Vale lembrar que **súmula e tema repetitivo do STJ raramente aparecem numa busca puramente fática**: o enunciado é redigido em vocabulário de autoridade, não no vocabulário do caso. Se a primeira busca só trouxer acórdãos de turma, faça uma segunda incluindo termos como "súmula", "repetitivo" ou "tema" junto ao núcleo temático.

## Quando o host cair

Se `processo.stj.jus.br` também passar a exigir verificação, o script levanta erro explícito. A alternativa é o portal unificado do CJF (`references/cjf.md`), que indexa STJ e STF na mesma base — com cobertura mais rasa, mas aberto.
